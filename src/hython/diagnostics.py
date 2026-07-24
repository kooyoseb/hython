"""Korean user-facing exception and traceback formatting."""

from __future__ import annotations

import re
import traceback
import subprocess
from pathlib import Path


TYPE_NAMES={
    SyntaxError:"문법 오류",IndentationError:"들여쓰기 오류",TabError:"탭/공백 오류",
    NameError:"이름 오류",UnboundLocalError:"지역 이름 오류",TypeError:"형식 오류",
    ValueError:"값 오류",AttributeError:"속성 오류",ImportError:"가져오기 오류",
    ModuleNotFoundError:"모듈 없음 오류",KeyError:"키 오류",IndexError:"인덱스 오류",
    ZeroDivisionError:"0 나누기 오류",FileNotFoundError:"파일 없음 오류",
    PermissionError:"권한 오류",IsADirectoryError:"디렉터리 오류",NotADirectoryError:"경로 오류",
    AssertionError:"검증 실패",RuntimeError:"실행 오류",RecursionError:"재귀 한도 오류",
    OverflowError:"범위 초과 오류",MemoryError:"메모리 부족 오류",
    NotImplementedError:"미구현 오류",TimeoutError:"시간 초과 오류",
    EOFError:"입력 종료 오류",OSError:"운영체제 오류",
    BaseExceptionGroup:"예외 묶음",
}


def exception_name(error: BaseException) -> str:
    for cls in type(error).__mro__:
        if cls in TYPE_NAMES:
            return TYPE_NAMES[cls]
    return type(error).__name__


def _replace(message: str, pattern: str, replacement: str) -> str | None:
    match=re.fullmatch(pattern,message)
    return match.expand(replacement) if match else None


def translated_message(error: BaseException) -> str:
    message=str(getattr(error,"msg",error)) if isinstance(error,SyntaxError) else str(error)
    if isinstance(error,FileNotFoundError):
        target=getattr(error,"filename",None)
        return f"파일을 찾을 수 없습니다: {target}" if target else "파일을 찾을 수 없습니다."
    if isinstance(error,PermissionError):
        target=getattr(error,"filename",None)
        return f"접근 권한이 없습니다: {target}" if target else "접근 권한이 없습니다."
    if isinstance(error,subprocess.CalledProcessError):
        return f"외부 명령이 종료 코드 {error.returncode}로 실패했습니다."
    if isinstance(error,ModuleNotFoundError):
        name=getattr(error,"name",None)
        return f"모듈을 찾을 수 없습니다: {name}" if name else "모듈을 찾을 수 없습니다."
    if isinstance(error,KeyError):
        return f"키를 찾을 수 없습니다: {error.args[0]!r}" if error.args else "키를 찾을 수 없습니다."
    if isinstance(error,AssertionError) and not message:
        return "검증 조건이 참이 아닙니다."
    patterns=[]
    if isinstance(error,(NameError,UnboundLocalError)):
        patterns=[
            (r"name '([^']+)' is not defined",r"이름 '\1'이 정의되지 않았습니다."),
            (r"cannot access local variable '([^']+)' where it is not associated with a value",r"지역 변수 '\1'에 값이 연결되기 전에 접근했습니다."),
        ]
    elif isinstance(error,AttributeError):
        patterns=[(r"'([^']+)' object has no attribute '([^']+)'",r"'\1' 객체에 '\2' 속성이 없습니다."),
                  (r"module '([^']+)' has no attribute '([^']+)'",r"'\1' 모듈에 '\2' 속성이 없습니다.")]
    elif isinstance(error,ImportError):
        patterns=[(r"cannot import name '([^']+)' from '([^']+)'.*",r"'\2'에서 이름 '\1'을 가져올 수 없습니다.")]
    elif isinstance(error,IndexError):
        patterns=[(r"list index out of range",r"리스트 인덱스가 범위를 벗어났습니다."),
                  (r"tuple index out of range",r"튜플 인덱스가 범위를 벗어났습니다."),
                  (r"string index out of range",r"문자열 인덱스가 범위를 벗어났습니다.")]
    elif isinstance(error,ZeroDivisionError):
        patterns=[(r"division by zero",r"0으로 나눌 수 없습니다."),
                  (r"integer division or modulo by zero",r"0으로 정수 나눗셈 또는 나머지 연산을 할 수 없습니다."),
                  (r"float division by zero",r"부동소수점 수를 0으로 나눌 수 없습니다."),
                  (r"complex division by zero",r"복소수를 0으로 나눌 수 없습니다.")]
    elif isinstance(error,TypeError):
        patterns=[
            (r"'([^']+)' object is not callable",r"'\1' 객체는 호출할 수 없습니다."),
            (r"'([^']+)' object is not iterable",r"'\1' 객체는 반복할 수 없습니다."),
            (r"'([^']+)' object is not subscriptable",r"'\1' 객체는 첨자로 접근할 수 없습니다."),
            (r"unsupported operand type\(s\) for (.+): '([^']+)' and '([^']+)'",r"연산자 \1은 '\2'와 '\3' 형식에 사용할 수 없습니다."),
            (r"(.+) got an unexpected keyword argument '([^']+)'",r"\1에 예상하지 않은 키워드 인자 '\2'이 전달되었습니다."),
            (r"(.+) got multiple values for argument '([^']+)'",r"\1의 인자 '\2'에 값이 여러 번 전달되었습니다."),
            (r"(.+) missing (\d+) required positional argument(?:s)?: (.+)",r"\1에 필수 위치 인자 \2개가 없습니다: \3"),
        ]
    elif isinstance(error,SyntaxError):
        patterns=[(r"invalid syntax",r"잘못된 문법입니다."),(r"unexpected EOF while parsing",r"코드가 끝나기 전에 문법이 완성되지 않았습니다."),
                  (r"expected '([^']+)'",r"'\1'이 필요합니다."),(r"unmatched '([^']+)'",r"짝이 맞지 않는 '\1'가 있습니다."),
                  (r"unterminated (.+)",r"닫히지 않은 \1입니다.")]
    elif isinstance(error,RecursionError):
        patterns=[(r"maximum recursion depth exceeded.*",r"최대 재귀 깊이를 초과했습니다.")]
    for pattern,replacement in patterns:
        result=_replace(message,pattern,replacement)
        if result is not None:
            return result
    return message or exception_name(error)


