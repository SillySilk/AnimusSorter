"""sorting-tray: sort scraped training images into subject bins and batch-rename them.

The renamed files encode their subjects in the filename (NAME_SERIAL_CATEGORY.ext),
which a downstream LoRA tool parses to emit caption trigger tokens.
"""

__version__ = "1.0.0"
