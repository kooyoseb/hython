"""Deterministic English-identifier to Hangul phonetic approximation."""

from __future__ import annotations

import re

# Longest fragments are applied first. This is deliberately deterministic: users
# may edit generated dictionaries when a package's preferred pronunciation differs.
_SOUNDS = {
    "tion": "션", "sion": "전", "ough": "오", "ight": "아이트",
    "ph": "프", "sh": "시", "ch": "치", "th": "스", "wh": "우",
    "ck": "크", "qu": "쿠", "ng": "응", "ee": "이", "oo": "우",
    "ai": "에이", "ay": "에이", "ea": "이", "ou": "아우", "ow": "오우",
    "a": "아", "b": "브", "c": "크", "d": "드", "e": "에",
    "f": "프", "g": "그", "h": "흐", "i": "이", "j": "제이",
    "k": "크", "l": "르", "m": "므", "n": "느", "o": "오",
    "p": "프", "q": "큐", "r": "르", "s": "스", "t": "트",
    "u": "유", "v": "브", "w": "우", "x": "엑스", "y": "이",
    "z": "즈",
}
_PARTS = sorted(_SOUNDS, key=len, reverse=True)


def pronounce_word(word: str) -> str:
    """Return a stable Hangul approximation for one ASCII word."""
    result: list[str] = []
    lowered = word.lower()
    index = 0
    while index < len(lowered):
        if lowered[index].isdigit():
            result.append(lowered[index])
            index += 1
            continue
        for part in _PARTS:
            if lowered.startswith(part, index):
                result.append(_SOUNDS[part])
                index += len(part)
                break
        else:
            result.append(lowered[index])
            index += 1
    return "".join(result)


def pronounce_identifier(name: str) -> str:
    """Pronounce snake_case and CamelCase identifiers while preserving underscores."""
    expanded = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", name)
    expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", expanded)
    return "_".join(pronounce_word(part) for part in expanded.split("_"))
