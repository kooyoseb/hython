"""Package installation and safe, static public-API dictionary generation."""

from __future__ import annotations

import ast
import importlib.machinery
import importlib.metadata
import json
import re
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

from .phonetics import pronounce_identifier
from .environment import is_frozen, package_store


_DEEP_SCAN_SCRIPT = r"""
import importlib, inspect, json, sys
if sys.argv[2]:
    sys.path.insert(0, sys.argv[2])
module = importlib.import_module(sys.argv[1])
names = set()
def visit(obj, depth=0):
    try:
        members = inspect.getmembers_static(obj)
    except Exception:
        return
    for name, value in members:
        if not name.startswith("_"):
            names.add(name)
            if depth == 0 and inspect.isclass(value):
                visit(value, 1)
visit(module)
print("__HYTHON_API__" + json.dumps(sorted(names), ensure_ascii=False))
"""

_DICTIONARY_CACHE_KEY: tuple[tuple[str, int, int], ...] | None = None
_DICTIONARY_CACHE: dict[str, str] = {}


def infer_module_name(spec: str) -> str:
    """Infer an import name from a PEP 508-style distribution specifier."""
    match=re.match(r"\s*([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)",spec)
    if not match or spec[match.end():match.end()+1] not in ("","[","<",">","=","!","~","@"," ","\t"):
        raise ValueError("패키지 지정자에서 모듈명을 추론할 수 없습니다. --module을 지정하세요.")
    return match.group(1).replace("-","_")


def modules_for_distribution(spec: str, fallback: str | None = None) -> list[str]:
    """Return every top-level import supplied by a distribution."""
    distribution = infer_module_name(spec)
    normalized = re.sub(r"[-_.]+", "-", distribution).lower()
    modules = {
        module
        for module, distributions in importlib.metadata.packages_distributions().items()
        if any(re.sub(r"[-_.]+", "-", item).lower() == normalized for item in distributions)
        and module.isidentifier()
    }
    if fallback:
        modules.add(fallback)
    elif not modules:
        modules.add(distribution)
    return sorted(modules)


def dictionary_dir() -> Path:
    root = Path(__import__("os").environ.get("HYTHON_HOME", Path.home() / ".hython")) / "dictionaries"
    root.mkdir(parents=True, exist_ok=True)
    return root


def install(package: str, *, upgrade: bool = False) -> None:
    """Install through the current interpreter; subprocess avoids pip internals."""
    if is_frozen():
        from .runtime_manager import find_manager
        command=[find_manager(),"exec","-V:default","-m","pip","install","--target",str(package_store())]
    else:
        command = [sys.executable, "-m", "pip", "install"]
    if upgrade:
        command.append("--upgrade")
    command.append(package)
    subprocess.run(command, check=True)


def uninstall(package: str) -> None:
    """Remove a distribution through pip."""
    if is_frozen():
        from .runtime_manager import find_manager
        env=__import__("os").environ.copy()
        env["PYTHONPATH"]=str(package_store())+__import__("os").pathsep+env.get("PYTHONPATH","")
        command=[find_manager(),"exec","-V:default","-m","pip","uninstall","-y",package]
        subprocess.run(command,check=True,env=env)
    else:
        subprocess.run([sys.executable,"-m","pip","uninstall","-y",package],check=True)


