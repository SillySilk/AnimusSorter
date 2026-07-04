"""LM Studio vision layer for Analyze + Auto-sort.

Talks to a local LM Studio server over its OpenAI-compatible REST API (the same
connection AnimaForge uses): images go up as base64 JPEG data-URIs, replies come
back as JSON we parse tolerantly. Pure stdlib `urllib` + Pillow — no heavy deps.

Two domain calls:
  - analyze_bin: look at a bin's images and report the distinct recurring subjects.
  - match_image: decide which roster subjects appear in one tray image (+ outsiders).

The correctness core (`is_exact_match`) and the parsers are pure and unit-tested;
the network/Pillow parts take an injectable `transport` so they test without a server.
"""
from __future__ import annotations

import base64
import io
import json
import re
import urllib.request

from .applog import get_logger

log = get_logger("llm")

DEFAULT_URL = "http://localhost:1234/v1"
DEFAULT_MODEL = "qwen2.5-vl-7b-instruct"
MAX_ANALYZE_IMAGES = 8  # vision models get unreliable past a handful of images per call

_REFUSAL_RE = re.compile(r"^\s*(i'm sorry|i am sorry|i can't|i cannot|i won't|as an ai|sorry,)", re.I)


# --- correctness core --------------------------------------------------------
def _norm(name: str) -> str:
    """Case- and whitespace-insensitive key for comparing subject names."""
    return re.sub(r"\s+", " ", (name or "").strip()).lower()


def is_exact_match(present, outsiders: bool, bin_names) -> bool:
    """A tray image belongs in the bin iff it holds EXACTLY the bin's named subjects
    (all of them, none extra) and no characters from outside that set."""
    if outsiders:
        return False
    return {_norm(n) for n in present} == {_norm(n) for n in bin_names if _norm(n)}


# --- tolerant parsing --------------------------------------------------------
def _extract_json(text: str):
    """Pull the first JSON object/array out of a model reply (tolerates code fences,
    preamble, trailing prose). Returns the parsed value or None."""
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```[a-zA-Z]*", "", t).strip().strip("`").strip()
    # Try the whole thing first, then the first {...} or [...] span.
    for candidate in (t, *_json_spans(t)):
        try:
            return json.loads(candidate)
        except (ValueError, TypeError):
            continue
    return None


def _json_spans(t: str):
    for open_c, close_c in (("{", "}"), ("[", "]")):
        i, j = t.find(open_c), t.rfind(close_c)
        if 0 <= i < j:
            yield t[i:j + 1]


def parse_match_response(text: str, roster_names) -> dict:
    """Parse {"present": [...], "outsiders": bool}. Unknown/garbage -> safe non-match
    ({present: [], outsiders: False}). Present names are canonicalized to roster spelling."""
    data = _extract_json(text)
    if not isinstance(data, dict):
        return {"present": [], "outsiders": False}
    canon = {_norm(n): n for n in roster_names}
    present = []
    for n in data.get("present") or []:
        key = _norm(n if isinstance(n, str) else "")
        if key in canon and canon[key] not in present:
            present.append(canon[key])
    return {"present": present, "outsiders": bool(data.get("outsiders"))}


def parse_analyze_response(text: str, n_expected: int) -> list:
    """Parse a list of {description, rep_index}. Accepts a bare list or {"subjects":[...]}.
    Coerces a missing/bad rep_index to 0."""
    data = _extract_json(text)
    if isinstance(data, dict):
        data = data.get("subjects") or data.get("figures") or data.get("characters") or []
    if not isinstance(data, list):
        return []
    figures = []
    for item in data:
        if not isinstance(item, dict):
            continue
        desc = str(item.get("description") or item.get("desc") or "").strip()
        if not desc:
            continue
        try:
            idx = int(item.get("rep_index"))
        except (TypeError, ValueError):
            idx = 0
        figures.append({"description": desc, "rep_index": max(0, idx)})
    return figures


def is_refusal(text: str) -> bool:
    return bool(_REFUSAL_RE.search(text or ""))


# --- message builders --------------------------------------------------------
def _subject_word(category: str) -> str:
    return "object" if str(category).lower() == "object" else "character"


def _image_part(image_b64: str) -> dict:
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}


