"""Entry point used by standalone Hython executables."""

import os
from pathlib import Path

os.environ.setdefault("HYTHON_FROZEN","1")
os.environ.setdefault("HYTHON_BUNDLED_SOURCE",str(Path(__file__).resolve().parent/"hython_source"))

from hython.cli import entrypoint


if __name__ == "__main__":
    raise SystemExit(entrypoint())
