# 변경 기록

## Hython Studio 1.0.2 - 2026-07-27

- GitHub 설치가 본체 태그와 정확한 Hython x64 MSI만 선택하도록 수정했습니다.
- Studio 및 VS Code 확장 릴리스가 최신이어도 엔진 설치가 실패하지 않습니다.
- PyPI 설치·탐지·제거 패키지 이름을 `hython-lang`으로 바로잡았습니다.

## 2.0.5 - 2026-07-27

- Studio 및 VS Code 확장 릴리스를 Hython 본체 업데이트로 잘못 해석하던 문제를 수정했습니다.
- 정식 본체 버전 태그와 일치하는 x64 MSI가 함께 있는 릴리스만 선택합니다.

## Hython Development 1.0.1 - 2026-07-27

- VS Code 탐색기와 편집기 탭의 `.hy` 파일에 정식 Hython 아이콘을 표시합니다.
- 밝은 테마와 어두운 테마의 언어 아이콘을 모두 등록했습니다.

## Hython Development 1.0.0 - 2026-07-27

- VS Code용 Hython 언어 확장을 추가했습니다.
- 문법 강조, 한글 진단, 자동완성, 정의·참조·이름 변경과 호버를 지원합니다.
- 실행, HBC/EXE 빌드, HBC VM 디버거와 프로젝트·패키지 관리를 제공합니다.
- 실제 VS Code Extension Host 통합 테스트를 추가했습니다.

## Hython Studio 1.0.1 - 2026-07-27

- 시작 화면 중앙의 문자 타일을 정식 Hython 아이콘으로 교체했습니다.
- 아이콘을 단일 실행 파일 내부 리소스로 포함해 설치판과 무설치판에서 동일하게 표시합니다.
- Studio 전용 MSI 버전을 1.0.1로 갱신했습니다.

## 2.0.4 - 2026-07-26

- Windows 로그인 시 트레이에서 실행되는 `HythonUpdater.exe`를 추가했습니다.
- 현재 설치 버전과 GitHub 최신 릴리스를 6시간마다 비교합니다.
- 새 버전의 x64 MSI를 자동 다운로드하고 SHA-256 검증 후 관리자 권한으로 설치합니다.
- 트레이 메뉴에서 즉시 업데이트 확인과 업데이터 종료를 지원합니다.
- 트레이 메뉴에서 한국어와 영어를 선택하고 사용자별 설정으로 저장할 수 있습니다.

## 2.0.3 - 2026-07-26

- setup.exe가 기존 Hython 설치를 감지해 복구와 제거 작업을 제공합니다.
- 한국어·영어 유지관리 문구와 제거 확인 화면을 추가했습니다.
- 설치 UI를 배너, 옵션 영역, 상태 및 작업 버튼으로 구성된 Windows 설치 마법사 형태로 개편했습니다.

## 2.0.2 - 2026-07-26

- 설치 마법사에 PATH, 시작 메뉴 바로가기, 바탕화면 바로가기 선택 기능을 추가했습니다.
- `Hython Command Prompt` 바로가기에 하이썬 아이콘을 명시적으로 연결했습니다.
- Windows 앱 목록에서도 하이썬 아이콘이 표시되도록 MSI 제품 아이콘을 추가했습니다.

## 2.0.1 - 2026-07-25

- Windows MSI에 설치·진행·완료 및 복구/제거 UI를 추가했습니다.
- 설치 여부가 보이지 않던 2.0.0 MSI의 사용자 경험 문제를 수정했습니다.
- Winget 배포용 MSI 메타데이터와 버전 검증을 강화했습니다.

## 2.0.0 - 2026-07-24

- 모든 최상위 CLI 명령과 컴파일러·패키지·런타임 하위 명령에 한글 별칭을 추가했습니다.
- `__네임__`, `__파일__`, `__이니트__`, `__레퍼__` 등 Python 데이터 모델 특수
  이름을 영어 없이 사용할 수 있게 했습니다.
- 문자열·URL·경로·환경 변수 값은 외부 시스템과의 정확한 호환을 위해 변형하지 않으며,
  영어 감사에서도 실행 문법과 분리된 데이터로 취급합니다.

## 2.0.0-dev187

- `audit` 명령이 실행 코드에 남은 영어 식별자와 권장 발음형을 위치별로 보고합니다.
- `translate --reverse --complete`가 알려진 문법/API, 사용자 식별자와 문자열 접두사를
  한글 발음형으로 일괄 변환합니다.
- `에프"값={값}"`, `알"\n"`처럼 문자열 접두사도 영어 없이 사용할 수 있습니다.
- Python 동기화 시 표준 라이브러리 전체 공개 API 사전을 생성합니다.
- 패키지 설치는 모든 import 모듈을 찾아 정적 소스와 격리 런타임 API를 합쳐
  모듈·상수·함수·클래스·공개 메서드를 자동 등록합니다.
- 발음 충돌 시 API를 누락하지 않고 숫자 접미 발음명을 부여하며 대형 사전은 파일 변경
  감지 캐시로 로드합니다.
- 패키지 제거와 Python/Hython 업데이트는 생성 사전을 재검사·갱신·삭제합니다.

## 2.0.0-dev186

- 표준 라이브러리와 GUI API의 핵심 이름을 발음형 한글로 즉시 사용할 수 있게 했습니다.
- 패키지 문법 사전이 모듈 이름과 클래스의 공개 메서드까지 정적으로 수집합니다.
- 한글 import 별칭을 보존하면서 `티케이.티케이()`, `창.타이틀()`,
  `창.메인루프()` 같은 API 이름은 정확히 Python 이름으로 변환합니다.

## 2.0.0-dev185

- Hython 자체 onefile 빌드를 PyInstaller 묶음에서 Nuitka C 변환으로 교체해 Python 모듈을 C 소스로 생성하고 MSVC 14.5로 컴파일·링크하며 Tkinter/Tcl/Tk를 기본 산출물에서 제외합니다.

- `build-hython.bat`가 Visual Studio x64 개발 환경과 강제 UTF-8을 자동 구성하고 C build report·아이콘·PE 버전·SHA-256이 포함된 네이티브 `release/hython.exe`를 생성합니다.

- `publish-pypi.bat`과 검증 파이프라인이 wheel+sdist, `twine check`, 깨끗한 venv 설치, HBC compile/execute를 수행하며 명시적 TestPyPI/PyPI 토큰 게시를 지원합니다.

- `build-installer.bat`과 WiX 정의가 C-compiled Hython EXE, 시스템 PATH, 시작 메뉴 REPL 바로가기, 업그레이드·제거 정보를 포함하는 x64 MSI와 SHA-256을 생성합니다.

- native onefile에 업데이트용 Hython 원본을 별도 데이터로 포함하고 `doctor`가 실제 실행 파일 경로와 번들 소스 누락 여부를 진단합니다.

- 독립 `hython.exe`에 Python 3.14의 Tkinter와 Tcl/Tk 8.6 런타임을 기본 포함해 사용자 `.hy`의 동적 `인폴트 tkinter`가 별도 Python 설치 없이 GUI 창을 생성합니다.

- `tkinter.ttk`, `messagebox`, `filedialog`, `colorchooser`, `simpledialog`을 함께 수집하고 HBC→EXE 빌더도 tkinter import를 발견하면 동일한 GUI 하위 모듈을 자동 포함합니다.

- Hython 자체 EXE 빌드 smoke test가 숨김 Tk root를 실제 생성하고 event loop를 거쳐 자동 종료해 Tcl/Tk DLL·스크립트 누락을 매 빌드마다 검출합니다.

- Python 호환 실행·HBC VM·REPL·독립 `hython.exe`의 처리되지 않은 예외를 공통 한글 진단기로 통합해 예외명, 대표 표준 메시지와 traceback 안내를 한국어로 표시합니다.

- 문법 오류는 파일·줄·소스·캐럿 범위를 보존하고, 실행 오류는 사용자 `.hy` 프레임과 HBC의 `하이썬 위치` note를 표시하면서 내부 compiler/VM 프레임은 숨깁니다.

- 원인·문맥 예외 연결과 `ExceptionGroup` 하위 오류를 한국어 구조로 출력하고, 안전하게 번역할 수 없는 사용자 정의 메시지는 원문을 보존합니다.

- 저수준 진단이 필요하면 `HYTHON_TRACEBACK=python`으로 기존 Python traceback을 선택할 수 있습니다.

- Hython 자체 compiler·VM·runtime·package·EXE toolchain을 Python 설치 없이 시작할 수 있는 공식 아이콘·PE 메타데이터 포함 `release/hython.exe` one-file 배포 빌드를 추가합니다.

