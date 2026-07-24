"""Command line interface for Hython."""

from __future__ import annotations

import argparse
import code
import platform
import sys
from pathlib import Path

from . import __version__
from .translator import compile_hython, to_hython, to_python
from .importer import install_importer
from .package_manager import (
    infer_module_name, install as install_package, remove_dictionary,
    scan as scan_package, uninstall as uninstall_package,
)
from .runtime import check_tree, inspect_runtime, sync_runtime
from .runtime_manager import (
    install_runtime, list_runtimes, reexec_with_preferred_runtime,
    run_hython_with_runtime, set_preference, RuntimeManagerError,
)
from .bytecode import read as read_hbc, write as write_hbc
from .compiler import compile_hir, compile_source
from .hir import format_hir
from .vm import VM
from .updater import initialize, refresh
from .compiler_manager import (
    CompilerUpdateError, active_version as active_compiler_version,
    check as check_compiler_update, reexec_with_active as reexec_with_active_compiler,
    remove as remove_compiler, rollback as rollback_compiler,
    update as update_compiler,
)


def _run(path: Path, args: list[str]) -> int:
    source = path.read_text(encoding="utf-8")
    namespace = {
        "__name__": "__main__", "__file__": str(path),
        "__package__": None, "__cached__": None,
    }
    old_argv = sys.argv
    old_path = sys.path[:]
    sys.argv = [str(path), *args]
    sys.path.insert(0, str(path.resolve().parent))
    install_importer()
    try:
        exec(compile_hython(source, str(path)), namespace)
    finally:
        sys.argv = old_argv
        sys.path[:] = old_path
    return 0


