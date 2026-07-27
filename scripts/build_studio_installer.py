"""Build the standalone Hython Studio x64 MSI."""
from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.3"


def main() -> int:
    wix = shutil.which("wix")
    if not wix:
        raise SystemExit("WiX가 없습니다: dotnet tool install --global wix")
    executable = ROOT / "studio" / "release" / "HythonStudio.exe"
    if not executable.is_file():
        raise SystemExit("먼저 build-studio.bat을 실행하세요.")
    output = ROOT / "release" / f"HythonStudio-{VERSION}-x64.msi"
    command = [
        wix, "build", str(ROOT / "installer" / "studio.wxs"), "-arch", "x64",
        "-d", f"HythonStudioExe={executable.resolve()}",
        "-d", f"StudioVersion={VERSION}",
        "-d", f"LicenseRtf={(ROOT / 'installer' / 'license.rtf').resolve()}",
        "-d", f"HythonIcon={(ROOT / 'assets' / 'hython.ico').resolve()}",
        "-ext", "WixToolset.UI.wixext", "-pdbtype", "none", "-o", str(output),
    ]
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode:
        raise SystemExit(result.returncode)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    checksum = output.with_suffix(output.suffix + ".sha256")
    checksum.write_text(f"{digest}  {output.name}\n", encoding="ascii")
    print(f"Studio MSI: {output}")
    print(f"SHA-256: {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
