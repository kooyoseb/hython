"""Reproducibly build and smoke-test the standalone Windows Hython CLI."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"src"
sys.path.insert(0,str(SRC))

from hython import __version__
from hython.exe_builder import _version_source


def run(command: list[str], *, timeout: int = 300, env: dict[str,str] | None = None) -> None:
    result=subprocess.run(command,cwd=ROOT,timeout=timeout,env=env)
    if result.returncode:
        raise SystemExit(result.returncode)


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="standalone Hython EXE builder")
    parser.add_argument("--output-dir",type=Path,default=ROOT/"release")
    parser.add_argument("--onedir",action="store_true")
    parser.add_argument("--skip-tests",action="store_true")
    ns=parser.parse_args(argv)
    if os.name!="nt":
        parser.error("Windows에서만 Hython EXE를 빌드할 수 있습니다.")
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        parser.error('PyInstaller가 필요합니다: pip install "hython-lang[exe]"')
    output=ns.output_dir.resolve(); output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hython-self-build-") as directory:
        work=Path(directory); version_file=work/"version_info.txt"
        match=re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-dev(\d+))?",__version__)
        numeric=".".join((*match.groups()[:3],match.group(4) or "0")) if match else "1.0.0.0"
        version_file.write_text(_version_source({
            "version":numeric,"name":"hython","product":"Hython Programming Language",
            "company":"Hython contributors","description":"Hython compiler, VM and package toolchain",
            "copyright":"MIT License","filename":"hython.exe",
        }),encoding="utf-8")
        command=[sys.executable,"-m","PyInstaller","--noconfirm","--clean",
                 "--onedir" if ns.onedir else "--onefile","--console","--name","hython",
                 "--icon",str(ROOT/"assets"/"hython.ico"),"--version-file",str(version_file),
                 "--paths",str(SRC),"--collect-all","hython",
                 "--add-data",f"{SRC/'hython'}{os.pathsep}hython_source/hython",
                 "--distpath",str(work/"dist"),"--workpath",str(work/"build"),
                 "--specpath",str(work/"spec"),str(ROOT/"scripts"/"hython_frozen_launcher.py")]
        run(command)
        built=(work/"dist"/"hython"/"hython.exe") if ns.onedir else (work/"dist"/"hython.exe")
        artifact=output/("hython" if ns.onedir else "hython.exe")
        if artifact.exists():
            shutil.rmtree(artifact) if artifact.is_dir() else artifact.unlink()
        shutil.copytree(built.parent,artifact) if ns.onedir else shutil.copy2(built,artifact)
    executable=artifact/"hython.exe" if artifact.is_dir() else artifact
    digest=hashlib.sha256(executable.read_bytes()).hexdigest()
    checksum=output/"hython.exe.sha256"
    checksum.write_text(f"{digest}  hython.exe\n",encoding="ascii")
    if not ns.skip_tests:
        with tempfile.TemporaryDirectory(prefix="hython-self-smoke-") as smoke_directory:
            smoke=Path(smoke_directory); env=os.environ.copy(); env["HYTHON_HOME"]=str(smoke/"home")
            hbc=smoke/"program.hbc"
            run([str(executable),"--version"],timeout=60,env=env)
            run([str(executable),"doctor"],timeout=60,env=env)
            run([str(executable),"runtime","info"],timeout=60,env=env)
            run([str(executable),"compiler","info"],timeout=60,env=env)
            run([str(executable),"package","scan","pathlib"],timeout=60,env=env)
            run([str(executable),"compile",str(ROOT/"examples"/"컴파일.hy"),"-o",str(hbc)],timeout=60,env=env)
            run([str(executable),"execute",str(hbc)],timeout=60,env=env)
    print(f"Hython EXE: {executable}")
    print(f"SHA-256: {checksum}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
