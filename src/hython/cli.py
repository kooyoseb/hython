"""Command line interface for Hython."""

from __future__ import annotations

import argparse
import code
import platform
import sys
from pathlib import Path

from . import __version__
from .translator import audit_english, compile_hython, koreanize, to_hython, to_python
from .importer import install_importer
from .package_manager import (
    infer_module_name, install as install_package, modules_for_distribution,
    remove_dictionary,
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
from .exe_builder import ExeBuildError, build_exe, create_archive, resolve_entry
from .environment import display_executable, external_source_root, is_frozen

COMMAND_ALIASES = {
    "소스실행":"run", "모듈":"module", "변환":"translate", "감사":"audit",
    "대화":"repl", "진단":"doctor", "초기화":"init", "업데이트":"update",
    "컴파일러":"compiler", "패키지":"package", "런타임":"runtime",
    "컴파일":"compile", "바이트실행":"execute", "실행파일":"exe",
    "해체":"disassemble", "빌드":"build",
    "아이디이":"ide",
}
NESTED_ALIASES = {
    "정보":"info", "확인":"check", "업데이트":"update",
    "되돌리기":"rollback", "제거":"remove", "설치":"install",
    "분석":"scan", "동기화":"sync", "검사":"check", "목록":"list",
    "온라인":"online", "사용":"use",
}


def _resource_argument(value: str) -> tuple[Path,Path]:
    if "=" in value:
        source,destination=value.split("=",1)
    else:
        source=value; destination=Path(value).name
    if not source or not destination:
        raise argparse.ArgumentTypeError("리소스 형식은 SOURCE 또는 SOURCE=DEST입니다.")
    return Path(source),Path(destination)


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

        def showtraceback(self):
            from .diagnostics import format_exception
            error=sys.exception()
            if error is not None:
                print(format_exception(error),file=sys.stderr)

        def showsyntaxerror(self, filename=None):
            from .diagnostics import format_exception
            error=sys.exception()
            if error is not None:
                print(format_exception(error,traceback_enabled=False),file=sys.stderr)

    install_importer()
    Console().interact(banner=banner, exitmsg="하이썬을 종료합니다.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hython", description="발음으로 쓰는 한글 Python")
    parser.add_argument("--version", action="version", version=f"하이썬 {__version__}")
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run", aliases=["소스실행"], help="하이썬 파일 실행")
    run.add_argument("file", type=Path)
    run.add_argument("args", nargs=argparse.REMAINDER)
    module = sub.add_parser("module", aliases=["-m","모듈"], help="하이썬 모듈 실행")
    module.add_argument("name")
    module.add_argument("args", nargs=argparse.REMAINDER)
    trans = sub.add_parser("translate", aliases=["변환"], help="소스 파일 변환")
    trans.add_argument("file", type=Path)
    trans.add_argument("--reverse", action="store_true", help="Python에서 하이썬으로 변환")
    trans.add_argument("--complete", action="store_true", help="모든 영어 식별자를 발음형 한글로 변환")
    trans.add_argument("-o", "--output", type=Path)
    audit = sub.add_parser("audit", aliases=["감사"], help=".hy 소스에 남은 영어 식별자 검사")
    audit.add_argument("path", nargs="?", type=Path, default=Path("."))
    sub.add_parser("repl", aliases=["대화"], help="대화형 하이썬")
    sub.add_parser("doctor", aliases=["진단"], help="실행 환경 확인")
    init = sub.add_parser("init", aliases=["초기화"], help="최초 문법 환경 초기화")
    init.add_argument("--force", action="store_true", help="현재 환경을 다시 생성")
    update = sub.add_parser("update", aliases=["업데이트"], help="최신 Python 및 외부 문법 사전 갱신")
    update.add_argument("--no-runtime", action="store_true", help="Python 다운로드 없이 현재 환경만 갱신")
    update.add_argument("--activate-runtime", help=argparse.SUPPRESS)
    compiler_update = sub.add_parser("compiler", aliases=["컴파일러"], help="외부 HBC 컴파일러 자동 업데이트 관리")
    compiler_sub = compiler_update.add_subparsers(dest="compiler_command", required=True)
    compiler_sub.add_parser("info", aliases=["정보"], help="현재 활성 컴파일러 확인")
    compiler_sub.add_parser("check", aliases=["확인"], help="공식 최신 컴파일러 확인")
    compiler_install = compiler_sub.add_parser("update", aliases=["업데이트"], help="최신 컴파일러 검증·설치·활성화")
    compiler_install.add_argument("--force", action="store_true")
    compiler_sub.add_parser("rollback", aliases=["되돌리기"], help="이전 검증 컴파일러로 복구")
    compiler_remove = compiler_sub.add_parser("remove", aliases=["제거"], help="외부 컴파일러 삭제")
    compiler_remove.add_argument("version", nargs="?")
    package = sub.add_parser("package", aliases=["패키지"], help="Python 패키지 설치 및 발음 사전 관리")
    package_sub = package.add_subparsers(dest="package_command", required=True)
    package_install = package_sub.add_parser("install", aliases=["설치"], help="패키지를 설치하고 사전 생성")
    package_install.add_argument("spec", help="pip 패키지 지정자")
    package_install.add_argument("--module", help="import 모듈명 (패키지명과 다를 때)")
    package_install.add_argument("--upgrade", action="store_true")
    package_scan = package_sub.add_parser("scan", aliases=["분석"], help="설치된 모듈의 사전 생성")
    package_scan.add_argument("module")
    package_scan.add_argument("--static", action="store_true", help="모듈을 실행하지 않고 정적 분석만 사용")
    package_uninstall = package_sub.add_parser("uninstall", aliases=["제거"], help="패키지와 생성된 사전 제거")
    package_uninstall.add_argument("package", help="pip 배포 이름")
    package_uninstall.add_argument("--module", help="삭제할 import 모듈명")
    runtime = sub.add_parser("runtime", aliases=["런타임"], help="Python 런타임 분석 및 문법 호환성 검사")
    runtime_sub = runtime.add_subparsers(dest="runtime_command", required=True)
    runtime_sub.add_parser("info", aliases=["정보"], help="현재 Python 문법 정보")
    runtime_sub.add_parser("sync", aliases=["동기화"], help="현재 Python 프로필 저장")
    runtime_check = runtime_sub.add_parser("check", aliases=["검사"], help=".hy 파일 문법 검사")
    runtime_check.add_argument("path", nargs="?", type=Path, default=Path("."))
    runtime_sub.add_parser("list", aliases=["목록"], help="설치된 공식 Python 런타임 목록")
    runtime_online = runtime_sub.add_parser("online", aliases=["온라인"], help="공식 온라인 런타임 검색")
    runtime_online.add_argument("tag", nargs="?")
    runtime_install = runtime_sub.add_parser("install", aliases=["설치"], help="공식 Python 런타임 설치")
    runtime_install.add_argument("tag", nargs="?", default="default")
    runtime_install.add_argument("--update", action="store_true")
    runtime_install.add_argument("--dry-run", action="store_true")
    runtime_use = runtime_sub.add_parser("use", aliases=["사용"], help="프로젝트 Python 런타임 지정")
    runtime_use.add_argument("tag")
    compile_cmd = sub.add_parser("compile", aliases=["컴파일"], help="하이썬 소스를 독립 HBC로 컴파일")
    compile_cmd.add_argument("file", type=Path)
    compile_cmd.add_argument("-o", "--output", type=Path)
    compile_cmd.add_argument("--no-optimize", action="store_true")
    compile_cmd.add_argument("--show-hir", action="store_true")
    execute_cmd = sub.add_parser("execute", aliases=["바이트실행"], help="HBC를 하이썬 VM으로 실행")
    execute_cmd.add_argument("file", type=Path)
    exe_cmd = sub.add_parser("exe", aliases=["실행파일"], help="HBC를 독립 Windows EXE로 빌드")
    exe_cmd.add_argument("file", type=Path, help="HBC 파일 또는 프로젝트 디렉터리")
    exe_cmd.add_argument("--entry", help="프로젝트 entry HBC 상대 경로")
    exe_cmd.add_argument("-o", "--output", type=Path)
    exe_cmd.add_argument("--windowed", action="store_true", help="콘솔 창 없는 GUI 실행 파일")
    exe_cmd.add_argument("--icon", type=Path, help="Windows .ico 파일")
    exe_cmd.add_argument("--module-root", type=Path, help="함께 넣을 HBC 모듈 루트 (기본: 입력 폴더)")
    exe_cmd.add_argument("--onedir", action="store_true", help="빠른 시작용 디렉터리 배포")
    exe_cmd.add_argument("--resource", action="append", type=_resource_argument, default=[], metavar="SOURCE[=DEST]")
    exe_cmd.add_argument("--exclude-module", action="append", default=[], help="사용하지 않는 Python 모듈 제외")
    exe_cmd.add_argument("--product-name")
    exe_cmd.add_argument("--file-version", default="1.0.0.0")
    exe_cmd.add_argument("--company")
    exe_cmd.add_argument("--description")
    exe_cmd.add_argument("--copyright")
    exe_cmd.add_argument("--sign-pfx", type=Path, help="Authenticode PFX 인증서")
    exe_cmd.add_argument("--sign-password-env", help="PFX 암호가 든 환경 변수명")
    exe_cmd.add_argument("--timestamp-url", default="http://timestamp.digicert.com")
    exe_cmd.add_argument("--archive", type=Path, help="배포 ZIP과 .sha256 생성")
    dis = sub.add_parser("disassemble", aliases=["해체"], help="HBC 명령어 표시")
    dis.add_argument("file", type=Path)
    build = sub.add_parser("build", aliases=["빌드"], help="하이썬 프로젝트를 HBC 디렉터리로 빌드")
    build.add_argument("source", nargs="?", type=Path, default=Path("."))
    build.add_argument("-o", "--output", type=Path, default=Path("dist"))
    build.add_argument("--no-optimize", action="store_true")
    ide = sub.add_parser("ide", aliases=["아이디이"], help="IDE용 JSON 분석 프로토콜")
    ide_sub = ide.add_subparsers(dest="ide_command", required=True)
    ide_analyze = ide_sub.add_parser("analyze", help="진단·심볼·자동완성 통합 분석")
    ide_analyze.add_argument("file", type=Path)
    ide_analyze.add_argument("--line", type=int, default=1)
    ide_analyze.add_argument("--column", type=int, default=0)
    ide_analyze.add_argument("--stdin", action="store_true",
                             help="파일 대신 표준 입력의 저장되지 않은 코드 분석")
    ide_diagnose = ide_sub.add_parser("diagnose", help="한글 문법 진단")
    ide_diagnose.add_argument("file", type=Path)
    ide_symbols = ide_sub.add_parser("symbols", help="파일 코드 구조")
    ide_symbols.add_argument("file", type=Path)
    ide_complete = ide_sub.add_parser("complete", help="현재 위치 자동완성")
    ide_complete.add_argument("file", type=Path)
    ide_complete.add_argument("line", type=int)
    ide_complete.add_argument("column", type=int)
    ide_debug = ide_sub.add_parser("debug", help="IDE JSON 디버그 어댑터")
    ide_debug.add_argument("file", type=Path)
    ide_debug.add_argument("--breakpoint", action="append", type=int, default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    actual_argv = list(sys.argv[1:] if argv is None else argv)
    reexec_with_active_compiler(actual_argv)
    if not (actual_argv and actual_argv[0] == "runtime"):
        start = Path(actual_argv[1]) if len(actual_argv) > 1 and actual_argv[0] == "run" else Path.cwd()
        reexec_with_preferred_runtime(actual_argv, start)
    parser = build_parser()
    ns = parser.parse_args(actual_argv)
    ns.command = COMMAND_ALIASES.get(ns.command,ns.command)
    for attribute in ("compiler_command","package_command","runtime_command"):
        if hasattr(ns,attribute):
            value=getattr(ns,attribute)
            setattr(ns,attribute,NESTED_ALIASES.get(value,value))
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
    if ns.command == "ide":
        if ns.ide_command == "debug":
            from .debug_adapter import run as run_debug_adapter
            return run_debug_adapter(ns.file, ns.breakpoint)
        from .ide_protocol import (
            analyze_file, analyze_source, completions, diagnostics, emit, symbols,
        )
        source = sys.stdin.read() if getattr(ns, "stdin", False) else ns.file.read_text(encoding="utf-8-sig")
        if ns.ide_command == "analyze":
            emit(
                analyze_source(source, str(ns.file), line=ns.line, column=ns.column)
                if ns.stdin else
                analyze_file(ns.file, line=ns.line, column=ns.column)
            )
        elif ns.ide_command == "diagnose":
            emit({"protocolVersion": 1, "diagnostics": diagnostics(source, str(ns.file))})
        elif ns.ide_command == "symbols":
            emit({"protocolVersion": 1, "symbols": symbols(source, str(ns.file))})
        else:
            emit({"protocolVersion": 1, "completions": completions(source, ns.line, ns.column)})
        return 0
    if ns.command == "compile":
        output = ns.output or ns.file.with_suffix(".hbc")
        output.parent.mkdir(parents=True,exist_ok=True)
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
    if ns.command == "exe":
        entry,project_root=resolve_entry(ns.file,ns.entry)
        if ns.output:
            output=ns.output
        elif ns.onedir:
            output=(ns.file if ns.file.is_dir() else ns.file.parent)/(entry.stem+"-dist")
        else:
            output=entry.with_suffix(".exe")
        metadata={
            "version":ns.file_version,"name":entry.stem,
            **({"product":ns.product_name} if ns.product_name else {}),
            **({"company":ns.company} if ns.company else {}),
            **({"description":ns.description} if ns.description else {}),
            **({"copyright":ns.copyright} if ns.copyright else {}),
        }
        result=build_exe(
            entry,output,console=not ns.windowed,icon=ns.icon,
            module_root=ns.module_root or project_root,resources=ns.resource,
            onefile=not ns.onedir,metadata=metadata,excludes=set(ns.exclude_module),
            sign_pfx=ns.sign_pfx,sign_password_env=ns.sign_password_env,
            timestamp_url=ns.timestamp_url,
        )
        print(f"EXE 생성: {result}")
        if ns.archive:
            archive,checksum=create_archive(result,ns.archive)
            print(f"배포 압축: {archive}")
            print(f"SHA-256: {checksum}")
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
        if ns.complete:
            if not ns.reverse:
                parser.error("--complete는 Python을 하이썬으로 바꾸는 --reverse와 함께 사용하세요.")
            result = koreanize(source)
        else:
            result = to_hython(source) if ns.reverse else to_python(source)
        if ns.output:
            ns.output.write_text(result, encoding="utf-8")
        else:
            print(result, end="")
        return 0
    if ns.command == "audit":
        paths=[ns.path] if ns.path.is_file() else sorted(ns.path.rglob("*.hy"))
        found=0
        for path in paths:
            for item in audit_english(path.read_text(encoding="utf-8-sig")):
                print(f"{path}:{item.line}:{item.column}: {item.name} -> {item.suggestion}")
                found+=1
        if found:
            print(f"영어 식별자 {found}개 발견",file=sys.stderr)
            return 1
        print(f"완전 한글 문법 검사 통과: {ns.path}")
        return 0
    if ns.command == "doctor":
        print(f"하이썬: {__version__}\nPython: {platform.python_version()}\n실행 파일: {display_executable()}")
        if is_frozen():
            source=external_source_root()
            print(f"업데이트용 번들 소스: {source} ({'정상' if (source/'hython'/'cli.py').is_file() else '누락'})")
        return 0
    if ns.command == "package":
        if ns.package_command == "install":
            module = ns.module or infer_module_name(ns.spec)
            install_package(ns.spec, upgrade=ns.upgrade)
            for discovered in modules_for_distribution(ns.spec,ns.module):
                output = scan_package(discovered, deep=True)
                print(f"전체 공개 API 발음 사전 생성: {output}")
            return 0
        if ns.package_command == "uninstall":
            module = ns.module or infer_module_name(ns.package)
            modules = modules_for_distribution(ns.package,ns.module)
            uninstall_package(ns.package)
            removed = [name for name in modules if remove_dictionary(name)]
            print(f"패키지 제거 완료: {ns.package}")
            print(f"발음 사전 삭제: {len(removed)}개 ({', '.join(removed) or '대상 없음'})")
            return 0
        output = scan_package(ns.module, deep=not ns.static)
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
    except KeyboardInterrupt:
        print("하이썬: 사용자가 실행을 중단했습니다.",file=sys.stderr)
        return 1
    except SystemExit:
        raise
    except BaseException as exc:
        import os,traceback
        if os.environ.get("HYTHON_TRACEBACK","").lower()=="python":
            traceback.print_exception(exc)
        else:
            from .diagnostics import format_exception
            expected=isinstance(exc,(ParseError,CompileError,BytecodeError,VMError,RuntimeManagerError,CompilerUpdateError,ExeBuildError))
            print(format_exception(exc,traceback_enabled=not expected),file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(entrypoint())
