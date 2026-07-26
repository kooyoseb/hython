"""Build the bilingual single-file Hython setup launcher."""

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
            capture_output=True,
            text=True,
            check=True,
        )
        candidate = (
            Path(result.stdout.strip())
            / "MSBuild"
            / "Current"
            / "Bin"
            / "Roslyn"
            / "csc.exe"
        )
        if candidate.is_file():
            return candidate
    raise SystemExit("C# 컴파일러를 찾을 수 없습니다. Visual Studio Build Tools가 필요합니다.")


def main() -> int:
    if __version__ != "2.0.2":
        raise SystemExit(f"setup.exe 버전을 갱신하세요: 현재 {__version__}")
    msi = ROOT / "release" / f"Hython-{__version__}-x64.msi"
    if not msi.is_file():
        raise SystemExit(f"먼저 build-installer.bat을 실행하세요: {msi}")
    output = ROOT / "release" / f"Hython-{__version__}-setup.exe"
    command = [
        str(find_csc()),
        "/nologo",
        "/target:winexe",
        "/optimize+",
        "/platform:x64",
        "/reference:System.dll",
        "/reference:System.Drawing.dll",
        "/reference:System.Windows.Forms.dll",
        f"/win32icon:{ROOT / 'assets' / 'hython.ico'}",
        f"/resource:{msi},HythonInstaller.msi",
        f"/out:{output}",
        str(ROOT / "installer" / "setup_launcher.cs"),
    ]
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode:
        raise SystemExit(result.returncode)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    checksum = output.with_suffix(output.suffix + ".sha256")
    checksum.write_text(f"{digest}  {output.name}\n", encoding="ascii")
    print(f"Bilingual setup: {output}")
    print(f"SHA-256: {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
