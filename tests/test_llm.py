"""Pure-logic tests for the LM Studio vision layer (no live server)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sorting_tray.llm import (
    analyze_bin,
    build_analyze_messages,
    build_match_messages,
    is_exact_match,
    match_image,
    parse_analyze_response,
    parse_match_response,
)


# --- the correctness core: exactly-this-set, no outsiders --------------------
def test_exact_match_single_subject():
    assert is_exact_match(["Homer"], False, ["Homer"]) is True
    assert is_exact_match(["Homer"], True, ["Homer"]) is False   # an outsider present
    assert is_exact_match([], False, ["Homer"]) is False         # subject absent


def test_exact_match_is_case_and_space_insensitive():
    assert is_exact_match(["homer  simpson"], False, ["Homer Simpson"]) is True


def test_exact_match_multi_requires_full_set():
    assert is_exact_match(["Homer", "Marge"], False, ["Homer", "Marge"]) is True
    assert is_exact_match(["Homer"], False, ["Homer", "Marge"]) is False  # missing Marge
    assert is_exact_match(["Homer", "Marge", "Bart"], False, ["Homer", "Marge"]) is False  # extra named


def test_exact_match_outsider_blocks_even_with_full_set():
    assert is_exact_match(["Homer", "Marge"], True, ["Homer", "Marge"]) is False


# --- parsing the model's replies (tolerant) ----------------------------------
def test_parse_match_response_plain_json():
    out = parse_match_response('{"present": ["Homer"], "outsiders": false}', ["Homer", "Marge"])
    assert out == {"present": ["Homer"], "outsiders": False}


def test_parse_match_response_strips_code_fence_and_canonicalizes_names():
    raw = '```json\n{"present": ["HOMER"], "outsiders": true}\n```'
    out = parse_match_response(raw, ["Homer", "Marge"])
    assert out["present"] == ["Homer"]   # canonicalized to the roster's spelling
    assert out["outsiders"] is True


def test_parse_match_response_garbage_is_safe_nonmatch():
    out = parse_match_response("the model rambled with no json", ["Homer"])
    assert out == {"present": [], "outsiders": False}


def test_parse_analyze_response_list():
    raw = '[{"description":"red-haired girl","rep_index":2},{"description":"knight","rep_index":0}]'
    figs = parse_analyze_response(raw, 2)
    assert figs == [
        {"description": "red-haired girl", "rep_index": 2},
        {"description": "knight", "rep_index": 0},
    ]


def test_parse_analyze_response_tolerates_wrapper_and_bad_index():
    raw = '```\n{"subjects": [{"description":"a cat","rep_index":"x"}]}\n```'
    figs = parse_analyze_response(raw, 1)
    assert figs == [{"description": "a cat", "rep_index": 0}]   # bad index -> 0


# --- message builders --------------------------------------------------------
def test_build_match_messages_has_image_and_roster_and_json_instruction():
    msgs = build_match_messages({"Homer": "bald yellow man"}, "Character", "BASE64DATA")
    user = msgs[-1]["content"]
    kinds = [part["type"] for part in user]
    assert "image_url" in kinds and "text" in kinds
    text = next(p["text"] for p in user if p["type"] == "text")
    assert "Homer" in text and "bald yellow man" in text
    assert "json" in text.lower()


def test_build_analyze_messages_lists_images_and_targets_count():
    msgs = build_analyze_messages(["Homer", "Marge"], "Character", ["B1", "B2", "B3"])
    user = msgs[-1]["content"]
    image_parts = [p for p in user if p["type"] == "image_url"]
    assert len(image_parts) == 3            # one image_url per supplied base64
    text = next(p["text"] for p in user if p["type"] == "text")
    assert "2" in text                       # target count = number of named subjects


# --- domain calls with an injected fake transport (no network, no Pillow) ----
def _png(path: Path):
    from PIL import Image
    Image.new("RGB", (8, 8), (120, 80, 60)).save(path)
    return str(path)


def test_match_image_with_fake_transport(tmp_path):
    img = _png(tmp_path / "x.png")

    def fake_transport(url, body, timeout):
        return {"choices": [{"message": {"content": '{"present":["Homer"],"outsiders":false}'}}]}

    out = match_image(img, {"Homer": "bald man"}, "Character",
                      "http://x/v1", "m", transport=fake_transport)
    assert out == {"present": ["Homer"], "outsiders": False}


def test_analyze_bin_with_fake_transport(tmp_path):
    imgs = [_png(tmp_path / f"{i}.png") for i in range(3)]

    def fake_transport(url, body, timeout):
        return {"choices": [{"message": {"content":
                '[{"description":"a","rep_index":0},{"description":"b","rep_index":1}]'}}]}

    figs = analyze_bin(imgs, ["A", "B"], "Character",
                       "http://x/v1", "m", transport=fake_transport)
    assert [f["description"] for f in figs] == ["a", "b"]
