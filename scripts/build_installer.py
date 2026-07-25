"""Build the x64 Hython MSI with WiX."""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from hython import __version__


def main():
    wix=shutil.which("wix")
    if not wix: raise SystemExit("WiX가 없습니다: dotnet tool install --global wix")
    executable=ROOT/"release"/"hython.exe"
    if not executable.is_file(): raise SystemExit("먼저 build-hython.bat을 실행하세요.")
    version_check=subprocess.run(
        [str(executable), "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    expected=f"하이썬 {__version__}"
    actual=(version_check.stdout or version_check.stderr).strip()
    if version_check.returncode or actual != expected:
        raise SystemExit(
            f"EXE 버전이 일치하지 않습니다: {actual or '확인 실패'} "
            f"(필요: {expected}). build-hython.bat을 다시 실행하세요."
        )
    match=re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-dev(\d+))?",__version__)
    msi_version=f"{match.group(1)}.{match.group(2)}.{match.group(4) or match.group(3)}" if match else "1.0.0"
    output=ROOT/"release"/f"Hython-{__version__}-x64.msi"
    command=[wix,"build",str(ROOT/"installer"/"hython.wxs"),"-arch","x64",
             "-d",f"HythonExe={executable.resolve()}","-d",f"MsiVersion={msi_version}",
             "-pdbtype","none","-o",str(output)]
    result=subprocess.run(command,cwd=ROOT)
    if result.returncode: raise SystemExit(result.returncode)
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    checksum=output.with_suffix(output.suffix+".sha256")
    checksum.write_text(f"{digest}  {output.name}\n",encoding="ascii")
    print(f"MSI installer: {output}")
    print(f"SHA-256: {checksum}")
    return 0


if __name__=="__main__": raise SystemExit(main())