- `build-hython.bat`가 Python 3.14·PyInstaller 준비, 전체 회귀 테스트, 독립 EXE 빌드, frozen CLI smoke test와 SHA-256 생성을 한 번에 수행합니다.

- frozen Hython은 설치 패키지를 `~/.hython/packages/python-X.Y` 외부 저장소에 관리하고 공식 Python manager를 통해 pip를 실행해, 실행 파일 내부의 임시 Python에 잘못 설치하지 않습니다.

- runtime·compiler 업데이트가 frozen bootstrap에서 실행될 때 번들된 Hython 소스를 공식 관리 Python에 연결하고, HBC→EXE는 외부 PyInstaller 도구 저장소를 자동 준비하도록 경로를 분리합니다.

- `hython exe 프로젝트/ --entry main.hbc`가 프로젝트 entry를 자동 탐색하거나 명시적으로 선택하고 전체 HBC 모듈 트리를 배포합니다.

- `--onedir`, 반복 가능한 `--resource SOURCE=DEST`, `--exclude-module`을 추가해 빠른 시작 배포, 이미지·설정 포함, 미사용 모듈 제외를 지원하며 리소스 루트를 `HYTHON_RESOURCE_ROOT`로 제공합니다.

- `--product-name`, `--file-version`, `--company`, `--description`, `--copyright`를 Windows PE 버전 리소스에 기록하고 잘못된 버전·리소스 경로 탈출을 빌드 전에 거부합니다.

- `--sign-pfx`와 환경 변수 기반 PFX 암호·RFC 3161 timestamp 옵션으로 Authenticode 서명을 지원하며, 서명까지 성공해야 기존 배포물을 교체합니다.

- `--archive release.zip`이 onefile 또는 onedir 산출물을 ZIP으로 만들고 검증용 `release.zip.sha256`을 함께 생성합니다.

- `hython exe 프로그램.hbc -o 프로그램.exe`가 검증된 HBC payload와 Python 3.14·Hython VM을 Windows one-file PE에 내장해 원본 HBC 없이 실행되는 독립 EXE를 생성합니다.

- 콘솔·windowed·아이콘 빌드를 지원하고, 입력 폴더 또는 `--module-root` 아래 HBC 모듈의 디렉터리 구조와 각 모듈의 Python import를 자동 수집해 함께 번들합니다.

- 임시 PyInstaller 빌드가 성공하고 유효한 EXE를 생성한 뒤에만 기존 출력 파일을 원자적으로 교체하며, 실패 시 기존 EXE를 보존합니다. EXE 도구는 `hython-lang[exe]` 선택 의존성으로 제공합니다.

- `compile -o`가 존재하지 않는 출력 디렉터리를 자동 생성해 HBC→EXE 빌드 파이프라인을 끊지 않습니다.

- `hython compiler check/update/info/rollback/remove`로 공식 PyPI의 Hython compiler wheel을 SHA-256 검증하고 코어 설치본과 분리된 `~/.hython/compilers`에 설치·활성화합니다.

- 새 컴파일러는 안전한 wheel 경로 검사와 격리 smoke test를 통과한 뒤에만 원자적으로 활성화되며, 다운로드·해시·압축·실행 검증 실패 시 기존 컴파일러를 그대로 유지합니다.

- 활성 외부 컴파일러를 다음 명령부터 `PYTHONPATH` 우선순위로 자동 실행하고, 최대 10개의 이전 활성 이력에서 롤백하거나 특정 버전을 제거할 수 있습니다.

- `hython init`과 최초 CLI 자동 초기화를 추가해 코어 설치 파일을 수정하지 않고 활성 Python 문법 프로필을 외부 상태에 생성합니다.

- `hython update`가 공식 install manager로 최신 `default` Python을 설치한 뒤 그 런타임에서 문법·패키지 사전을 재생성하고, 이후 명령의 전역 기본 런타임으로 활성화합니다.

- `hython package uninstall`과 전체 사전 재조정이 제거된 패키지의 발음 문법을 삭제하며, 설치·갱신 사전은 임시 파일과 원자적 교체로 중간 실패 시 기존 상태를 보존합니다.

- 개발 버전의 배포 메타데이터가 `Production/Stable`을 주장하지 않도록 PyPI 개발 상태를 `Beta`로 바로잡고 릴리스 계약으로 고정합니다.

- `CLASS_BEGIN`·`CLASS_ARG` 명령 집합 변경을 형식에 명시하기 위해 HBC를 v6으로 올리고, 이전 v5 artifact를 모호하게 실행하지 않고 명확히 거부합니다.

- 번들 `examples/컴파일.hbc`를 현재 v6 컴파일러로 재생성해 문서의 `execute` 예제가 설치 직후 실행되도록 맞춥니다.

- 외부 Python 예외 처리기에서 `yield from` Hython delegate와 async generator를 재개할 때의 임시 예외 상속·yield 후 제거를 교차 회귀 게이트로 고정합니다.

- Hython generator를 Python `next()`·`for` 또는 HBC 호출자가 예외 처리기에서 재개하면 caller 예외를 해당 재개 동안만 상속하고, yield 뒤 다음 재개에는 누출하지 않습니다.

- Python descriptor·operator 등 객체 모델이 동기 Hython 함수를 암시적으로 호출할 때 `sys.exception()`의 활성 예외를 전달해 bare `raise` 의미를 보존하며, suspended 함수 생성은 예외를 캡처하지 않습니다.

- CPython/HBC 의미 차등 행렬도 Python 3.14의 모든 concrete AST 노드군을 포함하도록 제어 흐름·표현식/t-string·패턴·async for/with 복합 사례와 구조 게이트를 추가합니다.

- Python 3.14의 concrete statement·expression·pattern·type-parameter AST 노드가 공식 syntax matrix에 모두 포함되는 구조 커버리지 게이트를 추가하고 singleton pattern·TypeVarTuple·ParamSpec 차등 사례를 보강합니다.

- `package install`이 extras·비교 연산자·direct-reference를 포함한 배포 지정자에서 import 모듈명을 안전하게 추론하며, URL/경로만 주어지면 설치 전에 `--module`을 요구합니다.

- dotted 패키지 사전 스캔이 부모 `__init__.py`를 import하지 않도록 `PathFinder` 기반 정적 spec 탐색을 사용하고, malformed 사용자 사전은 안전하게 건너뜁니다.

- 함수 호출과 클래스 starred base에서 `iter()` 획득 실패만 비반복 오류로 변환하고, 반복 도중 사용자 iterator가 낸 `TypeError`는 원문 그대로 보존합니다.

- 클래스 헤더 `**mapping`이 `.items()` 대신 Python 호출 규약의 `keys()`·`__getitem__` duck mapping을 받아들이고 문자열 키를 검증합니다.

- 클래스 헤더 인자를 `CLASS_BEGIN`·`CLASS_ARG`로 순차 병합해 `*`/`**` 프로토콜 또는 중복 키 실패 시 뒤쪽 base·keyword·metaclass 식을 평가하지 않습니다.

- generic class 메서드의 실행 closure에 숨은 class type-parameter scope를 연결해 본문과 `locals()`에서 class·method 타입 매개변수를 Python 3.14처럼 읽습니다.

- generic class의 평가용 type parameter 바인딩을 `locals()`·`vars()`·`dir()`에서 숨기되, 같은 이름을 실제 클래스 속성으로 shadow하면 노출하도록 Python 3.14 scope를 재현합니다.

- 클래스 실행 중 생성된 메서드를 직접 추적해 decorator가 함수 객체를 컨테이너나 사용자 descriptor에 감춰도 lazy annotation의 클래스 scope를 유지합니다.

- 클래스 문맥의 private annotation 식별자를 저장 문자열에도 맹글링해 `STRING`·`FORWARDREF` 형식을 Python 3.14와 일치시키며 문자열 리터럴은 보존합니다.

- 메서드 실행 closure와 Python 3.14 annotation scope를 분리해 lazy annotation이 live class binding과 private class name을 해석하도록 합니다.

- generic 메서드 type parameter가 동명 class type parameter를 가리고, 다른 이름은 class type parameter로 fallback하는 annotation 조회 순서를 구현합니다.

- class body 패턴의 private class 이름과 value/mapping qualified path를 구성요소별로 맹글링하되 class-pattern keyword attribute는 Python처럼 원문 이름을 유지합니다.

- 함수 metadata를 생성 객체에 전달해 중첩 generator·coroutine·async generator의 `__qualname__`을 `outer.<locals>.inner` 형식으로 보존합니다.

