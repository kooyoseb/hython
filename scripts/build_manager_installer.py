"""Build the standalone Hython Manager x64 MSI."""
from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.1.1"


def main() -> int:
    wix = shutil.which("wix")
    if not wix:
        raise SystemExit("WiX가 없습니다: dotnet tool install --global wix")
    executable = ROOT / "manager" / "release" / "HythonManager.exe"
    if not executable.is_file():
        raise SystemExit("먼저 build-manager.bat을 실행하세요.")
    version = subprocess.run(
        [
            "powershell", "-NoProfile", "-Command",
            f"(Get-Item -LiteralPath '{executable}').VersionInfo.FileVersion",
        ],
        capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout.strip()
    if version != VERSION + ".0":
        raise SystemExit(
            f"Manager EXE 버전이 일치하지 않습니다: {version} (필요: {VERSION}.0)"
        )
    output = ROOT / "release" / f"HythonManager-{VERSION}-x64.msi"
    command = [
        wix, "build", str(ROOT / "installer" / "manager.wxs"), "-arch", "x64",
        "-d", f"HythonManagerExe={executable.resolve()}",
        "-d", f"ManagerVersion={VERSION}",
        "-d", f"LicenseRtf={(ROOT / 'installer' / 'license.rtf').resolve()}",
        "-d", f"HythonIcon={(ROOT / 'assets' / 'hython.ico').resolve()}",
        "-ext", "WixToolset.UI.wixext", "-pdbtype", "none", "-o", str(output),
    ]
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode:
        return result.returncode
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    checksum = output.with_suffix(output.suffix + ".sha256")
    checksum.write_text(f"{digest}  {output.name}\n", encoding="ascii")
    print(f"Manager MSI: {output}")
    print(f"SHA-256: {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
