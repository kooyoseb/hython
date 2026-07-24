"""Verified, side-by-side Hython compiler updates.

The installed bootstrap package is never overwritten.  A verified wheel is
expanded below HYTHON_HOME and selected by re-executing Hython with that tree
at the front of PYTHONPATH.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from . import __version__
from .environment import external_source_root, is_frozen

PYPI_URL = "https://pypi.org/pypi/hython-lang/json"


class CompilerUpdateError(RuntimeError):
    pass


def compiler_root() -> Path:
    root=Path(os.environ.get("HYTHON_HOME",Path.home()/".hython"))/"compilers"
    root.mkdir(parents=True,exist_ok=True)
    return root


def state_path() -> Path:
    return compiler_root()/"state.json"


def load_state() -> dict:
    try:
        payload=json.loads(state_path().read_text(encoding="utf-8"))
        if payload.get("format") != 1:
            return {"format":1,"active":None,"history":[]}
        return payload
    except (OSError,UnicodeError,json.JSONDecodeError):
        return {"format":1,"active":None,"history":[]}


def active_version() -> str | None:
    value=load_state().get("active")
    return value if isinstance(value,str) and (compiler_root()/value).is_dir() else None


def _version_key(value: str) -> tuple:
    match=re.match(r"^(\d+)\.(\d+)\.(\d+)(?:(?:[.-]?dev)(\d+))?",value)
    if not match:
        return (-1,value)
    major,minor,patch,dev=match.groups()
    return (int(major),int(minor),int(patch),1 if dev is None else 0,int(dev or 0))


def query_latest(*, url: str = PYPI_URL, timeout: int = 20) -> dict:
    if not url.lower().startswith("https://"):
        raise CompilerUpdateError("컴파일러 인덱스는 HTTPS 주소여야 합니다.")
    request=urllib.request.Request(url,headers={"User-Agent":f"hython/{__version__}"})
    try:
        with urllib.request.urlopen(request,timeout=timeout) as response:
            payload=json.load(response)
    except (OSError,ValueError) as exc:
        raise CompilerUpdateError(f"컴파일러 인덱스 조회 실패: {exc}") from exc
    version=payload.get("info",{}).get("version")
    files=payload.get("releases",{}).get(version,[]) if isinstance(version,str) else []
    candidates=[item for item in files if isinstance(item,dict) and item.get("packagetype")=="bdist_wheel"]
    universal=[item for item in candidates if str(item.get("filename","")).endswith("py3-none-any.whl")]
    candidates=universal or candidates
    if not version or not candidates:
        raise CompilerUpdateError("설치 가능한 공식 Hython compiler wheel이 없습니다.")
    item=candidates[0]
    digest=item.get("digests",{}).get("sha256")
    artifact_url=item.get("url")
    if not isinstance(digest,str) or len(digest)!=64 or not isinstance(artifact_url,str) or not artifact_url.startswith("https://"):
        raise CompilerUpdateError("PyPI wheel의 SHA-256 메타데이터가 올바르지 않습니다.")
    return {"version":version,"url":artifact_url,"sha256":digest,"filename":item.get("filename")}


def check() -> dict:
    latest=query_latest()
    current=active_version() or __version__
    latest["current"]=current
    latest["update_available"]=_version_key(latest["version"])>_version_key(current)
    return latest


def _download(url: str, destination: Path, *, timeout: int = 60) -> None:
    request=urllib.request.Request(url,headers={"User-Agent":f"hython/{__version__}"})
    try:
        with urllib.request.urlopen(request,timeout=timeout) as response, destination.open("wb") as output:
            shutil.copyfileobj(response,output)
    except OSError as exc:
        raise CompilerUpdateError(f"compiler wheel 다운로드 실패: {exc}") from exc


def _safe_extract(wheel: Path, destination: Path) -> None:
    try:
        with zipfile.ZipFile(wheel) as archive:
            root=destination.resolve()
            for member in archive.infolist():
                target=(destination/member.filename).resolve()
                if target!=root and root not in target.parents:
                    raise CompilerUpdateError("wheel에 안전하지 않은 경로가 포함되어 있습니다.")
                if member.is_dir():
                    target.mkdir(parents=True,exist_ok=True)
                else:
                    target.parent.mkdir(parents=True,exist_ok=True)
                    with archive.open(member) as source,target.open("wb") as output:
                        shutil.copyfileobj(source,output)
    except (OSError,zipfile.BadZipFile) as exc:
        raise CompilerUpdateError(f"compiler wheel 압축 해제 실패: {exc}") from exc


def _smoke_test(path: Path, version: str) -> None:
    env=os.environ.copy()
    env["PYTHONPATH"]=str(path)
    env["HYTHON_COMPILER_ACTIVE"]=version
    script=(
        "import pathlib,hython; from hython.compiler import compile_source; "
        "from hython.bytecode import dumps,loads; "
        "p=pathlib.Path(hython.__file__).resolve(); root=pathlib.Path(r'"+str(path).replace("'","''")+"').resolve(); "
        "assert root in p.parents; dumps(loads(dumps(compile_source('값 = 1 + 2'))))"
    )
    result=subprocess.run([sys.executable,"-c",script],env=env,capture_output=True,text=True,timeout=30)
    if result.returncode:
        detail=(result.stderr or result.stdout).strip().splitlines()[-1:] or ["알 수 없는 오류"]
        raise CompilerUpdateError(f"새 컴파일러 smoke test 실패: {detail[0]}")


def install_wheel(wheel: Path, *, version: str, sha256: str) -> Path:
    actual=hashlib.sha256(wheel.read_bytes()).hexdigest()
    if not __import__("hmac").compare_digest(actual.lower(),sha256.lower()):
        raise CompilerUpdateError("compiler wheel SHA-256 검증 실패")
    root=compiler_root(); final=root/version
    staging=Path(tempfile.mkdtemp(prefix=f".{version}-",dir=root))
    try:
        _safe_extract(wheel,staging)
        _smoke_test(staging,version)
        if final.exists():
            shutil.rmtree(final)
        staging.replace(final)
    except BaseException:
        shutil.rmtree(staging,ignore_errors=True)
        raise
    _activate(version)
    return final


def update(*, force: bool = False) -> dict:
    release=check()
    if not release["update_available"] and not force:
        return release|{"installed":False}
    with tempfile.TemporaryDirectory(prefix="hython-compiler-download-") as directory:
        wheel=Path(directory)/(release.get("filename") or "compiler.whl")
        _download(release["url"],wheel)
        install_wheel(wheel,version=release["version"],sha256=release["sha256"])
    return release|{"installed":True}


def _activate(version: str | None) -> None:
    state=load_state(); previous=state.get("active"); history=list(state.get("history",[]))
    if previous and previous!=version:
        history=[item for item in history if item!=previous]+[previous]
    state={"format":1,"active":version,"history":history[-10:]}
    _atomic_json(state_path(),state)


def rollback() -> str | None:
    state=load_state(); history=list(state.get("history",[]))
    while history:
        version=history.pop()
        if (compiler_root()/version).is_dir():
            _atomic_json(state_path(),{"format":1,"active":version,"history":history})
            return version
    _activate(None)
    return None


def remove(version: str | None = None) -> str:
    state=load_state(); target=version or state.get("active")
    if not isinstance(target,str) or not target:
        raise CompilerUpdateError("삭제할 외부 컴파일러가 없습니다.")
    if state.get("active")==target:
        rollback()
    path=compiler_root()/target
    shutil.rmtree(path,ignore_errors=True)
    state=load_state()
    state["history"]=[item for item in state.get("history",[]) if item!=target]
    _atomic_json(state_path(),state)
    return target


def reexec_with_active(argv: list[str]) -> None:
    version=active_version()
    if not version or os.environ.get("HYTHON_COMPILER_ACTIVE")==version:
        return
    env=os.environ.copy(); env["HYTHON_COMPILER_ACTIVE"]=version
    env["PYTHONPATH"]=str(compiler_root()/version)+os.pathsep+str(external_source_root())+os.pathsep+env.get("PYTHONPATH","")
    if is_frozen():
        from .runtime_manager import find_manager
        command=[find_manager(),"exec","-V:default","-m","hython",*argv]
    else:
        command=[sys.executable,"-m","hython",*argv]
    result=subprocess.run(command,env=env)
    raise SystemExit(result.returncode)


def _atomic_json(output: Path, payload: dict) -> None:
    handle,temporary=tempfile.mkstemp(prefix=output.name+".",suffix=".tmp",dir=output.parent)
    try:
        with os.fdopen(handle,"w",encoding="utf-8",newline="\n") as stream:
            json.dump(payload,stream,ensure_ascii=False,indent=2); stream.write("\n")
            stream.flush(); os.fsync(stream.fileno())
        Path(temporary).replace(output)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
