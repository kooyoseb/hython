"""Lifecycle for generated syntax state kept outside the installed core."""

from __future__ import annotations

import json
import os
import platform
import tempfile
from pathlib import Path

from . import __version__
from .package_manager import refresh_dictionaries
from .runtime import sync_runtime


def state_root() -> Path:
    root = Path(os.environ.get("HYTHON_HOME", Path.home() / ".hython"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def marker_path() -> Path:
    return state_root() / "state.json"


def is_initialized() -> bool:
    try:
        payload = json.loads(marker_path().read_text(encoding="utf-8"))
        return (
            payload.get("format") == 1
            and payload.get("hython_version") == __version__
            and payload.get("python_version") == platform.python_version()
        )
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False


def initialize(*, force: bool = False) -> dict:
    if is_initialized() and not force:
        return {"initialized": False, "runtime": None}
    previous = {}
    try:
        previous=json.loads(marker_path().read_text(encoding="utf-8"))
    except (OSError,UnicodeError,json.JSONDecodeError):
        pass
    runtime = sync_runtime()
    if previous:
        refresh_dictionaries()
    payload = {
        "format": 1,
        "hython_version": __version__,
        "python_version": platform.python_version(),
    }
    if isinstance(previous.get("runtime_tag"),str):
        payload["runtime_tag"]=previous["runtime_tag"]
    _atomic_json(marker_path(), payload)
    return {"initialized": True, "runtime": runtime}


def refresh(*, runtime_tag: str | None = None) -> dict:
    """Regenerate active runtime and package overlays, pruning stale packages."""
    runtime = sync_runtime()
    refreshed, removed = refresh_dictionaries()
    payload = {
        "format": 1,
        "hython_version": __version__,
        "python_version": platform.python_version(),
    }
    if runtime_tag:
        payload["runtime_tag"] = runtime_tag
    else:
        try:
            previous=json.loads(marker_path().read_text(encoding="utf-8"))
            if isinstance(previous.get("runtime_tag"),str):
                payload["runtime_tag"]=previous["runtime_tag"]
        except (OSError,UnicodeError,json.JSONDecodeError):
            pass
    _atomic_json(marker_path(), payload)
    return {"runtime": runtime, "refreshed": refreshed, "removed": removed}


def _atomic_json(output: Path, payload: dict) -> None:
    handle, temporary = tempfile.mkstemp(prefix=output.name + ".", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        Path(temporary).replace(output)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