- Python 3.13+처럼 `generator.close()`가 `GeneratorExit` 처리기나 `finally`의 제너레이터 반환값을 돌려주며 `yield from` delegate의 close 반환값은 무시합니다.

- 제너레이터·코루틴·비동기 제너레이터에 Python 3.14 `gi_suspended`, `cr_suspended`, `ag_suspended` 상태 속성을 추가하고 생성·일시중단·종료 수명주기를 맞춥니다.

- HythonCoroutine 자체를 `__await__` iterator facade로 사용해 native await, 수동 `send/throw`, iterator `close`가 동일한 실행·종료·재사용 방지 상태 머신을 통과합니다.

- 클래스 lazy annotation scope를 생성 시 snapshot에서 live class `__dict__` view로 바꿔 생성 후 속성 추가·변경·삭제와 전역 fallback을 반영합니다.

- generic 클래스의 숨겨진 type parameter는 annotation scope에 유지하되 class body의 동명 실제 binding이 우선하도록 조회 순서를 맞춥니다.

- HythonModule이 native `ModuleType`의 `__annotations__`/`__annotate__` 쓰기·검증·캐시 무효화 프로토콜을 그대로 상속함을 회귀 검증합니다.

- import된 HBC 모듈의 Python 3.14 lazy annotation owner와 평가 scope를 실제 `ModuleType` 객체에 재결속해 이후 module globals 변경을 반영합니다.

- `module.__annotations__` 속성 접근 시 VALUE 평가하고 `__annotate__`는 STRING/FORWARDREF 포맷 thunk로 유지해 `annotationlib.get_annotations()` fallback 의미를 맞춥니다.

- 실패한 annotation VALUE 평가는 부분 결과를 캐시하지 않으며 함수·클래스·모듈 STRING/FORWARDREF 재평가의 CPython 부작용 순서를 보존합니다.

- README와 언어·컴파일러 문서를 현재 HBC v5, 독립 스택 HIR, native import bridge와 Python 3.14 네이티브 지원 범위에 맞춰 갱신했습니다.

- 보존된 1.x 안정판 설명과 진행 중인 2.0 개발판 지원표를 분리하고 문법·의미 차등 검증 근거를 명시합니다.

- HBC 함수의 VM 내부 dataclass 상태와 사용자 `function.__dict__`를 분리해 점 속성 대입·삭제와 dict 전체 교체를 Python 함수처럼 처리합니다.

- `function.__builtins__`를 정의 시점 namespace로 고정하고 `__globals__`·`__closure__`·`__builtins__` 읽기 전용 의미와 HBC `__code__` 교체를 지원합니다.

- 클래스 선언 시작 줄을 HBC에 보존해 Python 3.14 `__firstlineno__`를 class body 실행 전과 metaclass namespace에 제공합니다.

- decorated 클래스는 첫 decorator 줄, 일반·중첩 클래스는 `class` 줄을 사용하며 class body의 명시적 `__firstlineno__` 덮어쓰기를 보존합니다.

- Python 3.14 클래스의 `__static_attributes__`를 정적 분석해 `self.attr` 저장 이름을 중첩 함수·staticmethod까지 수집하고 정렬 tuple로 metaclass namespace에 제공합니다.

- 다른 변수의 속성 저장, 삭제, 값 없는 속성 주석과 중첩 클래스의 저장은 바깥 클래스 정적 속성에서 제외합니다.

- 클래스 private name mangling을 컴파일 문맥에 구현해 필드·메서드·매개변수·주석·descriptor·패턴·중첩 scope·상속·전역/비지역 선언을 CPython 규칙과 일치시킵니다.

- 중첩 클래스는 자체 접두사를 사용하고 선행 밑줄은 제거하며, 뒤가 `__`인 magic 이름과 형식 매개변수 객체의 원래 이름은 보존합니다.

- 반복 절 자체는 동기식이지만 원소·키·값·필터에 `await`가 있는 비동기 list/set/dict comprehension과 generator expression을 전체 노드 기준으로 분류하고 실행합니다.

- CPython 3.14와 HBC VM의 대표 실행 결과를 직접 비교하는 의미 차등 매트릭스를 추가했습니다.

- Python 3.14 네이티브/HBC 문법 수용성 매트릭스를 19개에서 54개 대표군으로 확대해 주요 문장·표현식 AST 계열과 generic 선언을 포괄합니다.

- 비동기 comprehension의 필터·키·값·원소식에 중첩된 `await`도 자식 HBC 코루틴을 따라 부모 `cr_await`에 실제 awaitable로 노출합니다.

- 비동기 list/set/dict comprehension의 모든 비동기 절이 실제 `__anext__` awaitable을 코루틴 `cr_await`에 노출합니다.

- `async for`와 `async with`가 암묵적으로 기다리는 `__anext__`, `__aenter__`, `__aexit__` awaitable도 코루틴 `cr_await`에 노출합니다.

- 코루틴의 `cr_await`가 현재 awaitable을 일시 중단 동안 노출하고 완료·예외·종료 시 정확히 해제됩니다.

- 비동기 생성기의 `ag_await`가 거짓으로 평가되는 awaitable도 누락하지 않도록 `None` 여부로 대기 상태를 판별합니다.

- 잘못된 `__await__` 반환형과 대기 중 코루틴 종료의 상태 정리를 회귀 검증합니다.

## 2.0.0-dev143

- Python 3.14 `TypeVarTuple`의 unpack 기본값(`*Ts = *tuple[...]`)과 뒤 variadic 매개변수 전방 참조를 지연 원문 evaluator로 처리합니다.

- 형식 매개변수 기본값·bound의 지연 evaluator가 정의 그룹 전체를 보존해 `T=U, U=int` 같은 뒤 매개변수 전방 참조를 지원합니다.

- 중첩 클래스의 `nonlocal` 읽기도 선언된 free-name 경로를 사용해 바깥 클래스의 동명 속성을 건너뛰고 함수 binding을 읽습니다.

- 여러 단계 중첩 클래스의 `nonlocal` 탐색이 바깥 클래스 namespace를 모두 건너뛰고 가장 가까운 함수 binding을 갱신합니다.

- 함수 안 중첩 클래스 본문의 `nonlocal` 선언이 바깥 함수 binding을 정적으로 찾고 HBC 실행 중 대입·삭제할 수 있도록 클래스 closure를 연결합니다.

- class pattern의 사용된 `__match_args__` 안에서 위치 속성명이 반복되면 Python처럼 `TypeError`를 발생시키며 위치·키워드 전체 중복을 선언 순서대로 검사합니다.

- 키워드 전용 class pattern은 Python처럼 `__match_args__`를 조회하지 않아 metaclass descriptor의 불필요한 부작용·예외를 피합니다.

- 메서드가 `__class__`를 직접 대입·삭제하면 Python처럼 지역 변수로 분류하고 implicit class cell/owner를 주입하지 않아 `super()` 오류 의미를 보존합니다.

- class body 메서드의 직접 `__class__` 참조도 cell 요구로 탐지해 descriptor `__set_name__` 중 조기 호출에서 새 클래스 객체를 읽을 수 있습니다.

- zero-argument `super()`의 `__classcell__`을 class body 함수 생성 즉시 연결해 임의 decorator가 원본 메서드를 사용자 descriptor 안에 숨겨도 cell을 보존합니다.

- `type.__new__`가 descriptor `__set_name__`을 실행하는 시점에도 새 클래스의 HBC 메서드가 zero-argument `super()`를 사용할 수 있도록 실제 `__classcell__`을 연결합니다.

- 알려진 부모 패키지 없이 상대 import를 실행하면 내부 모듈 탐색 오류 대신 Python과 같은 `ImportError`를 발생시킵니다.

- 값 없는 속성·구독 대상 주석(`객체.속성: 타입`, `자료[키]: 타입`)이 Python처럼 대상 표현식만 순서대로 평가하고 주석식이나 저장 동작은 실행하지 않습니다.

- `except ... as 이름` 처리기에서 중첩 closure를 반환해도 처리기 종료 시 별칭 cell을 비워 Python의 순환 참조 방지 의미를 유지함을 회귀 검증합니다.

- 본문에 `yield` 또는 `yield from` 표현식이 있는 람다를 Python처럼 제너레이터 함수로 컴파일합니다.

- 람다 함수의 `__name__`과 중첩 `__qualname__`을 Python과 같은 `<lambda>`로 노출하고, 정의 시점 기본값과 실행 시점 클로저 동작을 회귀 테스트로 고정했습니다.

- generator expression이 생성 시 복사된 locals가 아니라 살아 있는 바깥 scope binding을 각 지연 실행 시점에 읽습니다.
- comprehension 반복 변수는 계속 격리하면서 `:=` 대상만 바깥 scope에 즉시 게시합니다.

