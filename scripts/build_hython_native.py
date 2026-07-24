"""Compile the Hython language executable through Nuitka's C backend."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; SRC=ROOT/"src"
sys.path.insert(0,str(SRC))
from hython import __version__


def run(command: list[str],*,timeout=900,env=None,capture=False):
    result=subprocess.run(command,cwd=ROOT,timeout=timeout,env=env,text=True,capture_output=capture)
    if result.returncode:
        if capture: print(result.stdout); print(result.stderr,file=sys.stderr)
        raise SystemExit(result.returncode)
    return result


def numeric_version() -> str:
    match=re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-dev(\d+))?",__version__)
    return ".".join((*match.groups()[:3],match.group(4) or "0")) if match else "1.0.0.0"


def msvc_environment() -> dict[str,str]:
    vswhere=Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
    if not vswhere.is_file(): raise SystemExit("Visual Studio Build Tools vswhere.exe not found")
    result=subprocess.run([str(vswhere),"-latest","-products","*","-requires","Microsoft.VisualStudio.Component.VC.Tools.x86.x64","-property","installationPath"],capture_output=True,text=True)
    installation=Path(result.stdout.strip())
    developer=installation/"Common7"/"Tools"/"VsDevCmd.bat"
    if not developer.is_file(): raise SystemExit("Visual Studio C++ developer environment not found")
    with tempfile.TemporaryDirectory(prefix="hython-msvc-env-") as directory:
        wrapper=Path(directory)/"environment.bat"
        wrapper.write_text(f'@call "{developer}" -arch=x64 -host_arch=x64 >nul\n@set\n',encoding="utf-8")
        environment=subprocess.run(["cmd.exe","/d","/c",str(wrapper)],capture_output=True,text=True,encoding="utf-8",errors="replace",check=True).stdout
    values=os.environ.copy()
    for line in environment.splitlines():
        if "=" in line:
            key,value=line.split("=",1)
            if key.lower()=="path":
                for existing in list(values):
                    if existing.lower()=="path": values.pop(existing)
                key="PATH"
            values[key]=value
    return values


def main(argv=None):
    parser=argparse.ArgumentParser(description="C-compiled Hython executable builder")
    parser.add_argument("--output-dir",type=Path,default=ROOT/"release")
    parser.add_argument("--skip-tests",action="store_true")
    ns=parser.parse_args(argv)
    if os.name!="nt": parser.error("Windows native build only")
    try: import nuitka  # noqa: F401
    except ImportError: parser.error('Nuitka가 필요합니다: pip install ".[native]"')
    output=ns.output_dir.resolve(); output.mkdir(parents=True,exist_ok=True)
    build_env=msvc_environment(); build_env["PYTHONUTF8"]="1"; build_env["PYTHONIOENCODING"]="utf-8"
    for attempt in range(1,4):
        with tempfile.TemporaryDirectory(prefix="hython-native-build-") as directory:
            work=Path(directory); report=work/"nuitka-report.xml"
            command=[sys.executable,"-m","nuitka","--onefile","--standalone","--assume-yes-for-downloads",
                     "--msvc=latest","--output-dir="+str(work),"--output-filename=hython.exe",
                     "--include-package=hython","--include-data-files="+str(SRC/"hython"/"*.py")+"=hython_source/hython/",
                     "--nofollow-import-to=tkinter,_tkinter","--windows-console-mode=force",
                     "--windows-icon-from-ico="+str(ROOT/"assets"/"hython.ico"),
                     "--product-name=Hython Programming Language","--file-description=Hython C-compiled compiler and HBC VM",
                     "--company-name=Hython contributors","--copyright=MIT License",
                     "--file-version="+numeric_version(),"--product-version="+numeric_version(),
                     "--report="+str(report),str(ROOT/"scripts"/"hython_frozen_launcher.py")]
            result=subprocess.run(
                command,cwd=ROOT,timeout=900,env=build_env,text=True,
                capture_output=True,errors="replace",
            )
            print(result.stdout,end="")
            print(result.stderr,end="",file=sys.stderr)
            if result.returncode:
                resource_lock=(
                    "Failed to add resources" in result.stderr
                    or "error code 22" in result.stderr
                )
                if resource_lock and attempt<3:
                    print(f"[Hython] Windows resource lock; retrying C build ({attempt}/3)...")
                    continue
                raise SystemExit(result.returncode)
            built=work/"hython.exe"
            if not built.is_file(): raise SystemExit("Nuitka did not create hython.exe")
            temporary=output/"hython.exe.new"; shutil.copy2(built,temporary); temporary.replace(output/"hython.exe")
            if report.is_file(): shutil.copy2(report,output/"hython-native-report.xml")
            break
    executable=output/"hython.exe"; digest=hashlib.sha256(executable.read_bytes()).hexdigest()
    (output/"hython.exe.sha256").write_text(f"{digest}  hython.exe\n",encoding="ascii")
    if not ns.skip_tests:
        with tempfile.TemporaryDirectory(prefix="hython-native-smoke-") as directory:
            root=Path(directory); env=os.environ.copy(); env["HYTHON_HOME"]=str(root/"home")
            artifact=root/"program.hbc"
            for args in (["--version"],["doctor"],["runtime","info"],["compiler","info"]):
                run([str(executable),*args],timeout=60,env=env)
            run([str(executable),"compile",str(ROOT/"examples"/"컴파일.hy"),"-o",str(artifact)],timeout=60,env=env)
            run([str(executable),"execute",str(artifact)],timeout=60,env=env)
    print(f"C-compiled Hython EXE: {executable}")
    print(f"SHA-256: {output/'hython.exe.sha256'}")
    return 0


if __name__=="__main__": raise SystemExit(main())
