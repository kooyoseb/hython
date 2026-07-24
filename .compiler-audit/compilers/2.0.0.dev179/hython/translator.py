"""Token-safe translation between Hython and Python."""

from __future__ import annotations

import io
import tokenize
from collections.abc import Mapping

from .vocabulary import HYTHON_TO_PYTHON, PYTHON_TO_HYTHON


def _hython_names() -> dict[str, str]:
    # Lazy import keeps startup cheap and allows newly generated dictionaries to
    # become active without restarting a long-running process.
    from .package_manager import load_dictionaries
    from .runtime import load_runtime_spellings
    # Core syntax wins if an untrusted/generated package dictionary collides.
    return load_dictionaries() | load_runtime_spellings() | HYTHON_TO_PYTHON


def _python_names() -> dict[str, str]:
    from .package_manager import load_python_dictionaries
    from .runtime import load_runtime_spellings
    runtime = {python: spoken for spoken, python in load_runtime_spellings().items()}
    return load_python_dictionaries() | runtime | PYTHON_TO_HYTHON


class TranslationError(SyntaxError):
    """Raised when a source stream cannot be tokenized."""


def _translate(source: str, names: Mapping[str, str]) -> str:
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError) as exc:
        raise TranslationError(str(exc)) from exc

    changed = [
        token._replace(string=names.get(token.string, token.string))
        if token.type == tokenize.NAME
        else token
        for token in tokens
    ]
    return tokenize.untokenize(changed)


def to_python(source: str) -> str:
    """Translate Hython source to executable Python without touching text/comments."""
    return _translate(source, _hython_names())


def to_hython(source: str) -> str:
    """Translate supported Python names to canonical Hython spellings."""
    return _translate(source, _python_names())


def compile_hython(source: str, filename: str = "<하이썬>", mode: str = "exec"):
    """Translate and compile Hython source."""
    return compile(to_python(source), filename, mode)