## 2.0.0-dev126 - 개발 중

- 클래스 decorator가 최종 이름 binding 전에 lazy annotation을 읽으면 동명 이전 전역 binding을 보도록 Python 3.14 시점을 따릅니다.
- generic 클래스 type parameter를 annotation scope와 `__type_params__`에는 보존하되 실제 클래스 속성으로 노출하지 않습니다.

## 2.0.0-dev125 - 개발 중

- generic 함수의 기본값을 type parameter annotation scope 생성 전에 평가해 동명 바깥 binding을 참조하도록 Python 3.14와 일치시킵니다.
- generic 클래스의 base·header는 새 type parameter를 계속 참조하며 평가 실패 시 기존 이름을 롤백합니다.

## 2.0.0-dev124 - 개발 중

- generic 정의의 기본값·header 평가가 실패해도 미완료 `SAVE_NAME` 상태를 code-object 예외 경계에서 자동 롤백합니다.
- 예외가 같은 scope의 `try`에서 처리되거나 바깥 호출자까지 전파되는 경우 모두 기존 type-parameter 동명 binding과 정의 이름 미바인딩 상태를 보존합니다.

## 2.0.0-dev123 - 개발 중

- HBC v5 `SAVE_NAME`·`RESTORE_NAME` 명령으로 generic 함수·클래스 정의 중 임시 type parameter binding 뒤 기존 동명 이름을 복원합니다.
- type parameter가 없던 이름은 정의 후 제거하고, 기존 전역·지역 binding은 값과 정체성을 그대로 보존합니다.

## 2.0.0-dev122 - 개발 중

- 함수 기본값과 클래스 base·header 인자에서 사용한 이름을 뒤따르는 `global`·`nonlocal` 선언보다 앞선 사용으로 정확히 판정합니다.
- Python 3.14 lazy annotation 표현식은 정의 시점 이름 사용으로 계산하지 않는 scope 규칙을 유지합니다.

## 2.0.0-dev121 - 개발 중

- dotted HBC import가 자식 module 실행 전에 부모 package와 `__init__.hbc`를 먼저 초기화합니다.
- 자식 로드 성공 후 부모 package 속성에 module을 연결하며 순환 import에서는 이미 노출된 부분 초기화 부모를 재사용합니다.

## 2.0.0-dev120 - 개발 중

- custom metaclass가 `type`이 아닌 임의 객체를 반환해도 클래스 문이 그 객체를 이름에 정상 바인딩합니다.
- 실제 class 객체가 생성된 경우에만 하이썬 method의 class-owner·zero-argument `super()` 연결을 수행합니다.

## 2.0.0-dev119 - 개발 중

- `with`·`async with` 본문과 exit hook이 동일한 예외 인스턴스를 재전파할 때 예외가 자기 자신을 `__context__`로 참조하지 않도록 수정합니다.
- 동기·비동기 다중 manager unwinder가 CPython처럼 원래 예외 인스턴스와 빈 context를 보존합니다.

## 2.0.0-dev118 - 개발 중

- coroutine의 `throw()`·`close()`가 실행 중 재진입을 `ValueError`로 거부하고 `send()`와 같은 단일 실행 규칙을 따릅니다.
- coroutine이 정상 반환뿐 아니라 예외로 종료된 경우에도 완료 상태를 고정해 이후 `send()`·`throw()` 재사용을 `RuntimeError`로 처리합니다.

## 2.0.0-dev117 - 개발 중

- async generator가 내부 `await`에서 정지한 동안 두 번째 `anext()`·`asend()`·`athrow()`·`aclose()` 재진입을 CPython처럼 `RuntimeError`로 거부합니다.
- 비동기 frame의 단일 실행 보장을 통해 동시 구동에 따른 stack·delegate 상태 손상을 방지합니다.

## 2.0.0-dev116 - 개발 중

- `generator.close()`가 중단 지점에 `GeneratorExit`를 주입해 `finally`와 컨텍스트 정리를 실제로 실행합니다.
- 종료 처리 중 다시 값을 yield하는 generator는 조용히 폐기하지 않고 CPython처럼 `RuntimeError: generator ignored GeneratorExit`를 발생시킵니다.
- `yield from` 위임 중 닫을 때 대상의 `throw()`가 아닌 `close()` 훅을 직접 호출합니다.

## 2.0.0-dev115 - 개발 중

- Python 3.14가 허용하는 두 번째 수준의 f-string·t-string 중첩 format spec을 파싱하고 평가합니다.
- 그보다 깊은 보간 중첩은 CPython과 동일하게 컴파일 단계에서 거부합니다.

## 2.0.0-dev114 - 개발 중

- `**mapping` 호출 확장에서 비문자열 키 검증을 실제 함수 호출 직전까지 지연해 매핑 값 조회와 뒤쪽 인자 표현식의 평가 순서를 CPython과 일치시킵니다.
- 중복 키는 확장 시점에 계속 즉시 거부하면서, 최종 키워드 이름 검증은 하이썬 함수와 네이티브 callable에 동일하게 적용합니다.

## 2.0.0-dev113 - 개발 중

- `except*` 처리기에서 bare `raise`로 재전파한 하위 그룹과 처리되지 않은 나머지를 원본 `ExceptionGroup` 트리로 재구성합니다.
- `except*` 처리 중 새 예외가 발생하면 새 예외와 원본에서 파생된 미처리 subgroup을 CPython과 같은 빈 메시지 그룹으로 병합합니다.

## 2.0.0-dev112 - 개발 중

- `int(값)`·`str(값)`·`list(값)` 등 Python 내장 형식과 그 하위 형식의 클래스 패턴이 대상 객체 자체를 위치 패턴에 전달합니다.
- 클래스 패턴은 실제로 사용되는 `__match_args__` 항목만 문자열인지 검사해 CPython의 지연 검증 의미론을 따릅니다.
- 별표 sequence pattern이 대상 객체의 슬라이스 지원을 요구하지 않고 정수 인덱싱 프로토콜만으로 나머지 목록을 구성합니다.

## 2.0.0-dev111 - 개발 중

- async for·비동기 컴프리헨션·비동기 제너레이터 위임이 `aiter()`/`anext()`를 사용해 `__aiter__`·`__anext__`를 타입에서 조회하도록 CPython 특별 메서드 규칙과 일치시킵니다.
- 인스턴스 속성으로 비동기 반복 프로토콜을 위장하지 못하며 타입 수준 `__anext__` 누락을 즉시 `TypeError`로 처리합니다.

## 2.0.0-dev110 - 개발 중

- 확장이 없는 일반 set·dict 리터럴도 HBC v4 순차 collection builder를 사용해 각 항목을 평가 직후 삽입합니다.
- set 항목 및 dict 키의 hash·동등성 검사 실패가 뒤쪽 항목 표현식 평가 전에 발생하고, dict는 키→값→삽입 순서를 보존합니다.

## 2.0.0-dev109 - 개발 중

- 리스트·튜플·집합·딕셔너리 리터럴을 소스 순서대로 즉시 확장하는 HBC v4 collection builder 명령을 도입합니다.
- `*`/`**` 확장 실패가 뒤쪽 표현식 평가 전에 발생하고, 딕셔너리 `**`는 iterable-of-pairs가 아닌 mapping protocol만 허용합니다.

## 2.0.0-dev108 - 개발 중

- 별표 없는 구조 분해가 iterable 전체를 리스트화하지 않고 필요한 개수보다 한 항목만 더 읽어 과다 여부를 판정하도록 수정합니다.
- 일반 VM·생성기·코루틴과 for/with/comprehension 복합 대상이 부족·과다 구조 분해에 Python 호환 `ValueError`를 발생시킵니다.

## 2.0.0-dev107 - 개발 중

- 연쇄 비교가 중간 결과에만 진리값 검사를 적용하고, 단락된 비교 객체 또는 마지막 비교 객체 자체를 반환하도록 CPython의 `and`형 의미론과 일치시킵니다.
- 동일 동작을 일반 VM·생성기·코루틴 비교 체인에 적용합니다.

## 2.0.0-dev106 - 개발 중

- assert 메시지 표현식을 조건 실패 분기로 이동해 조건이 참이면 평가하지 않고, 실패할 때만 한 번 평가하도록 CPython 의미론과 일치시킵니다.
- 네이티브 개발 문서의 독립 바이트코드 표기를 HBC v3로 갱신합니다.

## 2.0.0-dev105 - 개발 중