def _public_names(path: Path) -> set[str]:
    names: set[str] = set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError):
        return names
    explicit_all: set[str] = set()
    def collect_node(node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                names.add(node.name)
            # Public methods and nested public API classes are part of the
            # spelling surface too (for example tkinter's title/mainloop).
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    collect_node(child)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                exposed = alias.asname or alias.name.split(".")[0]
                if exposed != "*" and not exposed.startswith("_"):
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
    for node in tree.body:
        collect_node(node)
    return explicit_all or names


def _deep_public_names(module: str, timeout: int = 30) -> set[str]:
    """Inspect extension/dynamic exports in an isolated child interpreter."""
    if is_frozen():
        from .runtime_manager import find_manager
        command = [
            find_manager(), "exec", "-V:default", "-c", _DEEP_SCAN_SCRIPT,
            module, str(package_store()),
        ]
    else:
        command = [sys.executable, "-I", "-c", _DEEP_SCAN_SCRIPT, module, ""]
    result = subprocess.run(
        command, text=True, capture_output=True, errors="replace", timeout=timeout
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise RuntimeError(
            "패키지 심층 API 분석 실패: " + (detail[-1] if detail else module)
        )
    marker = next(
        (line.removeprefix("__HYTHON_API__") for line in result.stdout.splitlines()
         if line.startswith("__HYTHON_API__")),
        None,
    )
    if marker is None:
        raise RuntimeError("패키지 심층 API 분석 결과를 읽을 수 없습니다.")
    payload = json.loads(marker)
    return {name for name in payload if isinstance(name, str)}


def _unique_spellings(
    names: set[str], reserved: dict[str, str] | None = None
) -> dict[str, str]:
    """Give every public API a deterministic, collision-free Hangul spelling."""
    result: dict[str, str] = {}
    occupied: dict[str, str] = dict(reserved or {})
    for name in sorted(names, key=lambda item: (pronounce_identifier(item), item)):
        base = pronounce_identifier(name)
        spoken = base
        suffix = 2
        while spoken in occupied and occupied[spoken] != name:
            spoken = f"{base}{suffix}"
            suffix += 1
        result[name] = spoken
        occupied[spoken] = name
    return result


def scan(module: str, *, deep: bool = False) -> Path:
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
    # The module spelling itself must be translatable in an import statement.
    names: set[str] = {part for part in module.split(".") if not part.startswith("_")}
    for file in files:
        names.update(_public_names(file))
    if deep:
        names.update(_deep_public_names(module))
    from .vocabulary import HYTHON_TO_PYTHON
    python_to_hython = _unique_spellings(
        names, load_dictionaries() | HYTHON_TO_PYTHON
    )
    payload = {
        "format": 1,
        "module": module,
        "scan_mode": "deep" if deep else "static",
        "distribution_version": _version_for(module),
        "python_to_hython": python_to_hython,
    }
    output = dictionary_dir() / f"{module.replace('.', '__')}.json"
    _atomic_json(output, payload)
    return output


def scan_standard_library() -> Path:
    """Build one collision-free dictionary for the active Python stdlib."""
    root = Path(sysconfig.get_paths()["stdlib"])
    names = {
        name for name in getattr(sys, "stdlib_module_names", ())
        if isinstance(name, str) and not name.startswith("_")
    }
    for file in root.rglob("*.py"):
        lowered = {part.lower() for part in file.parts}
        if "site-packages" in lowered or "dist-packages" in lowered:
            continue
        names.update(_public_names(file))
    from .vocabulary import HYTHON_TO_PYTHON
    spellings = _unique_spellings(names, load_dictionaries() | HYTHON_TO_PYTHON)
    output = dictionary_dir() / "_stdlib.json"
    _atomic_json(output, {
        "format": 1,
        "module": "__stdlib__",
        "scan_mode": "stdlib",
        "python_version": sys.version.split()[0],
        "python_to_hython": spellings,
    })
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
        if module == "__stdlib__":
            refreshed.append(scan_standard_library())
        elif _find_spec_static(module) is None:
            path.unlink(missing_ok=True)
            removed.append(path)
        else:
            refreshed.append(scan(module, deep=payload.get("scan_mode") == "deep"))
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
    global _DICTIONARY_CACHE_KEY, _DICTIONARY_CACHE
    paths = sorted(dictionary_dir().glob("*.json"))
    key = tuple(
        (str(path), stat.st_mtime_ns, stat.st_size)
        for path in paths
        if (stat := path.stat())
    )
    if key == _DICTIONARY_CACHE_KEY:
        return dict(_DICTIONARY_CACHE)
    result: dict[str, str] = {}
    for path in paths:
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
    _DICTIONARY_CACHE_KEY = key
    _DICTIONARY_CACHE = dict(result)
    return result


def load_python_dictionaries() -> dict[str, str]:
    """Load valid user dictionaries as Python-to-Hython mappings."""
    return {python: spoken for spoken, python in load_dictionaries().items()}
