# 하이썬 (Hython)

**Python, pronounced in Hangul.** Python의 의미를 번역하지 않고 발음을 한글로 적는
난해한 프로그래밍 언어입니다.

```hython
데프 인사(이름):
    프린트(f"안녕, {이름}!")

포 번호 인 레인지(3):
    인사(번호)
```

## 설치와 실행

```console
python -m pip install -e .
python -m pip install -e ".[exe]"
hython init
hython run examples/안녕.hy
hython module 내패키지
hython repl
hython doctor
```

Python 파일을 하이썬으로 바꾸거나 그 반대로 바꿀 수 있습니다.

```console
hython translate program.py --reverse -o program.hy
hython translate program.hy -o program.py
```

하이썬은 Python 호환 실행 모드와 독립 HBC 컴파일 모드를 함께 제공합니다.
따라서 문자열과 주석 안의 단어는 바뀌지 않습니다. Python 문법의 괄호, 연산자,
들여쓰기 규칙은 그대로 사용합니다.

같은 폴더의 `계산기.hy`는 일반 모듈처럼 `인폴트 계산기`로 불러올 수 있습니다.
패키지는 `도구/__init__.hy` 형태로 만들며 상대 import도 지원합니다.

## Python 패키지와 발음 사전

```console
hython package install requests
hython package install beautifulsoup4 --module bs4
hython package uninstall beautifulsoup4 --module bs4
hython package scan pathlib
```

설치는 현재 Python의 `pip`를 사용합니다. 그 뒤 패키지를 실행하지 않고 `.py` 파일의
AST를 정적으로 읽어 공개 이름의 발음 사전을 `~/.hython/dictionaries`에 생성합니다.
사전은 JSON이므로 자동 발음이 마음에 들지 않으면 직접 고칠 수 있습니다.
설치·갱신은 임시 파일을 완성한 뒤 기존 사전을 원자적으로 교체합니다. 제거 명령과
`hython update`는 더 이상 설치되지 않은 모듈의 사전을 삭제하므로 낡은 발음이 남지 않습니다.

## Python 런타임 동기화

```console
hython init
hython update
hython update --no-runtime
hython runtime info
hython runtime sync
hython runtime check .
```

`init`은 최초 CLI 실행 때도 네트워크 접근 없이 자동 수행됩니다. `update`는 Windows의
공식 Python install manager로 최신 `default` 런타임을 설치한 다음, 새 런타임 안에서
문법 프로필과 설치 패키지 사전을 재생성하고 이후 Hython 실행에 그 런타임을 사용합니다.
`--no-runtime`은 다운로드 없이 현재 Python과 패키지 상태만 다시 분석합니다.

## HBC 컴파일러 자동 업데이트

```console
hython compiler info
hython compiler check
hython compiler update
hython compiler rollback
hython compiler remove
hython compiler remove 2.1.0
```

`compiler update`는 공식 PyPI에서 `hython-lang` wheel과 게시된 SHA-256을 조회합니다.
wheel 전체 해시와 압축 경로를 검증하고 임시 디렉터리에서 실제 Hython import·기본 문법
compile·HBC 직렬화 smoke test가 성공한 경우에만 활성화합니다. 새 컴파일러는 설치된 코어를
덮어쓰지 않고 `~/.hython/compilers/버전`에 보관되며 다음 명령부터 자동 사용됩니다.
실패 시 현재 컴파일러는 바뀌지 않으며 `rollback`은 직전 검증 버전, 이력이 없으면 내장
부트스트랩 컴파일러로 돌아갑니다. `remove`는 활성 또는 지정 버전과 그 문법을 삭제합니다.

`info`와 `sync`는 하드코딩된 버전 번호가 아니라 현재 Python의 `keyword` 모듈을
조사합니다. 새 키워드가 발견되면 발음 후보와 함께
`~/.hython/runtimes/python-버전.json`에 기록합니다. `check`는 코드를 실행하지 않고
모든 `.hy` 파일을 현재 Python 컴파일러로 문법 검사합니다.

