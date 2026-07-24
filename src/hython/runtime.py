"""Python runtime discovery and Hython syntax compatibility profiles."""

from __future__ import annotations

import json
import keyword
import platform
import sys
import sysconfig
import tempfile
from pathlib import Path

from .phonetics import pronounce_identifier
from .translator import to_python
from .vocabulary import KEYWORDS
from .environment import display_executable


def profile_dir() -> Path:
    path = Path(__import__("os").environ.get("HYTHON_HOME", Path.home() / ".hython")) / "runtimes"
    path.mkdir(parents=True, exist_ok=True)
    return path


def inspect_runtime() -> dict:
    """Inspect the active interpreter instead of assuming a Python grammar version."""
    hard = sorted(keyword.kwlist)
    soft = sorted(getattr(keyword, "softkwlist", []))
    known = set(KEYWORDS)
    # Pattern wildcard `_` is intentionally identical in Hython.
    discovered = [name for name in hard + soft if name not in known and name != "_"]
    return {
        "format": 1,
        "implementation": platform.python_implementation(),
        "version": platform.python_version(),
        "version_info": list(sys.version_info[:3]),
        "executable": str(display_executable()),
        "platform": sysconfig.get_platform(),
        "hard_keywords": hard,
        "soft_keywords": soft,
        "new_keywords": discovered,
        "generated_spellings": {
            name: pronounce_identifier(name) for name in discovered
        },
    }


def sync_runtime() -> Path:
    """Persist a reproducible profile for the active Python runtime."""
    profile = inspect_runtime()
    output = profile_dir() / f"python-{profile['version']}.json"
    _atomic_json(output, profile)
    # Keep the entire standard-library API pronunciation layer matched to the
    # selected Python version. This state lives outside the installed core.
    from .package_manager import scan_standard_library
    scan_standard_library()
    return output


def _atomic_json(output: Path, payload: dict) -> None:
    """Replace generated state without exposing a half-written profile."""
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=output.name + ".", suffix=".tmp", dir=output.parent)
    try:
        with __import__("os").fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            __import__("os").fsync(stream.fileno())
        Path(temporary).replace(output)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def load_runtime_spellings() -> dict[str, str]:
    """Return generated spellings for the active interpreter only."""
    path = profile_dir() / f"python-{platform.python_version()}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = payload.get("generated_spellings", {})
        if payload.get("format") != 1 or not isinstance(entries, dict):
            return {}
        return {
            spoken: python_name for python_name, spoken in entries.items()
            if isinstance(python_name, str) and isinstance(spoken, str)
        }
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}


def check_file(path: Path) -> tuple[bool, str | None]:
    """Compile a Hython file with the active interpreter without executing it."""
    try:
        source = path.read_text(encoding="utf-8-sig")
        compile(to_python(source), str(path), "exec")
    except (OSError, UnicodeError, SyntaxError) as exc:
        return False, str(exc)
    return True, None


def check_tree(root: Path) -> list[tuple[Path, str]]:
    """Return syntax failures for all Hython files under a path."""
    paths = [root] if root.is_file() else sorted(root.rglob("*.hy"))
    failures: list[tuple[Path, str]] = []
    for path in paths:
        valid, error = check_file(path)
        if not valid:
            failures.append((path, error or "알 수 없는 오류"))
    return failures