- 함수 내부 generic과 type alias의 annotation scope가 현재 정의 scope, 다단계 `$closure`, VM globals를 순서대로 탐색하도록 보강합니다.
- type parameter bound/default와 alias value가 정의 함수 반환 뒤에도 전역·비지역 이름 및 나중에 변경된 지역 셀 값을 지연 평가합니다.

## 2.0.0-dev104 - 개발 중

- 일반 VM·생성기·코루틴의 클래스 생성 코드를 하나의 metaclass 경로로 통합합니다.
- `__prepare__` namespace에 `dict.update`, `pop`, `values`를 요구하지 않고 기본 mapping protocol만으로 클래스 본문 실행, 내부 상태 정리, 메서드 바인딩을 수행합니다.

## 2.0.0-dev103 - 개발 중

- decorated 함수·클래스의 원본 객체를 이름에 미리 노출하지 않고 모든 decorator 적용이 성공한 뒤 최종 결과만 바인딩하도록 CPython 정의 의미론과 일치시킵니다.
- decorator 표현식은 위에서 아래로 평가하고 기본값·클래스 본문 생성 뒤 아래에서 위로 적용하며, 적용 실패 시 기존 이름 바인딩을 보존합니다.

## 2.0.0-dev102 - 개발 중

- 증강 할당이 일반 이항 연산 대신 `__iadd__`, `__imul__` 등 Python의 제자리 연산 프로토콜을 사용하도록 전용 HBC 명령을 추가합니다.
- 이름·속성·구독 증강 할당에서 공유 가변 객체와 사용자 정의 `__i*__` 반환값을 보존하며 복합 대상을 한 번만 평가합니다.

## 2.0.0-dev101 - 개발 중

- 혼합 호출 인자를 소스 순서대로 즉시 누적하는 HBC v3 호출 명령을 도입해 `*` iterable 및 `**` mapping 검증과 키워드 중복 오류가 뒤쪽 인자 평가 전에 발생하도록 CPython과 일치시킵니다.
- 새 호출 누적 명령을 일반 VM, 생성기, 코루틴 실행기에 모두 지원합니다.

## 2.0.0-dev100 - 개발 중

- Hython 함수 descriptor의 `__get__(instance, owner=None)` 계약을 Python 함수와 맞춰 owner 인자를 생략한 직접 바인딩을 지원합니다.
- 데이터/비데이터 descriptor 우선순위와 `__getattribute__`/`__getattr__`, 속성 설정·삭제 hook의 객체 모델 호환성을 검증합니다.

## 2.0.0-dev99 - 개발 중

- 전파 중인 예외의 `finally` 블록과 그 안에서 호출된 함수에서 bare `raise`가 원래 예외를 재발생시키도록 활성 예외 상태를 보존합니다.
- 일반 함수, 생성기, 코루틴에서 암시적 context와 명시적 cause 및 `from None` 억제 상태를 CPython과 동일하게 유지합니다.

## 2.0.0-dev98 - 개발 중

- `with`와 `async with`가 문맥 관리자의 특별 메서드를 인스턴스가 아닌 타입에서 조회하고, 진입 전에 종료 메서드까지 확인하도록 CPython 의미론과 일치시킵니다.
- 코루틴의 `with` 안에서 발생한 return/break/continue를 `__exit__`에 예외로 노출하지 않고 정상 제어 흐름으로 처리합니다.

## 2.0.0-dev97 - 개발 중

- 제너레이터에서 빠져나온 StopIteration/StopAsyncIteration을 정상 return 종료와 구분해 원인 예외가 연결된 RuntimeError로 변환합니다.

## 2.0.0-dev96

- `barry_as_FLUFL` future 기능이 활성화되면 `<>`를 not-equal로 허용하고 `!=`를 구문 오류로 전환합니다.

## 2.0.0-dev95

- `__future__` import의 파일 선두/docstring 배치, 중첩 범위 금지, 알려진 기능명, `*` 및 `braces` 거부 규칙을 컴파일 단계에서 검증합니다.

## 2.0.0-dev94

- `await` operand를 primary/postfix chain으로 제한해 산술·거듭제곱·비교가 바깥에서 결합되도록 하고, 괄호 없는 단항·not·lambda·중첩 await를 거부합니다.

## 2.0.0-dev93

- `not`의 결합력을 비교·멤버십보다 낮고 `and`·`or`보다 높게 분리해 Python의 불리언 우선순위를 정확히 구현합니다.

## 2.0.0-dev92

- 함수·클래스·type alias의 빈 타입 매개변수 목록을 거부하고, TypeVarTuple·ParamSpec의 기본값은 허용하되 금지된 bound는 거부합니다.

## 2.0.0-dev91

- 대입·연쇄 대입·복합 대입·return·yield의 expression-list에서 단일 후행 쉼표를 1원소 튜플로 보존하고, 복합 대입의 괄호 없는 튜플 RHS를 지원합니다.

## 2.0.0-dev90

- `match` subject의 괄호 없는 expression-list, 단일 후행 쉼표, 별표 unpack을 subject 튜플 생성 문법으로 지원합니다.

## 2.0.0-dev89

- 동기·비동기 `for ... in`의 괄호 없는 iterable expression-list와 후행 쉼표를 튜플 iterable로 지원합니다.

## 2.0.0-dev88

- 일반 `yield`의 튜플 expression-list와 `yield from`의 단일 표현식 문법을 분리해, 괄호 없는 다중 `yield from` 피연산자를 거부합니다.

## 2.0.0-dev87

- `del`의 후행 쉼표, 괄호·리스트 중첩 대상, 빈 튜플·리스트 대상을 지원하고 이름·속성·첨자를 재귀적으로 왼쪽부터 삭제합니다.

## 2.0.0-dev86

- Python 3.14의 빈 괄호형 `with ():`와 괄호형 관리자 목록 내부의 직접 명명식(`이름 := 문맥`)을 지원합니다.

## 2.0.0-dev85

- 함수 호출에서 일반 키워드 뒤 `*args`는 허용하되 `**kwargs` 뒤 `*args`는 CPython처럼 구문 오류로 거부합니다.

## 2.0.0-dev84

- 첨자의 마지막 쉼표와 PEP 646 별표 항목을 튜플 키로 처리하고, 빈 첨자 및 slice 경계의 별표 표현식을 구문 오류로 거부합니다.

## 2.0.0-dev83

- 음수·복소수·열린 시퀀스·그룹 패턴을 지원하고, `as _`, `**_`, 다중/비마지막 `**rest`, 클래스 키워드 뒤 위치 패턴을 거부합니다.

## 2.0.0-dev82

- Python 3.14의 괄호 없는 다중 `except`/`except*` 타입을 지원하고, handler 없는 `else` 및 종료된 try 뒤의 고아 예외 절을 거부합니다.

## 2.0.0-dev81

- 빈 세미콜론 문장과 빈 한 줄 suite를 거부하고, 콜론 뒤 한 줄 suite에는 CPython처럼 단순 문장만 허용합니다.

## 2.0.0-dev80

- `...` 토큰을 포함한 임의 깊이 상대 import를 파싱하고, 일반 `import *`, 별표 import의 별칭·혼합·괄호 사용을 CPython처럼 거부합니다.

## 2.0.0-dev79

- `for *대상, in ...`의 한 원소 구조 분해 튜플을 지원하고, 컴프리헨션과 `with as`를 포함한 각 대상 수준에서 별표 대상이 하나뿐인지 검증합니다.

## 2.0.0-dev78

- 클래스 헤더의 마지막 쉼표를 지원하고, base·`*bases`·키워드·`**kwargs`를 소스 순서대로 평가하며 잘못된 위치/별표 unpack 순서를 정적으로 거부합니다.

## 2.0.0-dev77

- 함수와 람다 매개변수 목록의 마지막 쉼표를 `/`, `*args`, 키워드 전용 인자까지 지원하고, 람다의 중복 이름·잘못된 `/`·빈 `*`를 정적으로 검증합니다.

## 2.0.0-dev76

- 잘못된 숫자 밑줄·진법처럼 토큰 경계에서 발생하는 모든 프런트엔드 `SyntaxError`에도 실제 `.hy` 파일명을 보존합니다.

## 2.0.0-dev75

- 문자열·bytes·숫자 리터럴 구문 분석에 실제 `.hy` 파일명을 전달하여 리터럴 오류와 `SyntaxWarning`의 진단 파일 위치를 보존합니다.

## 2.0.0-dev74

- 인접한 일반 문자열과 f-string, 여러 f-string, 여러 t-string 리터럴을 CPython 3.14와 같은 원자 단계에서 결합하며 t-string과 다른 문자열 종류의 혼합은 거부합니다.

## 2.0.0-dev73