def _repl() -> int:
    banner = f"하이썬 {__version__} (Python {platform.python_version()})"

    class Console(code.InteractiveConsole):
        def runsource(self, source, filename="<하이썬>", symbol="single"):
            return super().runsource(to_python(source), filename, symbol)

    install_importer()
    Console().interact(banner=banner, exitmsg="하이썬을 종료합니다.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hython", description="발음으로 쓰는 한글 Python")
    parser.add_argument("--version", action="version", version=f"하이썬 {__version__}")
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run", help="하이썬 파일 실행")
    run.add_argument("file", type=Path)
    run.add_argument("args", nargs=argparse.REMAINDER)
    module = sub.add_parser("module", aliases=["-m"], help="하이썬 모듈 실행")
    module.add_argument("name")
    module.add_argument("args", nargs=argparse.REMAINDER)
    trans = sub.add_parser("translate", help="소스 파일 변환")
    trans.add_argument("file", type=Path)
    trans.add_argument("--reverse", action="store_true", help="Python에서 하이썬으로 변환")
    trans.add_argument("-o", "--output", type=Path)
    sub.add_parser("repl", help="대화형 하이썬")
    sub.add_parser("doctor", help="실행 환경 확인")
    init = sub.add_parser("init", help="최초 문법 환경 초기화")
    init.add_argument("--force", action="store_true", help="현재 환경을 다시 생성")
    update = sub.add_parser("update", help="최신 Python 및 외부 문법 사전 갱신")
    update.add_argument("--no-runtime", action="store_true", help="Python 다운로드 없이 현재 환경만 갱신")
    update.add_argument("--activate-runtime", help=argparse.SUPPRESS)
    compiler_update = sub.add_parser("compiler", help="외부 HBC 컴파일러 자동 업데이트 관리")
    compiler_sub = compiler_update.add_subparsers(dest="compiler_command", required=True)
    compiler_sub.add_parser("info", help="현재 활성 컴파일러 확인")
    compiler_sub.add_parser("check", help="공식 최신 컴파일러 확인")
    compiler_install = compiler_sub.add_parser("update", help="최신 컴파일러 검증·설치·활성화")
    compiler_install.add_argument("--force", action="store_true")
    compiler_sub.add_parser("rollback", help="이전 검증 컴파일러로 복구")
    compiler_remove = compiler_sub.add_parser("remove", help="외부 컴파일러 삭제")
    compiler_remove.add_argument("version", nargs="?")
    package = sub.add_parser("package", help="Python 패키지 설치 및 발음 사전 관리")
    package_sub = package.add_subparsers(dest="package_command", required=True)
    package_install = package_sub.add_parser("install", help="패키지를 설치하고 사전 생성")
    package_install.add_argument("spec", help="pip 패키지 지정자")
    package_install.add_argument("--module", help="import 모듈명 (패키지명과 다를 때)")
    package_install.add_argument("--upgrade", action="store_true")
    package_scan = package_sub.add_parser("scan", help="설치된 모듈의 사전 생성")
    package_scan.add_argument("module")
    package_uninstall = package_sub.add_parser("uninstall", help="패키지와 생성된 사전 제거")
    package_uninstall.add_argument("package", help="pip 배포 이름")
    package_uninstall.add_argument("--module", help="삭제할 import 모듈명")
    runtime = sub.add_parser("runtime", help="Python 런타임 분석 및 문법 호환성 검사")
    runtime_sub = runtime.add_subparsers(dest="runtime_command", required=True)
    runtime_sub.add_parser("info", help="현재 Python 문법 정보")
    runtime_sub.add_parser("sync", help="현재 Python 프로필 저장")
    runtime_check = runtime_sub.add_parser("check", help=".hy 파일 문법 검사")
    runtime_check.add_argument("path", nargs="?", type=Path, default=Path("."))
    runtime_sub.add_parser("list", help="설치된 공식 Python 런타임 목록")
    runtime_online = runtime_sub.add_parser("online", help="공식 온라인 런타임 검색")
    runtime_online.add_argument("tag", nargs="?")
    runtime_install = runtime_sub.add_parser("install", help="공식 Python 런타임 설치")
    runtime_install.add_argument("tag", nargs="?", default="default")
    runtime_install.add_argument("--update", action="store_true")
    runtime_install.add_argument("--dry-run", action="store_true")
    runtime_use = runtime_sub.add_parser("use", help="프로젝트 Python 런타임 지정")
    runtime_use.add_argument("tag")
    compile_cmd = sub.add_parser("compile", help="하이썬 소스를 독립 HBC로 컴파일")
    compile_cmd.add_argument("file", type=Path)
    compile_cmd.add_argument("-o", "--output", type=Path)
    compile_cmd.add_argument("--no-optimize", action="store_true")
    compile_cmd.add_argument("--show-hir", action="store_true")
    execute_cmd = sub.add_parser("execute", help="HBC를 하이썬 VM으로 실행")
    execute_cmd.add_argument("file", type=Path)
    dis = sub.add_parser("disassemble", help="HBC 명령어 표시")
    dis.add_argument("file", type=Path)
    build = sub.add_parser("build", help="하이썬 프로젝트를 HBC 디렉터리로 빌드")
    build.add_argument("source", nargs="?", type=Path, default=Path("."))
    build.add_argument("-o", "--output", type=Path, default=Path("dist"))
    build.add_argument("--no-optimize", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    actual_argv = list(sys.argv[1:] if argv is None else argv)
    reexec_with_active_compiler(actual_argv)
    if not (actual_argv and actual_argv[0] == "runtime"):
        start = Path(actual_argv[1]) if len(actual_argv) > 1 and actual_argv[0] == "run" else Path.cwd()
        reexec_with_preferred_runtime(actual_argv, start)
    parser = build_parser()
    ns = parser.parse_args(actual_argv)
    if ns.command != "init":
        initialize()
    if ns.command == "init":
        result = initialize(force=ns.force)
        if result["initialized"]:
            print(f"하이썬 초기화 완료: {result['runtime']}")
        else:
            print("하이썬은 이미 초기화되어 있습니다.")
        return 0
    if ns.command == "update":
        if not ns.no_runtime:
            install_runtime("default", update=True)
            result_code=run_hython_with_runtime("default",["update","--no-runtime","--activate-runtime","default"])
            if result_code:
                raise RuntimeManagerError(f"새 Python에서 문법 동기화 실패 (종료 코드 {result_code})")
            print("최신 Python 런타임 설치 및 활성화 완료")
            return 0
        result = refresh(runtime_tag=getattr(ns,"activate_runtime",None))
        print(f"문법 업데이트 완료: Python {platform.python_version()}")
        print(f"패키지 사전: {len(result['refreshed'])}개 갱신, {len(result['removed'])}개 삭제")
        return 0
    if ns.command == "compiler":
        if ns.compiler_command == "info":
            active=active_compiler_version()
            print(f"부트스트랩 컴파일러: {__version__}")
            print(f"활성 외부 컴파일러: {active or '없음'}")
            return 0
        if ns.compiler_command == "check":
            result=check_compiler_update()
            print(f"현재: {result['current']}")
            print(f"공식 최신: {result['version']}")
            print(f"업데이트: {'가능' if result['update_available'] else '최신 상태'}")
            return 0
        if ns.compiler_command == "update":
            result=update_compiler(force=ns.force)
            if result["installed"]:
                print(f"컴파일러 설치·검증·활성화 완료: {result['version']}")
                print("다음 Hython 실행부터 새 컴파일러를 사용합니다.")
            else:
                print(f"컴파일러가 최신 상태입니다: {result['current']}")
            return 0
        if ns.compiler_command == "rollback":
            version=rollback_compiler()
            print(f"컴파일러 복구 완료: {version or '내장 부트스트랩'}")
            return 0
        version=remove_compiler(ns.version)
        print(f"외부 컴파일러 삭제 완료: {version}")
        return 0
    if ns.command == "run":
        return _run(ns.file, ns.args)
    if ns.command == "compile":
        output = ns.output or ns.file.with_suffix(".hbc")
        source = ns.file.read_text(encoding="utf-8-sig")
        hir = compile_hir(source, str(ns.file), optimize=not ns.no_optimize)
        if ns.show_hir:
            print(format_hir(hir))
        write_hbc(output, compile_source(source, str(ns.file), optimize=not ns.no_optimize))
        print(f"HBC 생성: {output}")
        return 0
    if ns.command == "execute":
        VM([ns.file.resolve().parent]).run(read_hbc(ns.file))
        return 0
    if ns.command == "disassemble":
        code = read_hbc(ns.file)
        for index, instruction in enumerate(code.instructions):
            print(f"{index:04d}  {instruction[0]:14} {' '.join(map(str, instruction[1:]))}")
        return 0
    if ns.command == "build":
        source_root=ns.source.resolve()
        files=[source_root] if source_root.is_file() else sorted(source_root.rglob("*.hy"))
        if not files:
            parser.error(f".hy 파일을 찾을 수 없습니다: {ns.source}")
        for source_file in files:
            relative=Path(source_file.name) if source_root.is_file() else source_file.relative_to(source_root)
            output=(ns.output/relative).with_suffix(".hbc")
            output.parent.mkdir(parents=True,exist_ok=True)
            code=compile_source(source_file.read_text(encoding="utf-8-sig"),str(relative),optimize=not ns.no_optimize)
            write_hbc(output,code)
            print(f"빌드: {relative} -> {output}")
        print(f"빌드 완료: {len(files)}개 모듈")
        return 0
    if ns.command in ("module", "-m"):
        install_importer()
        old_argv = sys.argv
        sys.argv = [ns.name, *ns.args]
        try:
            import runpy
            runpy.run_module(ns.name, run_name="__main__", alter_sys=True)
        finally:
            sys.argv = old_argv
        return 0
    if ns.command == "translate":
        source = ns.file.read_text(encoding="utf-8")
        result = to_hython(source) if ns.reverse else to_python(source)
        if ns.output:
            ns.output.write_text(result, encoding="utf-8")
        else:
            print(result, end="")
        return 0
    if ns.command == "doctor":
        print(f"하이썬: {__version__}\nPython: {platform.python_version()}\n실행 파일: {sys.executable}")
        return 0
    if ns.command == "package":
        if ns.package_command == "install":
            module = ns.module or infer_module_name(ns.spec)
            install_package(ns.spec, upgrade=ns.upgrade)
            output = scan_package(module)
            print(f"발음 사전 생성: {output}")
            return 0
        if ns.package_command == "uninstall":
            module = ns.module or infer_module_name(ns.package)
            uninstall_package(ns.package)
            removed = remove_dictionary(module)
            print(f"패키지 제거 완료: {ns.package}")
            print(f"발음 사전 삭제: {'완료' if removed else '대상 없음'} ({module})")
            return 0
        output = scan_package(ns.module)
        print(f"발음 사전 생성: {output}")
        return 0
    if ns.command == "runtime":
        if ns.runtime_command == "info":
            info = inspect_runtime()
            print(f"Python: {info['version']} ({info['implementation']})")
            print(f"실행 파일: {info['executable']}")
            print(f"키워드: {len(info['hard_keywords'])}개")
            print(f"소프트 키워드: {', '.join(info['soft_keywords']) or '없음'}")
            print(f"미등록 새 키워드: {', '.join(info['new_keywords']) or '없음'}")
            return 0
        if ns.runtime_command == "sync":
            print(f"런타임 프로필 생성: {sync_runtime()}")
            return 0
        if ns.runtime_command == "list":
            print(list_runtimes(), end="")
            return 0
        if ns.runtime_command == "online":
            print(list_runtimes(online=True, tag=ns.tag), end="")
            return 0
        if ns.runtime_command == "install":
            install_runtime(ns.tag, update=ns.update, dry_run=ns.dry_run)
            if not ns.dry_run:
                print(f"Python 런타임 설치 완료: {ns.tag}")
            return 0
        if ns.runtime_command == "use":
            print(f"프로젝트 런타임 지정: {set_preference(Path.cwd(), ns.tag)}")
            print(f"설치 전 확인: hython runtime install {ns.tag} --dry-run")
            return 0
        failures = check_tree(ns.path)
        if failures:
            for path, error in failures:
                print(f"실패: {path}\n  {error}", file=sys.stderr)
            return 1
        print(f"문법 검사 통과: {ns.path}")
        return 0
    if ns.command in (None, "repl"):
        return _repl()
    parser.error("알 수 없는 명령입니다.")
    return 2

def entrypoint() -> int:
    """Console entry point with stable, user-facing diagnostics."""
    from .bytecode import BytecodeError
    from .compiler import CompileError
    from .frontend import ParseError
    from .runtime_manager import RuntimeManagerError
    from .vm import VMError
    try:
        return main()
    except (ParseError,CompileError,BytecodeError,VMError,RuntimeManagerError,CompilerUpdateError) as exc:
        print(f"하이썬 오류: {exc}",file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"하이썬 오류: 파일을 찾을 수 없습니다: {exc.filename}",file=sys.stderr)
        return 1
    except __import__("subprocess").CalledProcessError as exc:
        print(f"하이썬 오류: 외부 명령 실패 (종료 코드 {exc.returncode})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(entrypoint())