def build_analyze_messages(subject_names, category: str, image_b64_list) -> list:
    word = _subject_word(category)
    n = len(subject_names)
    names = ", ".join(subject_names)
    system = (
        f"You are a precise visual analyst labeling a small image set for sorting. You "
        f"identify distinct recurring {word}s across the images and never invent ones that "
        f"are not visible."
    )
    text = (
        f"These {len(image_b64_list)} images are meant to show {n} distinct {word}(s): "
        f"{names}. Identify the distinct recurring {word}s you actually see (aim for {n}). "
        f"For each, give a short recognition description (the visual features that tell it "
        f"apart from the others) and rep_index = the 0-based index of the image that shows "
        f"it most clearly.\n"
        f'Reply with ONLY a JSON array, no prose: '
        f'[{{"description": "...", "rep_index": 0}}, ...].'
    )
    user = [{"type": "text", "text": text}] + [_image_part(b) for b in image_b64_list]
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_match_messages(roster: dict, category: str, image_b64: str) -> list:
    word = _subject_word(category)
    roster_lines = "\n".join(f"- {name}: {desc}" for name, desc in roster.items())
    names = ", ".join(roster.keys())
    system = (
        f"You are a precise visual matcher. Given a roster of described {word}s and one "
        f"image, you report which roster {word}s appear and whether anyone NOT on the "
        f"roster appears. You never guess; if unsure a {word} is present, omit it."
    )
    text = (
        f"Roster ({word}s):\n{roster_lines}\n\n"
        f"Look at the image. Which of these roster {word}s appear: {names}? Are there any "
        f"prominent {word}s present that are NOT on the roster?\n"
        f'Reply with ONLY JSON, no prose: {{"present": ["<roster names that appear>"], '
        f'"outsiders": <true if any non-roster {word} appears, else false>}}.'
    )
    user = [{"type": "text", "text": text}, _image_part(image_b64)]
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# --- image encoding ----------------------------------------------------------
def downscale_to_jpeg_b64(path: str, max_side: int = 1024, quality: int = 90) -> str:
    from PIL import Image
    img = Image.open(path).convert("RGB")
    w, h = img.size
    if max(w, h) > max_side:
        scale = max_side / max(w, h)
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("ascii")


# --- transport + chat --------------------------------------------------------
def _urllib_transport(url: str, body: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def chat(url, model, messages, *, timeout=120.0, max_tokens=700, transport=None) -> str:
    """POST a chat completion and return the assistant text. One refusal-retry. The
    `transport(url, body, timeout) -> response_json` seam lets tests inject canned replies."""
    transport = transport or _urllib_transport
    params = {"temperature": 0.2, "max_tokens": max_tokens, "stream": False}
    if model and model.strip():
        params["model"] = model.strip()
    body = {"messages": messages, **params}
    data = transport(url, body, timeout)
    content = (data["choices"][0]["message"].get("content") or "") if data.get("choices") else ""
    if is_refusal(content):
        retry = list(messages) + [{"role": "user",
                                   "content": "Continue. Answer with the JSON only; do not refuse."}]
        data = transport(url, {"messages": retry, **{**params, "temperature": 0.5}}, timeout)
        content = (data["choices"][0]["message"].get("content") or "") if data.get("choices") else ""
    return content


def verify_server(url: str):
    """(ok, detail). ok only when LM Studio is reachable AND a model is loaded."""
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/models", timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        ids = [m.get("id") for m in data.get("data", [])]
        if not ids:
            return False, "LM Studio is up but no model is loaded — load a vision model."
        return True, "Loaded: " + ", ".join(str(i) for i in ids)
    except Exception as exc:  # noqa: BLE001 — surface any connection error to the UI
        return False, f"Cannot reach LM Studio at {url} ({exc})."


# --- domain calls ------------------------------------------------------------
def analyze_bin(image_paths, subject_names, category, url, model, *, transport=None,
                timeout=180.0) -> list:
    """Identify the distinct recurring subjects across a bin's images."""
    paths = list(image_paths)[:MAX_ANALYZE_IMAGES]
    b64s = [downscale_to_jpeg_b64(p) for p in paths]
    messages = build_analyze_messages(subject_names, category, b64s)
    content = chat(url, model, messages, timeout=timeout, transport=transport)
    return parse_analyze_response(content, len(subject_names))


def match_image(image_path, roster, category, url, model, *, transport=None,
                timeout=120.0) -> dict:
    """Decide which roster subjects appear in one image (and whether outsiders do)."""
    b64 = downscale_to_jpeg_b64(image_path)
    messages = build_match_messages(roster, category, b64)
    content = chat(url, model, messages, timeout=timeout, transport=transport)
    return parse_match_response(content, list(roster.keys()))
