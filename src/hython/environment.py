"""Shared paths for source and frozen Hython distributions."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys,"frozen",False) or "__compiled__" in globals() or os.environ.get("HYTHON_FROZEN"))


def hython_home() -> Path:
    root=Path(os.environ.get("HYTHON_HOME",Path.home()/".hython"))
    root.mkdir(parents=True,exist_ok=True)
    return root


def external_source_root() -> Path:
    configured=os.environ.get("HYTHON_BUNDLED_SOURCE")
    if configured:
        return Path(configured)
    if is_frozen():
        base=Path(getattr(sys,"_MEIPASS",Path(sys.argv[0]).resolve().parent))
        return base/"hython_source"
    return Path(__file__).resolve().parents[1]


def package_store() -> Path:
    path=hython_home()/"packages"/f"python-{sys.version_info.major}.{sys.version_info.minor}"
    path.mkdir(parents=True,exist_ok=True)
    return path


def activate_package_store() -> Path:
    path=package_store()
    value=str(path)
    if value not in sys.path:
        sys.path.insert(0,value)
    return path


def display_executable() -> Path:
    """Return the user-launched executable, not a onefile extraction helper."""
    if is_frozen() and sys.argv:
        return Path(sys.argv[0]).resolve()
    return Path(sys.executable).resolve()
