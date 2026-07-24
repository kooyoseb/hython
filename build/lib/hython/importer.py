"""Import hook for loading ``.hy`` source modules and packages."""

from __future__ import annotations

import importlib.abc
import importlib.machinery
import importlib.util
import sys
from pathlib import Path

from .translator import compile_hython


class HythonLoader(importlib.abc.SourceLoader):
    """Load a Hython source file as a normal Python module."""

    def __init__(self, fullname: str, path: Path) -> None:
        self.fullname = fullname
        self.path = path

    def get_filename(self, fullname: str) -> str:
        return str(self.path)

    def get_data(self, path: str) -> bytes:
        return Path(path).read_bytes()

    def get_code(self, fullname: str):
        source = self.path.read_text(encoding="utf-8-sig")
        return compile_hython(source, str(self.path))

    def set_data(self, path: str, data: bytes, *, _mode: int = 0o666) -> None:
        # Do not create misleading CPython .pyc cache files for Hython sources.
        return None


class HythonFinder(importlib.abc.MetaPathFinder):
    """Find ``name.hy`` and ``name/__init__.hy`` on the import path."""

    marker = "hython-finder-v1"

    def find_spec(self, fullname: str, path=None, target=None):
        name = fullname.rpartition(".")[2]
        search_paths = sys.path if path is None else path
        for entry in search_paths:
            base = Path(entry or ".")
            package_file = base / name / "__init__.hy"
            if package_file.is_file():
                loader = HythonLoader(fullname, package_file)
                return importlib.util.spec_from_file_location(
                    fullname,
                    package_file,
                    loader=loader,
                    submodule_search_locations=[str(package_file.parent)],
                )
            module_file = base / f"{name}.hy"
            if module_file.is_file():
                return importlib.util.spec_from_file_location(
                    fullname, module_file, loader=HythonLoader(fullname, module_file)
                )
        return None


def install_importer() -> HythonFinder:
    """Install the finder once, ahead of Python's normal path finder."""
    for finder in sys.meta_path:
        if isinstance(finder, HythonFinder):
            return finder
    finder = HythonFinder()
    sys.meta_path.insert(0, finder)
    return finder


def uninstall_importer() -> None:
    """Remove all installed Hython finders (mainly useful for tests)."""
    sys.meta_path[:] = [finder for finder in sys.meta_path if not isinstance(finder, HythonFinder)]

