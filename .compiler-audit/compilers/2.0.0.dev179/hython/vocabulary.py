"""Canonical Hython vocabulary.

The spellings deliberately follow pronunciation rather than Korean meaning.
Aliases can be accepted, but reverse translation always emits the canonical form.
"""

import builtins as _python_builtins

from .phonetics import pronounce_identifier

KEYWORDS: dict[str, str] = {
    "False": "폴스", "None": "넌", "True": "트루",
    "and": "앤드", "as": "애즈", "assert": "어설트",
    "async": "어싱크", "await": "어웨이트", "break": "브레이크",
    "class": "클래스", "continue": "컨티뉴", "def": "데프",
    "del": "델", "elif": "엘리프", "else": "엘스",
    "except": "익셉트", "finally": "파이널리", "for": "포",
    "from": "프롬", "global": "글로벌", "if": "이프",
    "import": "인폴트", "in": "인", "is": "이즈",
    "lambda": "람다", "nonlocal": "논로컬", "not": "낫",
    "or": "오어", "pass": "패스", "raise": "레이즈",
    "return": "리턴", "try": "트라이", "while": "와일",
    "with": "위드", "yield": "일드", "match": "매치",
    "case": "케이스", "type": "타입",
}

BUILTINS: dict[str, str] = {
    "print": "프린트", "input": "인풋", "len": "렌",
    "range": "레인지", "str": "스트링", "int": "인트",
    "float": "플로트", "bool": "불", "list": "리스트",
    "dict": "딕트", "set": "셋", "tuple": "튜플",
    "open": "오픈", "enumerate": "이뉴머레이트", "zip": "집",
    "map": "맵", "filter": "필터", "sum": "썸", "min": "민",
    "max": "맥스", "abs": "앱스", "round": "라운드",
    "sorted": "소티드", "reversed": "리버스드", "super": "수퍼",
    "object": "오브젝트", "property": "프로퍼티",
    "staticmethod": "스태틱메서드", "classmethod": "클래스메서드",
    "isinstance": "이즈인스턴스", "issubclass": "이즈서브클래스",
    "getattr": "겟애트리뷰트", "setattr": "셋애트리뷰트", "hasattr": "해즈애트리뷰트",
    "metaclass": "메타클래스",
    "Exception": "익셉션", "ExceptionGroup": "익셉션그룹", "BaseExceptionGroup": "베이스익셉션그룹", "ValueError": "밸류에러",
    "TypeError": "타입에러", "NameError": "네임에러",
    "AssertionError": "어설션에러",
    "next": "넥스트",
    "any": "애니", "all": "올",
    "aiter": "에이터", "anext": "에이넥스트",
    "ascii": "아스키", "bin": "빈", "breakpoint": "브레이크포인트",
    "bytearray": "바이트어레이", "bytes": "바이츠", "callable": "콜러블",
    "chr": "씨에이치알", "compile": "컴파일", "complex": "컴플렉스",
    "delattr": "델애트리뷰트", "dir": "디어", "divmod": "디브모드",
    "eval": "이밸", "exec": "이그젝", "format": "포맷",
    "frozenset": "프로즌셋", "globals": "글로벌스", "hash": "해시",
    "help": "헬프", "hex": "헥스", "id": "아이디", "iter": "이터",
    "locals": "로컬스", "memoryview": "메모리뷰", "oct": "옥트",
    "ord": "오드", "pow": "파우", "repr": "레퍼", "slice": "슬라이스",
    "vars": "바스",
    "BaseException": "베이스익셉션", "ArithmeticError": "어리스메틱에러",
    "AttributeError": "애트리뷰트에러", "ImportError": "인폴트에러",
    "ModuleNotFoundError": "모듈낫파운드에러", "IndexError": "인덱스에러",
    "KeyError": "키에러", "LookupError": "룩업에러", "MemoryError": "메모리에러",
    "NotImplementedError": "낫임플리멘티드에러", "OSError": "오에스에러",
    "OverflowError": "오버플로에러", "RecursionError": "리커전에러",
    "ReferenceError": "레퍼런스에러", "RuntimeError": "런타임에러",
    "StopIteration": "스톱이터레이션", "SyntaxError": "신택스에러",
    "SystemError": "시스템에러", "SystemExit": "시스템엑시트",
    "UnboundLocalError": "언바운드로컬에러", "UnicodeError": "유니코드에러",
    "ZeroDivisionError": "제로디비전에러", "GeneratorExit": "제너레이터엑시트",
    "KeyboardInterrupt": "키보드인터럽트", "NotImplemented": "낫임플리멘티드",
    "asyncio_run": "어싱크실행",
    "StopAsyncIteration": "스톱어싱크이터레이션",
}

# Explicit spellings remain canonical. Public builtins introduced by newer
# Python releases automatically receive a deterministic phonetic spelling.
for _name in dir(_python_builtins):
    if not _name.startswith("_") and _name not in KEYWORDS:
        BUILTINS.setdefault(_name, pronounce_identifier(_name))

PYTHON_TO_HYTHON = KEYWORDS | BUILTINS
HYTHON_TO_PYTHON = {spoken: python for python, spoken in PYTHON_TO_HYTHON.items()}

# Accepted conveniences which are not emitted by to_hython().
HYTHON_TO_PYTHON.update({"임포트": "import", "널": "None"})
