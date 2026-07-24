"""Adapter for the official Windows Python install manager."""
from __future__ import annotations
import os
import json
import shutil
import subprocess
from pathlib import Path
from .environment import external_source_root

class RuntimeManagerError(RuntimeError):
    pass

def find_manager() -> str:
    manager = shutil.which("pymanager")
    if manager:
        return manager
    py = shutil.which("py")
    if py:
        probe = subprocess.run([py, "help", "install"], capture_output=True, text=True, timeout=10)
        if probe.returncode == 0:
            return py
    raise RuntimeManagerError("공식 Python install manager가 없습니다. Microsoft Store에서 설치하거나 `winget install 9NQ7512CXL7T`를 실행하세요.")

def _command(*args: str, capture: bool = False):
    return subprocess.run([find_manager(), *args], check=True, text=True, capture_output=capture)

def list_runtimes(*, online: bool = False, tag: str | None = None) -> str:
    args = ["list"]
    if online:
        args.append("--online")
    if tag:
        args.extend(["--one", tag])
    return _command(*args, capture=True).stdout

def install_runtime(tag: str = "default", *, update: bool = False, dry_run: bool = False) -> None:
    args = ["install"]
    if update:
        args.append("--update")
    if dry_run:
        args.append("--dry-run")
    _command(*args, tag)

def set_preference(root: Path, tag: str) -> Path:
    if not tag or any(c.isspace() for c in tag):
        raise ValueError("런타임 태그는 비어 있거나 공백을 포함할 수 없습니다.")
    output = root / ".hython-runtime"
    output.write_text(tag + "\n", encoding="utf-8")
    return output

def get_preference(start: Path) -> str | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for directory in (current, *current.parents):
        candidate = directory / ".hython-runtime"
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8").strip() or None
    try:
        home=Path(os.environ.get("HYTHON_HOME",Path.home()/".hython"))
        payload=json.loads((home/"state.json").read_text(encoding="utf-8"))
        tag=payload.get("runtime_tag")
        return tag if isinstance(tag,str) and tag else None
    except (OSError,UnicodeError,json.JSONDecodeError):
        return None

def run_hython_with_runtime(tag: str, argv: list[str]) -> int:
    """Run this installed Hython package inside a managed Python runtime."""
    env=os.environ.copy()
    env["HYTHON_RUNTIME_ACTIVE"]=tag
    source_root=str(external_source_root())
    env["PYTHONPATH"]=source_root+os.pathsep+env.get("PYTHONPATH","")
    return subprocess.run([find_manager(),"exec",f"-V:{tag}","-m","hython",*argv],env=env).returncode

def reexec_with_preferred_runtime(argv: list[str], start: Path) -> None:
    tag = get_preference(start)
    if not tag or os.environ.get("HYTHON_RUNTIME_ACTIVE") == tag:
        return
    env = os.environ.copy()
    env["HYTHON_RUNTIME_ACTIVE"] = tag
    source_root = str(external_source_root())
    env["PYTHONPATH"] = source_root + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run([find_manager(), "exec", f"-V:{tag}", "-m", "hython", *argv], env=env)
    raise SystemExit(result.returncode)
