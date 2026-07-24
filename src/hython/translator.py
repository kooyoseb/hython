"""Token-safe translation between Hython and Python."""

from __future__ import annotations

import io
import re
import tokenize
from dataclasses import dataclass
from collections.abc import Mapping

from .phonetics import pronounce_identifier
from .vocabulary import (
    BUILTINS, KEYWORDS, LIBRARY_NAMES, SPECIAL_NAMES,
    HYTHON_TO_PYTHON, PYTHON_TO_HYTHON,
)

LITERAL_PREFIXES = {
    "에프": "f", "알": "r", "비": "b", "유": "u",
    "알에프": "rf", "에프알": "fr", "비알": "br", "알비": "rb",
}
PYTHON_LITERAL_PREFIXES = {
    python: hython for hython, python in LITERAL_PREFIXES.items()
}


def normalize_literal_prefixes(source: str) -> str:
    """Turn adjacent Hangul string prefixes into Python lexical prefixes."""
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError) as exc:
        raise TranslationError(str(exc)) from exc
    lines = source.splitlines(keepends=True)
    offsets: list[int] = []
    total = 0
    for line in lines:
        offsets.append(total)
        total += len(line)
    replacements: list[tuple[int, int, str]] = []
    for index, token in enumerate(tokens[:-1]):
        following = tokens[index + 1]
        if (
            token.type == tokenize.NAME
            and token.string in LITERAL_PREFIXES
            and following.type == tokenize.STRING
            and token.end == following.start
        ):
            start = offsets[token.start[0] - 1] + token.start[1]
            end = offsets[token.end[0] - 1] + token.end[1]
            replacements.append((start, end, LITERAL_PREFIXES[token.string]))
    for start, end, replacement in reversed(replacements):
        source = source[:start] + replacement + source[end:]
    return source


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


@dataclass(frozen=True)
class EnglishName:
    """One executable English identifier left in Hython source."""

    name: str
    line: int
    column: int
    suggestion: str


def _translate(source: str, names: Mapping[str, str], *, preserve_aliases: bool = False) -> str:
    source = normalize_literal_prefixes(source)
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError) as exc:
        raise TranslationError(str(exc)) from exc

    aliases = {
        tokens[index + 1].string
        for index, token in enumerate(tokens[:-1])
        if preserve_aliases and token.type == tokenize.NAME
        and token.string in ("as", "애즈")
        and tokens[index + 1].type == tokenize.NAME
    }
    changed = []
    for index, token in enumerate(tokens):
        # A Korean import alias is user-owned, but an identically spelled API
        # member after a dot still needs translation (티케이.티케이 -> 티케이.Tk).
        alias_reference = token.string in aliases and (
            index == 0 or tokens[index - 1].string != "."
        )
        changed.append(
            token._replace(string=names.get(token.string, token.string))
            if token.type == tokenize.NAME and not alias_reference
            else token
        )
    return tokenize.untokenize(changed)


def to_python(source: str) -> str:
    """Translate Hython source to executable Python without touching text/comments."""
    return _translate(source, _hython_names(), preserve_aliases=True)


def to_hython(source: str) -> str:
    """Translate supported Python names to canonical Hython spellings."""
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError) as exc:
        raise TranslationError(str(exc)) from exc
    from .runtime import load_runtime_spellings
    runtime = {
        python: spoken for spoken, python in load_runtime_spellings().items()
    }
    core = KEYWORDS | BUILTINS | SPECIAL_NAMES | runtime
    api = _python_names() | LIBRARY_NAMES
    imported: set[str] = set()
    in_import = False
    after_as = False
    import_contexts: list[bool] = []
    for token in tokens:
        if token.type in (tokenize.NEWLINE, tokenize.NL):
            in_import = False
            after_as = False
        elif token.type == tokenize.NAME:
            if token.string in ("import", "from"):
                in_import = True
            elif in_import and token.string == "as":
                after_as = True
            elif in_import and not after_as:
                imported.add(token.string)
            elif after_as:
                after_as = False
        import_contexts.append(in_import)
    changed = []
    for index, token in enumerate(tokens):
        previous = tokens[index - 1].string if index else ""
        import_context = import_contexts[index]
        if token.type == tokenize.NAME:
            if token.string in core:
                token = token._replace(string=core[token.string])
            elif (
                token.string in api
                and (previous == "." or import_context or token.string in imported)
            ):
                token = token._replace(string=api[token.string])
        changed.append(token)
    return tokenize.untokenize(changed)


def audit_english(source: str) -> list[EnglishName]:
    """Find ASCII identifiers in code while ignoring strings and comments."""
    known = _python_names()
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        result = [
            EnglishName(
                token.string,
                token.start[0],
                token.start[1] + 1,
                known.get(token.string, pronounce_identifier(token.string)),
            )
            for token in tokens
            if token.type == tokenize.NAME
            and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token.string)
        ]
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            prefix = ""
            if token.type == tokenize.STRING:
                match = re.match(r"(?i)(rf|fr|rb|br|r|f|b|u)(?=['\"])", token.string)
                prefix = match.group(1).lower() if match else ""
            elif token.type == getattr(tokenize, "FSTRING_START", -1):
                prefix = token.string[:-1].lower()
            if prefix in PYTHON_LITERAL_PREFIXES:
                result.append(EnglishName(
                    prefix, token.start[0], token.start[1] + 1,
                    PYTHON_LITERAL_PREFIXES[prefix],
                ))
        return result
    except (tokenize.TokenError, IndentationError) as exc:
        raise TranslationError(str(exc)) from exc


def koreanize(source: str) -> str:
    """Convert every ASCII code identifier to a deterministic Hangul spelling.

    Known Python/package API names use their registered spelling. Unknown names
    are treated as user identifiers, so renaming all their occurrences is safe.
    """
    known = _python_names()
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError) as exc:
        raise TranslationError(str(exc)) from exc
    reverse_names = _hython_names()
    generated: dict[str, str] = {}
    occupied = set(reverse_names)
    changed = []
    for token in tokens:
        if token.type == tokenize.NAME and re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", token.string
        ):
            spoken = known.get(token.string)
            if spoken is None:
                spoken = generated.get(token.string)
                if spoken is None:
                    base = pronounce_identifier(token.string)
                    spoken = base
                    suffix = 2
                    while spoken in occupied:
                        spoken = f"{base}{suffix}"
                        suffix += 1
                    generated[token.string] = spoken
                    occupied.add(spoken)
            token = token._replace(string=spoken)
        elif token.type in (tokenize.STRING, getattr(tokenize, "FSTRING_START", -1)):
            match = re.match(r"(?i)(rf|fr|rb|br|r|f|b|u)(?=['\"])", token.string)
            if match and match.group(1).lower() in PYTHON_LITERAL_PREFIXES:
                prefix = match.group(1)
                token = token._replace(
                    string=PYTHON_LITERAL_PREFIXES[prefix.lower()]
                    + token.string[len(prefix):]
                )
        changed.append(token)
    return tokenize.untokenize(changed)


def compile_hython(source: str, filename: str = "<하이썬>", mode: str = "exec"):
    """Translate and compile Hython source."""
    return compile(to_python(source), filename, mode)