- 컴프리헨션 iterable의 중첩 람다·함수 범위 안에 숨은 `:=`도 CPython 3.14처럼 정적 구문 오류로 거부합니다.
- 타입 별칭과 타입 매개변수 바운드·기본값의 직접 `:=`를 거부하되, 주석 및 타입 식 내부 람다의 지역 `:=`는 허용합니다.

## 2.0.0-dev72

- f/t-문자열의 `!s`, `!r`, `!a` 이외 변환을 컴파일 단계에서 거부하고, 형식 지정자 내부 보간의 변환(`{값!r}`)을 지원합니다.

## 2.0.0-dev71

- t-문자열 `Interpolation.expression`과 f/t-문자열 디버그 접두사가 원본 하이썬 소스의 선행·내부·후행 공백을 CPython 3.14와 동일하게 보존합니다.

## 2.0.0-dev70

- 함수 `__annotations__` 쓰기·None 초기화·dict 형식 검증
- 변경된 함수 주석을 `inspect.signature()`에 즉시 반영
- Python 3.14 `__annotate__` callable/None 쓰기 프로토콜
- 사용자 지정 annotation 평가 함수의 지연 실행과 결과 캐싱
- 쓰기 가능한 `__name__`·`__qualname__` 및 문자열 형식 검증
- 임의 객체를 허용하는 `__module__`·`__doc__` 쓰기 계약
- 쓰기 가능한 `__type_params__` 튜플 메타데이터와 형식 검증

## 2.0.0-dev69 - 개발 중

- Hython 함수의 쓰기 가능한 `__defaults__` Python 객체 프로토콜
- 쓰기 가능한 `__kwdefaults__`와 키워드 전용 기본값 교체
- 변경된 기본값을 이후 HBC 호출 인자 바인딩에 즉시 반영
- 변경된 기본값을 `inspect.signature()` 결과에 반영
- 매개변수보다 긴 위치 기본값 튜플의 원형 보존과 마지막 값 매핑
- None 대입으로 기본값 제거 및 필수 인자 복원
- 잘못된 list/tuple 기본값 컨테이너의 Python 호환 TypeError

## 2.0.0-dev68 - 개발 중

- 중첩 함수의 `바깥.<locals>.안쪽` Python 호환 qualified name
- 함수 내부 지역 클래스와 메서드의 전체 `__qualname__` 구성
- 중첩 클래스·메서드의 `외부.내부.메서드` qualified name
- 동기·제너레이터·코루틴 함수 프레임에 중첩 정의 접두사 전달
- qualified-name 내부 프레임 메타데이터를 locals()/vars()에서 숨김
- 클래스 본문에서 실제 생성된 함수만 `__class__` 셀에 연결
- 데코레이터가 반환한 외부 함수의 원래 qualname·클래스 소유권 보존

## 2.0.0-dev67 - 개발 중

- 무인자 super()를 모든 Python 문맥에서 구문적으로 허용
- 모듈·무매개변수 함수의 super() 오류를 컴파일 시점에서 실행 시점으로 이동
- 클래스 셀이 없는 일반 함수의 `super(): __class__ cell not found`
- 삭제된 첫 매개변수의 `super(): arg[0] deleted`
- 유효한 메서드의 기존 무인자 super() 디스크립터 동작 유지
- 동기·제너레이터·코루틴 SUPER opcode 런타임 검증 통일
- 잘못된 super()도 HBC로 컴파일된 뒤 Python 호환 RuntimeError 발생

## 2.0.0-dev66 - 개발 중

- HBC handler의 `sys.exception()`·`sys.exc_info()` 표준 API 브리지
- except* handler에서 원본 그룹 대신 현재 매칭된 하위 그룹 노출
- sys.exc_info()의 예외 형식·인스턴스·트레이스백 일치
- handler가 호출한 네이티브 Python 콜백에도 HBC 활성 예외 전달
- 제너레이터 중단·재개 후 표준 예외 관찰 상태 복원
- handler 종료 뒤 sys.exception()/exc_info() 상태 누출 방지
- 동기·제너레이터·코루틴의 프레임 예외 메타데이터와 표준 API 통합

## 2.0.0-dev65 - 개발 중

- Python 예외 상태의 호출 시점 상속 규칙을 CPython과 직접 차등 교정
- handler에서 호출한 동기 함수의 bare raise 활성 예외 상속
- handler에서 즉시 await한 코루틴의 활성 예외 상속
- handler에서 생성했지만 나중에 실행한 코루틴은 예외를 캡처하지 않음
- handler 안에서 next/send로 재개한 제너레이터의 활성 예외 상속
- 자체 handler에서 중단된 제너레이터·코루틴의 저장 예외 우선 보존
- dev64의 잘못된 호출 함수 비상속 설명 정정

## 2.0.0-dev64 - 개발 중

- bare raise의 활성 예외를 VM 전역이 아닌 HBC 프레임별로 격리
- 예외 handler 진입·퇴장 시 프레임 예외 상태 스택 저장·복원
- 예외 처리 중 yield한 제너레이터들의 교차 재개 안전성
- 예외 처리 중 await한 동시 코루틴들의 예외 상태 격리
- 중단된 제너레이터·코루틴별 활성 예외 상태를 독립 보존
- 동기·제너레이터·코루틴 RERAISE 실행 경로 통일
- 프레임 내부 메타데이터는 locals()·vars()에서 계속 숨김

## 2.0.0-dev63 - 개발 중

- HBC 모듈 객체를 표준 `types.ModuleType` 하위 객체로 변경
- `__spec__`·`__loader__`·`__cached__`·패키지 `__path__` 메타데이터
- 패키지 내부 상대 import를 정규 절대 모듈 이름으로 해석
- 상대 import된 하위 모듈의 `패키지.모듈` 이름 및 캐시 통일
- 상대 하위 모듈을 부모 패키지 속성으로 자동 연결
- HBC 네임스페이스 패키지에도 표준 ModuleSpec 제공
- 패키지 경계를 벗어나는 상대 import의 ImportError 계약

## 2.0.0-dev62 - 개발 중

- type 별칭 우변의 정규화된 원문 표현식을 HBC에 보존
- TypeAliasType.evaluate_value의 annotationlib STRING 포맷 호환
- 미해결 별칭 타입의 annotationlib FORWARDREF 포맷 호환
- TypeVar evaluate_bound·evaluate_default STRING 포맷 호환
- 타입 표현식 이름을 살아 있는 HBC 스코프에서 조회하는 전용 네임스페이스
- 새 value_text·bound_text·default_text HBC 필드 형식 검증
- 텍스트 메타데이터가 없는 이전 개발 HBC용 지연 평가 폴백 유지

## 2.0.0-dev61 - 개발 중

- Python 3.14 `type` 별칭 우변의 실제 지연 평가와 결과 캐싱
- 아직 정의되지 않은 타입을 별칭 우변에서 참조하는 전방 참조 지원
- 타입 별칭의 TypeVar 경계·기본값 지연 평가
- 함수·클래스 타입 매개변수 경계·기본값 지연 평가
- 지연 평가 중 발생하는 부작용이 정의 시점에는 실행되지 않도록 수정
- 뒤쪽 타입 매개변수 경계에서 앞쪽 타입 매개변수 캡처
- 런타임 객체를 표준 `typing.TypeAliasType`·TypeVar 계열로 유지

## 2.0.0-dev60 - 개발 중

- Python 3.14 주요 구문군 19종의 네이티브/HBC 컴파일 차등 매트릭스
- 세미콜론·줄 연속·괄호 with·확장 del·위치 전용 lambda 검증
- 디버그 f-string·중첩 포맷·except*·비동기 컴프리헨션 검증
- 패턴 가드·호출/컬렉션 언패킹·확장 슬라이스·t-string 검증
- eval·exec 기본 호출이 현재 HBC globals/locals 프레임을 사용
- eval·exec에 명시적 네임스페이스를 주면 Python 표준 동작 유지

## 2.0.0-dev59 - 개발 중

- Python 3.14 공개 내장 이름 151개의 어휘·VM 노출 전수 대조
- hash·compile·iter·format 등 기본 함수의 사람이 읽을 수 있는 발음 표기
- BaseException·RuntimeError·KeyError 등 핵심 예외 발음 표기
- 발음형 예외 이름을 raise·except에서 직접 사용하는 실행 계약 검증
- 명시 어휘 밖의 최신 Python 내장은 결정적 자동 발음 폴백 유지
- 키워드·내장을 합친 정방향·역방향 어휘 187개 간 충돌 없음 검증

## 2.0.0-dev58 - 개발 중