외부 갱신은 키워드와 라이브러리의 공개 Python 식별자에 대한 발음 계층입니다. 패키지가
자체 import hook이나 문자열 DSL로 새로운 언어 문법을 구현한 경우에는 정적 사전의
대상이 아니며, Python 자체의 새로운 문법 구조를 HBC로 낮추는 작업은 새 HBC 컴파일러
릴리스가 필요합니다. Python 호환 실행 모드는 활성 최신 Python의 문법을 즉시 사용합니다.

### 공식 Python 런타임 관리 (Windows)

```console
hython runtime list
hython runtime online 3.14
hython runtime install 3.14 --dry-run
hython runtime install 3.14
hython runtime use 3.14
```

다운로드와 검증은 Python.org의 공식 Python install manager에 위임합니다. `use`는
프로젝트에 `.hython-runtime`을 만들고 이후 실행을 지정 버전으로 전환합니다.

## 독립 HBC 컴파일러와 VM

```console
hython compile examples/컴파일.hy -o 프로그램.hbc
hython compile examples/컴파일.hy --show-hir
hython compile examples/컴파일.hy --no-optimize
hython disassemble 프로그램.hbc
hython execute 프로그램.hbc
hython exe 프로그램.hbc -o 프로그램.exe
hython exe 프로그램.hbc -o 프로그램.exe --windowed --icon app.ico
hython build . -o dist
```

Windows의 `exe` 명령은 HBC, Python 런타임과 Hython VM을 PyInstaller one-file PE에
내장합니다. 생성된 EXE는 원본 `.hbc`나 별도 Python 설치 없이 실행됩니다. 입력 HBC와
같은 폴더의 다른 `.hbc` 모듈도 디렉터리 구조를 유지해 자동 포함하며, 다른 빌드 루트는
`--module-root dist`로 지정합니다. HBC가 import하는 설치 Python 패키지도 분석해
수집합니다. EXE 기능은 `pip install "hython-lang[exe]"`로 설치할 수 있습니다.

HBC는 `HYBC` 헤더, 자체 스택 명령어, 압축 페이로드와 SHA-256 무결성 검사를
사용하며 `.pyc`나 CPython opcode가 아닙니다. 보존된 1.x 배포물은 초기 HBC를,
현재 2.0 개발판은 예외·비동기·패턴 매칭·generic·지연 주석과 Python 3.14 클래스
메타데이터와 순차 클래스 인자 조립까지 확장한 HBC v6를 사용합니다.
네이티브 컴파일 경로는 하이썬 소유 AST와 Pratt 표현식 파서를 사용하며 `ast.parse`에
의존하지 않습니다.

0.7부터 소스 프런트엔드와 HBC 사이에 독립 HIR 계층이 있습니다. 기본 최적화는 숫자,
문자열과 비교식의 안전한 상수 접기를 수행하며 명령어 위치를 유지해 분기 안정성을
보존합니다. `--show-hir`로 결과를 확인할 수 있습니다.

여러 `.hy` 파일은 `hython build`로 디렉터리 구조를 유지한 채 한 번에 컴파일할 수
있습니다. HBC의 `인폴트 모듈`은 같은 출력 폴더의 `모듈.hbc`를 직접 로드합니다.

지원 범위와 두 실행 모드의 차이는 [언어 안내](docs/LANGUAGE.md)를 참고하세요.
신뢰 경계와 HBC 검증 범위는 [보안 정책](SECURITY.md)에 설명되어 있습니다.

## 안정성 검사

```console
python -m unittest discover -s tests -v
python scripts/stability.py --cycles 10
```

안정성 검사는 호환/네이티브 차등 계산, 10만 회 반복, 반복 함수 호출, 재귀,
대용량 컬렉션, 모듈 캐시 및 HBC 절단·변조 입력을 검사합니다.

## 목표

- 설치된 Python 버전에서 문법/키워드를 자동 검사
- 더 정확한 발음 규칙과 패키지별 공식 사전
- 독립 HIR/HBC/VM 컴파일러 ([설계 문서](docs/COMPILER.md))
- Python 새 버전 문법에 대한 호환성 검사 및 사전 업데이트

자동으로 내려받은 코드나 패키지는 실행 전 출처와 해시를 검증하는 방향으로 설계합니다.
