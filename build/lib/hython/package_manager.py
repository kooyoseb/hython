"""Package installation and safe, static public-API dictionary generation."""

from __future__ import annotations

import ast
import importlib.machinery
import importlib.metadata
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from .phonetics import pronounce_identifier


def infer_module_name(spec: str) -> str:
    """Infer an import name from a PEP 508-style distribution specifier."""
    match=re.match(r"\s*([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)",spec)
    if not match or spec[match.end():match.end()+1] not in ("","[","<",">","=","!","~","@"," ","\t"):
        raise ValueError("패키지 지정자에서 모듈명을 추론할 수 없습니다. --module을 지정하세요.")
    return match.group(1).replace("-","_")


def dictionary_dir() -> Path:
    root = Path(__import__("os").environ.get("HYTHON_HOME", Path.home() / ".hython")) / "dictionaries"
    root.mkdir(parents=True, exist_ok=True)
    return root


def install(package: str, *, upgrade: bool = False) -> None:
    """Install through the current interpreter; subprocess avoids pip internals."""
    command = [sys.executable, "-m", "pip", "install"]
    if upgrade:
        command.append("--upgrade")
    command.append(package)
    subprocess.run(command, check=True)


def uninstall(package: str) -> None:
    """Remove a distribution through pip."""
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", package], check=True)


def _public_names(path: Path) -> set[str]:
    names: set[str] = set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError):
        return names
    explicit_all: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                exposed = alias.asname or alias.name.split(".")[0]
                if not exposed.startswith("_"):
                    names.add(exposed)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    names.add(target.id)
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
            ) and isinstance(node.value, (ast.List, ast.Tuple)):
                explicit_all.update(
                    item.value for item in node.value.elts
                    if isinstance(item, ast.Constant) and isinstance(item.value, str)
                )
    return explicit_all or names


def scan(module: str) -> Path:
    """Statically scan a module/package without importing or executing it."""
    spec = _find_spec_static(module)
    if spec is None:
        raise ModuleNotFoundError(f"패키지를 찾을 수 없습니다: {module}")
    files: list[Path] = []
    if spec.submodule_search_locations:
        for location in spec.submodule_search_locations:
            files.extend(Path(location).rglob("*.py"))
    elif spec.origin and spec.origin.endswith(".py"):
        files.append(Path(spec.origin))
    names: set[str] = set()
    for file in files:
        names.update(_public_names(file))
    python_to_hython = {name: pronounce_identifier(name) for name in sorted(names)}
    # A collision is ambiguous; retain neither spelling until the user edits it.
    counts: dict[str, int] = {}
    for spoken in python_to_hython.values():
        counts[spoken] = counts.get(spoken, 0) + 1
    python_to_hython = {
        name: spoken for name, spoken in python_to_hython.items() if counts[spoken] == 1
    }
    payload = {
        "format": 1,
        "module": module,
        "distribution_version": _version_for(module),
        "python_to_hython": python_to_hython,
    }
    output = dictionary_dir() / f"{module.replace('.', '__')}.json"
    _atomic_json(output, payload)
    return output


def _atomic_json(output: Path, payload: dict) -> None:
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


def remove_dictionary(module: str) -> bool:
    path = dictionary_dir() / f"{module.replace('.', '__')}.json"
    existed = path.exists()
    path.unlink(missing_ok=True)
    return existed


def refresh_dictionaries() -> tuple[list[Path], list[Path]]:
    """Rescan installed modules and prune dictionaries whose packages disappeared."""
    refreshed: list[Path] = []
    removed: list[Path] = []
    for path in sorted(dictionary_dir().glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            module = payload["module"]
            if not isinstance(module, str):
                continue
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError):
            continue
        if _find_spec_static(module) is None:
            path.unlink(missing_ok=True)
            removed.append(path)
        else:
            refreshed.append(scan(module))
    return refreshed, removed


def _find_spec_static(module: str):
    """Resolve dotted modules without importing their parent packages."""
    if not module or any(not part for part in module.split(".")):
        return None
    search_path = None
    fullname = ""
    spec = None
    for part in module.split("."):
        fullname = f"{fullname}.{part}" if fullname else part
        spec = importlib.machinery.PathFinder.find_spec(fullname, search_path)
        if spec is None:
            return None
        search_path = spec.submodule_search_locations
    return spec


def _version_for(module: str) -> str | None:
    packages = importlib.metadata.packages_distributions()
    distributions = packages.get(module.split(".")[0], [])
    if not distributions:
        return None
    try:
        return importlib.metadata.version(distributions[0])
    except importlib.metadata.PackageNotFoundError:
        return None


def load_dictionaries() -> dict[str, str]:
    """Load valid user dictionaries as Hython-to-Python mappings."""
    result: dict[str, str] = {}
    for path in dictionary_dir().glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            entries = payload["python_to_hython"]
            if not isinstance(entries, dict):
                continue
            for python_name, spoken in entries.items():
                if isinstance(python_name, str) and isinstance(spoken, str):
                    result.setdefault(spoken, python_name)
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError):
            continue
    return result


def load_python_dictionaries() -> dict[str, str]:
    """Load valid user dictionaries as Python-to-Hython mappings."""
    return {python: spoken for spoken, python in load_dictionaries().items()}
