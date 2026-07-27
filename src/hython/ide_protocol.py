"""Stable JSON protocol consumed by Hython-aware editors."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

from . import __version__
from .diagnostics import exception_name, translated_message
from .package_manager import load_dictionaries
from .runtime import load_runtime_spellings
from .translator import to_python
from .vocabulary import BUILTINS, KEYWORDS, LIBRARY_NAMES, SPECIAL_NAMES


def _completion_items() -> list[dict[str, str]]:
    generated = load_dictionaries()
    runtime = load_runtime_spellings()
    groups = (
        ("키워드", KEYWORDS.values()),
        ("내장", BUILTINS.values()),
        ("라이브러리", LIBRARY_NAMES.values()),
        ("특수 이름", SPECIAL_NAMES.values()),
        ("설치 패키지", generated.keys()),
        ("런타임", runtime.keys()),
    )
    seen: set[str] = set()
    result = []
    for kind, names in groups:
        for name in sorted(names):
            if name in seen:
                continue
            seen.add(name)
            result.append({"label": name, "kind": kind, "insertText": name})
    return result


def completions(source: str, line: int, column: int) -> dict[str, Any]:
    lines = source.splitlines()
    current = lines[line - 1] if 0 < line <= len(lines) else ""
    column = max(0, min(column, len(current)))
    match = re.search(r"[\w가-힣_]*$", current[:column])
    prefix = match.group(0) if match else ""
    items = [
        item for item in _completion_items()
        if not prefix or item["label"].startswith(prefix)
    ]
    return {"prefix": prefix, "items": items[:250]}


def diagnostics(source: str, filename: str) -> list[dict[str, Any]]:
    try:
        compile(to_python(source), filename, "exec")
    except (SyntaxError, IndentationError) as error:
        return [{
            "severity": "error",
            "message": f"{exception_name(error)}: {translated_message(error)}",
            "line": error.lineno or 1,
            "column": max((error.offset or 1) - 1, 0),
            "endLine": getattr(error, "end_lineno", None) or error.lineno or 1,
            "endColumn": max((getattr(error, "end_offset", None) or error.offset or 1) - 1, 0),
        }]
    except BaseException as error:
        return [{
            "severity": "error", "message": str(error),
            "line": 1, "column": 0, "endLine": 1, "endColumn": 1,
        }]
    return []


def symbols(source: str, filename: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(to_python(source), filename)
    except SyntaxError:
        return []
    kinds = {
        ast.FunctionDef: "함수", ast.AsyncFunctionDef: "비동기 함수",
        ast.ClassDef: "클래스",
    }
    result = []
    for node in ast.walk(tree):
        kind = next((label for cls, label in kinds.items() if isinstance(node, cls)), None)
        if kind:
            result.append({
                "name": node.name, "kind": kind,
                "line": node.lineno, "column": node.col_offset,
            })
    return sorted(result, key=lambda item: (item["line"], item["column"]))


def analyze_source(
    source: str, filename: str, *, line: int = 1, column: int = 0
) -> dict[str, Any]:
    source = source.lstrip("\ufeff")
    return {
        "protocolVersion": 1,
        "hythonVersion": __version__,
        "file": filename,
        "diagnostics": diagnostics(source, filename),
        "symbols": symbols(source, filename),
        "completions": completions(source, line, column),
    }


def analyze_file(path: Path, *, line: int = 1, column: int = 0) -> dict[str, Any]:
    return analyze_source(
        path.read_text(encoding="utf-8-sig"), str(path.resolve()),
        line=line, column=column,
    )


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
