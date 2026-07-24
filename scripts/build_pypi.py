"""Build, validate, install-test, and optionally publish Hython distributions."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from hython import __version__


def run(command,*,env=None,timeout=300):
    result=subprocess.run(command,cwd=ROOT,env=env,timeout=timeout)
    if result.returncode: raise SystemExit(result.returncode)


def main(argv=None):
    parser=argparse.ArgumentParser(description="Hython PyPI release pipeline")
    parser.add_argument("--output-dir",type=Path,default=ROOT/"pypi-dist")
    parser.add_argument("--upload",action="store_true")
    parser.add_argument("--repository",choices=("testpypi","pypi"),default="testpypi")
    parser.add_argument("--allow-prerelease",action="store_true")
    ns=parser.parse_args(argv)
    output=ns.output_dir.resolve(); output.mkdir(parents=True,exist_ok=True)
    for path in output.glob("hython_lang-*"):
        if path.is_file(): path.unlink()
    run([sys.executable,"-m","build","--outdir",str(output)])
    artifacts=sorted([*output.glob("*.whl"),*output.glob("*.tar.gz")])
    if len(artifacts)!=2 or not any(path.suffix==".whl" for path in artifacts):
        raise SystemExit("wheel과 sdist가 정확히 생성되지 않았습니다.")
    run([sys.executable,"-m","twine","check",*[str(path) for path in artifacts]])
    wheel=next(path for path in artifacts if path.suffix==".whl")
    with tempfile.TemporaryDirectory(prefix="hython-pypi-smoke-") as directory:
        root=Path(directory); venv=root/"venv"
        env=os.environ.copy(); env.pop("PYTHONPATH",None); env["HYTHON_HOME"]=str(root/"home")
        run([sys.executable,"-m","venv",str(venv)],env=env)
        python=venv/"Scripts"/"python.exe"; cli=venv/"Scripts"/"hython.exe"
        run([str(python),"-m","pip","install","--no-deps","--force-reinstall",str(wheel)],env=env)
        run([str(cli),"--version"],env=env,timeout=60)
        run([str(cli),"compile",str(ROOT/"examples"/"컴파일.hy"),"-o",str(root/"program.hbc")],env=env,timeout=60)
        run([str(cli),"execute",str(root/"program.hbc")],env=env,timeout=60)
    if ns.upload:
        if ns.repository=="pypi" and "dev" in __version__ and not ns.allow_prerelease:
            raise SystemExit("개발 버전의 실제 PyPI 게시에는 --allow-prerelease가 필요합니다.")
        token=os.environ.get("TWINE_PASSWORD")
        if not token or not token.startswith("pypi-"):
            raise SystemExit("TWINE_PASSWORD에 PyPI API token을 설정하세요.")
        command=[sys.executable,"-m","twine","upload","--non-interactive","--username","__token__"]
        if ns.repository=="testpypi": command.extend(["--repository","testpypi"])
        command.extend(str(path) for path in artifacts)
        run(command)
    print(f"PyPI artifacts verified: {output}")
    for path in artifacts: print(f"  {path.name}")
    return 0


if __name__=="__main__": raise SystemExit(main())