def _user_frames(error: BaseException) -> list[traceback.FrameSummary]:
    frames=list(traceback.extract_tb(error.__traceback__))
    package=Path(__file__).resolve().parent
    visible=[]
    for frame in frames:
        normalized=frame.filename.replace("\\","/")
        try:
            internal=Path(frame.filename).resolve().is_relative_to(package)
        except (OSError,ValueError):
            internal=False
        internal=internal or normalized.startswith("hython/") or "/hython/" in normalized
        internal=internal or Path(normalized).name in {"code.py","codeop.py"}
        if not internal or frame.filename.startswith("<") or frame.filename.endswith((".hy",".hbc")):
            visible.append(frame)
    return visible


def _single(error: BaseException, *, indent: str = "", traceback_enabled: bool = True) -> list[str]:
    lines=[]
    if isinstance(error,SyntaxError) and getattr(error,"lineno",None):
        lines.append(indent+f'  파일 "{error.filename or "<하이썬>"}", 줄 {error.lineno}')
        source=(error.text or "").rstrip("\r\n")
        if source:
            lines.append(indent+"    "+source)
            if error.offset:
                end=max(error.offset,getattr(error,"end_offset",error.offset) or error.offset)
                lines.append(indent+"    "+" "*(max(error.offset-1,0))+"^"*max(end-error.offset,1))
    if traceback_enabled:
        frames=_user_frames(error)
        if frames:
            lines.append(indent+"하이썬 추적 (가장 최근 호출이 마지막):")
            for frame in frames:
                lines.append(indent+f'  파일 "{frame.filename}", 줄 {frame.lineno}, 함수 {frame.name}')
                if frame.line: lines.append(indent+"    "+frame.line.strip())
    lines.append(indent+f"{exception_name(error)}: {translated_message(error)}")
    for note in getattr(error,"__notes__",()) or ():
        lines.append(indent+f"  참고: {note}")
    return lines


def format_exception(error: BaseException, *, traceback_enabled: bool = True) -> str:
    """Format chaining and exception groups without exposing Hython internals."""
    lines=[]; seen=set()
    def render(current: BaseException,indent=""):
        if id(current) in seen: return
        seen.add(id(current))
        cause=current.__cause__
        context=current.__context__ if not current.__suppress_context__ else None
        if cause is not None:
            render(cause,indent); lines.append(indent+"위 오류가 다음 오류의 직접 원인입니다:")
        elif context is not None:
            render(context,indent); lines.append(indent+"위 오류를 처리하는 동안 다른 오류가 발생했습니다:")
        if isinstance(current,BaseExceptionGroup):
            lines.extend(_single(current,indent=indent,traceback_enabled=traceback_enabled))
            for index,child in enumerate(current.exceptions,1):
                lines.append(indent+f"  하위 오류 {index}:")
                render(child,indent+"    ")
        else:
            lines.extend(_single(current,indent=indent,traceback_enabled=traceback_enabled))
    render(error)
    return "\n".join(lines)
