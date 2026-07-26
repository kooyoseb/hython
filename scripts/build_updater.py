"""Build the Hython Windows tray updater."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hython import __version__


def find_csc() -> Path:
    direct = shutil.which("csc")
    if direct:
        return Path(direct)
    vswhere = Path(
        r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
    )
    if vswhere.is_file():
        result = subprocess.run(
            [str(vswhere), "-latest", "-products", "*", "-property", "installationPath"],
            capture_output=True, text=True, check=True,
        )
        candidate = Path(result.stdout.strip()) / "MSBuild/Current/Bin/Roslyn/csc.exe"
        if candidate.is_file():
            return candidate
    raise SystemExit("C# 컴파일러를 찾을 수 없습니다. Visual Studio Build Tools가 필요합니다.")


def main() -> int:
    source = ROOT / "installer" / "hython_updater.cs"
    text = source.read_text(encoding="utf-8")
    if f'AssemblyFileVersion("{__version__}.0")' not in text:
        raise SystemExit(f"업데이터 버전을 {__version__}.0으로 맞추세요.")
    output = ROOT / "release" / "HythonUpdater.exe"
    command = [
        str(find_csc()), "/nologo", "/target:winexe", "/optimize+", "/platform:x64",
        "/reference:System.dll", "/reference:System.Core.dll",
        "/reference:System.Drawing.dll", "/reference:System.Windows.Forms.dll",
        "/reference:System.Web.Extensions.dll",
        f"/win32icon:{ROOT / 'assets' / 'hython.ico'}",
        f"/out:{output}", str(source),
    ]
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode:
        return result.returncode
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".exe.sha256").write_text(
        f"{digest}  {output.name}\n", encoding="ascii"
    )
    print(f"Hython updater: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