- 클래스 지역 바인딩이 둘러싼 함수 이름을 잘못 가리는 이름 해석 수정
- 클래스 HBC 메타데이터에 지역 이름 집합 기록 및 검증
- 클래스 컴프리헨션이 클래스 네임스페이스를 캡처하지 않도록 수정
- 함수 안의 클래스 컴프리헨션은 바깥 함수 클로저를 정상 캡처
- property getter·setter·deleter 전체에 `__class__` 셀 연결
- 바운드 메서드의 `__self__`·`__func__` 및 비교·해시 계약 구현
- Hython 함수 객체를 Python 함수처럼 동일성 기반 비교·해시로 변경

## 2.0.0-dev57 - 개발 중

- 정의되지 않은 이름 조회를 Python 호환 `NameError`로 통일
- 미할당 지역 이름 삭제를 `UnboundLocalError`로 통일
- 존재하지 않는 글로벌·논로컬 이름 삭제의 `NameError` 계약
- 함수 HBC 메타데이터에 명시적 자유변수(`free_names`) 기록 및 검증
- 삭제된 논로컬 셀이 같은 이름의 전역으로 잘못 폴백하는 문제 수정
- 동기 함수·제너레이터·코루틴의 이름 오류 동작 일치

## 2.0.0-dev56 - 개발 중

- 비동기 제너레이터 `asend()` 값 전달과 시작 전 None 제한
- `athrow()` 예외를 async-for/with 하위 본문 delegate까지 전달
- `aclose()`의 GeneratorExit 주입과 await 포함 finally 완료 대기
- GeneratorExit 이후 값을 yield하는 비동기 제너레이터 RuntimeError
- async-for/with 중간 delegate의 send·throw·close 양방향 브리지
- `ag_running`·`ag_await` 실행 상태 추적 강화

## 2.0.0-dev55 - 개발 중

- Hython AST에 표현식 괄호 여부 보존
- 최상위 표현식 문장·대입 RHS의 괄호 없는 `:=` 차단
- return·yield·raise·assert·with·for iterable의 명명식 괄호 규칙
- 함수/lambda 기본값·lambda 본문·키워드 인자의 명명식 검증
- dict key/value/unpack의 명명식 괄호 규칙
- 변수·매개변수·반환 주석 내부 명명식 전면 차단
- if·while·match·위치 호출·list/set/subscript의 허용 문맥 유지

## 2.0.0-dev54 - 개발 중

- 매핑 패턴의 `상수.이름` dotted value key 지원
- 부호 있는 숫자와 복소수 매핑 패턴 키 지원
- Mapping.get 기반 키 조회로 `__missing__` 비호출 의미 보존
- 런타임 동적 중복 매핑 키 `ValueError` 진단
- `모듈.클래스(...)` dotted class pattern 지원
- class pattern 형식·위치 개수·중복 속성·`__match_args__` 검증
- 전체 pattern HBC payload 재귀 검증

## 2.0.0-dev53 - 개발 중

- async generator의 값 있는 return과 명시적 `return None` 컴파일 차단
- async 함수 안의 `yield from` 문장·표현식 차단
- 함수·클래스 범위의 `from ... import *` 차단
- try/with 등 구조화 코드 객체 안의 루프 밖 break·continue 정적 검증
- bare return과 값 있는 return의 Hython AST 구분
- yield 표현식만 포함한 함수의 generator 판정 수정

## 2.0.0-dev52 - 개발 중

- 함수·클래스 정의와 decorator 결과의 global·nonlocal 바인딩
- import 별칭·type alias·명명식의 선언 범위 저장
- with/async with·async for 구조화 대상의 범위 정보 전달
- 예외 처리 별칭의 범위 저장 및 처리 후 정확한 삭제
- match 캡처·as·star·mapping-rest 패턴의 global·nonlocal 바인딩
- 구조화 대입 target과 중첩 코드 객체의 HBC 재귀 검증

## 2.0.0-dev51 - 개발 중

- `yield from`의 `send()` 하위 제너레이터 전달
- 일반 iterator에 None 이외 값을 send할 때 Python 호환 `AttributeError`
- 하위 제너레이터 `StopIteration.value`를 yield-from 표현식 결과로 전달
- 위임 중 `close()`의 하위 iterator 종료 보장
- generator·coroutine `throw()`의 예외 형식·값·traceback 인자 정규화

## 2.0.0-dev50 - 개발 중

- 다중 `with`·`async with`의 Python 호환 역순 unwind
- 진입에 성공한 컨텍스트 관리자만 종료 처리
- 안쪽 `__exit__`·`__aexit__` 신규 예외를 바깥 종료 메서드에 전달
- 바깥 종료 메서드의 신규 예외 억제 지원
- return·break·continue를 종료 메서드에 정상 종료로 전달
- 내부 Hython 제어 신호의 예외 `__context__` 누출 방지

## 2.0.0-dev49 - 개발 중

- 제너레이터 표현식 생성 시 최외곽 iterable과 `iter`/`__aiter__` 즉시 평가
- 요소·필터·후속 iterable의 지연 평가 유지
- 모듈 범위 비동기 제너레이터 표현식 생성 지원
- 컴프리헨션 `:=` 바인딩을 평가 즉시 포함 범위에 공개
- 비동기 컴프리헨션의 다중 필터 단락 평가 수정

## 2.0.0-dev48 - 개발 중

- 네이티브 HBC 실행 중 Python 표준 라이브러리·설치 패키지 import fallback
- 로컬 HBC 모듈과 HBC namespace package의 우선순위 유지
- Python 모듈의 선택 import·별칭·`import *` 경로 통합
- 누락 모듈과 누락 이름을 `ModuleNotFoundError`·`ImportError`로 진단

## 2.0.0-dev47 - 개발 중

- 함수 호출의 누락·초과·중복·위치 전용 위반을 Python 호환 `TypeError`로 통일
- `**` 호출 확장에서 문자열 키를 강제하고 비매핑 입력 진단
- `dict` 하위 형식이 아니어도 `keys`·`__getitem__` 매핑 프로토콜을 지원
- 위치 전용 매개변수와 같은 이름을 `**kwargs`로 별도 전달하는 Python 동작 지원

## 2.0.0-dev46 - 개발 중

- `nonlocal` 저장 시 프레임 지역 사본을 만들지 않고 공유 셀만 갱신
- 형제 클로저가 변경한 값을 같은 호출·제너레이터 프레임에서 즉시 관찰
- 코루틴 `DELETE_NONLOCAL`과 `MAKE_TYPE_PARAMETER` 명령 지원
- 주석 코드가 포함된 중첩 함수의 HBC 검증 중 검증 대상 오염 수정

## 2.0.0-dev45 - 개발 중

- 함수 전체의 `global`·`nonlocal` 선언을 코드 생성 전에 확정
- `try`, `except`, `finally`, `with`, `async for`, `async with` 하위 HBC 코드에 선언 범위 상속
- 구조화 코드 객체 안의 전역·비지역 대입이 잘못 지역화되는 문제 수정

## 2.0.0-dev44

- bare `except`의 `BaseException` 계열 처리
- 잘못된 예외 처리기 형식의 Python 호환 `TypeError`
- 일반 `BaseException`을 `except*`에서 `BaseExceptionGroup`으로 래핑

## 2.0.0-dev43

- 컴파일 시 함수 지역 이름 집합 생성 및 HBC 검증
- 대입 전 지역 이름의 `UnboundLocalError` 처리
- 다단계 `nonlocal` 탐색과 `locals`·`vars`·`dir` 범위 정리

## 2.0.0-dev28 - 개발 중

- 클래스 지역과 바깥 함수 클로저 범위 분리
- 메서드 암시적 `__class__` 셀과 인자 없는 `super()` 지원
- 클래스 내부 descriptor 함수의 소유 클래스 연결
- 컴프리헨션 반복 대상 격리 유지
- 컴프리헨션 `:=` 대상의 포함 범위 바인딩과 지연 갱신

## 2.0.0-dev27

- OR 패턴 바인딩 정합성과 중복 캡처 컴파일 검증
- as 패턴과 점 경로 값 패턴 지원
- property·staticmethod·classmethod descriptor 지원
- 바운드 메서드 키워드 인자 전달 수정
- 클래스 키워드·메타클래스 `__prepare__`·생성 과정 지원

## 2.0.0-dev26

- Ellipsis·bytes·complex·tuple HBC 상수 직렬화 지원
- 인접 문자열·바이트 리터럴 자동 결합
- 다차원 인덱스와 확장 슬라이스 조합 지원
- 호출 위치의 암시적 제너레이터 표현식과 후행 쉼표 지원
- 패턴 싱글턴 identity 및 Sequence·Mapping 프로토콜 매칭

## 2.0.0-dev25

- 괄호 없는 튜플 대입·return·yield 표현식 지원
- 한 문장의 다중 del 대상 지원
- 세미콜론 문장 목록과 한 줄 suite 지원
- 괄호형 다중 with·async with 관리자 지원
- 괄호형 from-import 목록과 후행 쉼표 지원

## 2.0.0-dev24

- ExceptionGroup과 BaseExceptionGroup 내장 형식 제공
- `except*` 하위 예외 분할·병렬 처리 의미 지원
- 미처리 하위 그룹과 처리기 신규 예외 재결합·전파
- 일반 예외의 except* 그룹 래핑
- 비트·시프트·행렬 복합 대입 연산자 지원

## 2.0.0-dev23

- 형식 매개변수 상한·기본값의 정의 범위 평가
- 비동기 리스트·집합·사전 컴프리헨션 지원
- await 요소·필터와 async for 절의 순차 실행
- 비동기 제너레이터 표현식 및 비동기 반복 프로토콜 제공
- 동기 범위에서 비동기 컴프리헨션 실행 차단

## 2.0.0-dev22

- Python 3.14 함수·클래스 형식 매개변수 문법 지원
- 형식 매개변수의 함수 호출 범위·클래스 본문 바인딩
- `__type_params__` 런타임 메타데이터 제공
- TypeVar 상한과 기본형 평가 및 `__bound__`, `__default__` 보존
- 형식 매개변수의 바깥 범위 누출 방지

## 2.0.0-dev21

- Python 3.14 `type` 별칭 문법 지원
- `TypeVar`, `TypeVarTuple`, `ParamSpec` 제네릭 별칭 매개변수 생성
- 런타임 `TypeAliasType` 및 `__type_params__` 제공
- `객체[가, 나]` 다중 첨자 튜플 문법 지원
- HBC 타입 별칭 페이로드 검증

## 2.0.0-dev20

- `from ... import *` 공개 이름 병합 지원
- 함수 매개변수·반환 주석의 정의 시점 평가
- 함수 객체 `__annotations__` 노출
- MAKE_FUNCTION 주석 메타데이터와 스택 검증 확장

## 2.0.0-dev19

- lambda 기본값·위치 전용·키워드 전용·가변 인자 바인딩 지원
- 한 문장 다중 import와 점 경로 HBC 모듈 탐색 지원
- 이름 주석의 `__annotations__` 기록
- 속성·인덱스 주석 대입 지원
- HBC `ANNOTATE` 명령 검증과 전 실행기 지원

## 2.0.0-dev18

- Python 의미에 맞는 비교 연쇄의 중간 피연산자 단일 평가와 단락 실행
- 단일 비교의 기존 공개 AST 형태 유지
- HBC 비교 연쇄 코드 검증 및 동기·비동기 실행 지원

## 2.0.0-dev17

- 리스트·튜플·집합 별표 펼치기 리터럴 지원
- 사전 `**` 펼치기와 소스 순서 기반 키 덮어쓰기 지원
- 튜플 및 범위 표현식을 사용하는 복합 `except` 지원
- f-string `!r`, `!s`, `!a`, 정적·중첩 형식 지정자 지원
- 새 HBC 컬렉션 조립 및 형식화 명령 검증

## 2.0.0-dev16

- 인자 없는 `raise`와 활성 예외 재발생 지원
- `raise ... from ...` 명시적 예외 원인 연결 지원
- 지연 평가 제너레이터 표현식 지원
- `for`·컴프리헨션의 중첩 및 별표 구조 분해 대상 지원
- 구조화 대입 대상의 HBC 검증 확장

## 2.0.0-dev15

- 제너레이터 내부 `with`, 중첩 정의, 확장 호출, 컴프리헨션 지원
- 코루틴 실행기의 컬렉션·구조 분해·예외·문맥 관리 명령 집합 확장
- 비동기 제너레이터의 `await`, `async for`, `async with` 중단·재개 지원
- 속성과 인덱스 대상 복합 대입 지원 및 HBC `DUP2` 명령 추가

## 2.0.0-dev14

- 제너레이터 내부 `try/except/else/finally`의 중단·재개 지원
- `throw()` 예외 주입 및 `yield from` 위임 전달 지원
- 제너레이터의 `return`, `break`, `continue`가 `finally`를 통과하도록 제어 흐름 보강
- 제너레이터 내부 컬렉션·슬라이스·구조 분해·f-string·비트 연산 지원
- 표준 내장 함수 `any`, `all`, `sum`, `min`, `max`, `sorted` 등 확장

## 2.0.0-dev13

- 연쇄 대입과 오른쪽 표현식 단일 평가
- 동일 객체 참조 보존

## 2.0.0-dev12 - 개발 중

- `for/while ... else` 정상 종료 의미
- `break` 시 반복문 else 건너뛰기

## 2.0.0-dev11 - 개발 중

- 변수·매개변수·함수 반환 타입 주석 파싱
- 초기값 없는 주석 선언과 주석 대입

## 2.0.0-dev10 - 개발 중

- 별표 구조 분해와 가운데 나머지 리스트 수집
- HBC `UNPACK_EX` 및 부족 값 진단

## 2.0.0-dev9 - 개발 중

- 튜플·리스트 구조 분해 대입
- 중첩 구조 분해와 개수 불일치 진단
- HBC `UNPACK` 명령 및 정적 스택 검증

## 2.0.0-dev8 - 개발 중

- HBC async generator 객체
- `__aiter__`, `__anext__`, `asend`, `aclose` 프로토콜
- `async for`를 통한 비동기 생성기 소비

## 2.0.0-dev7 - 개발 중

- 비트 OR/XOR/AND, 좌우 시프트, 단항 비트 반전
- Python 우선순위에 맞춘 연산자 파서 재배치

## 2.0.0-dev6 - 개발 중

- 클래스 키워드 패턴과 속성 캡처
- 클래스 형식 검사 및 `__match_args__` 기반 위치 패턴 기반

## 2.0.0-dev5 - 개발 중

- 라이브 클로저 환경과 `nonlocal`
- 위치 전용 함수 인자(`/`)
- `try/finally`, `except`, `with` 내부 return 전파
- `try/finally` 경계를 넘는 break/continue
- 다중 for와 절별 필터를 지원하는 중첩 컴프리헨션

## 2.0.0-dev4 - 개발 중

- 실제 awaitable HBC 코루틴과 중첩 `await`
- `async for` 비동기 반복자 프로토콜
- `async with` 비동기 컨텍스트 프로토콜
- OR·시퀀스·별표·매핑 구조 패턴
- 제너레이터 yield 표현식과 `send()`

## 2.0.0-dev3 - 개발 중

- 슬라이스, 조건식, 명명식(`:=`)
- 리터럴·캡처·와일드카드·가드 패턴 매칭
- 재개 가능한 HBC 제너레이터 프레임
- 지연 `yield`와 `yield from`

## 2.0.0-dev1 - 개발 중

- HBC v2 개발 형식
- 네이티브 `elif`, `try/except/else/finally`, `raise`
- 예외 코드 객체의 HIR 최적화와 HBC 재귀 검증

## 2.0.0-dev2 - 개발 중

- 리스트·집합·딕셔너리 컴프리헨션과 독립 범위
- 튜플·집합 리터럴
- 기본값, 키워드 전용, `*args`, `**kwargs`와 확장 호출
- 렉시컬 클로저와 람다
- 클래스 상속과 함수·클래스 데코레이터
- 컨텍스트 관리자와 예외 억제
- 선택 import, 글로벌, 삭제, assert, 복합 비교 연산자

## 1.0.1 - 2026-07-16

- `for` 루프를 `break`할 때 Hython VM 반복자 스택 정리
- HBC 제어 흐름별 정적 스택 깊이 및 언더플로 검증
- 호환/네이티브 차등 계산, 반복 실행, 대용량 자료, 재귀, 모듈 캐시,
  절단·변조 파일을 포함하는 안정성 테스트 추가

## 1.0.0 - 2026-07-16

- 발음형 한글 Python 호환 소스 변환기와 `.hy` import hook
- 실행, REPL, 양방향 변환, 패키지 API 발음 사전
- 공식 Windows Python install manager 연동과 프로젝트 런타임 고정
- 하이썬 전용 AST, Pratt 파서, HIR 및 상수 최적화
- 독립 HBC v1 컨테이너와 Hython VM
- 함수, 클래스, 조건/반복, 컬렉션, f-string, 네이티브 HBC 모듈
- HBC SHA-256 무결성, 크기 제한 및 명령어 검증
- 프로젝트 일괄 빌드와 사용자용 오류 진단
