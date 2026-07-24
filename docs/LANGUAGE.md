# 하이썬 언어 안내

하이썬은 영어 Python 철자를 의미 번역이 아닌 한글 발음으로 쓰는 언어다.

## 두 실행 모드

### Python 호환 모드

`hython run`, `hython repl`과 `.hy` import hook은 하이썬 토큰을 Python으로 바꾼다.
문자열과 주석은 보존하며 설치된 Python이 지원하는 전체 문법과 생태계를 활용한다.

### 네이티브 HBC 모드

`hython compile/build/execute`는 하이썬 AST, HIR, HBC와 Hython VM을 사용한다.
CPython AST, opcode, `.pyc` 형식과 호환되지 않는다. 현재 2.0 개발판의 주요 네이티브
지원 범위는 다음과 같다.

- Python 3.14 리터럴, 연산자, 대입, f-string과 t-string
- 조건·반복·컴프리헨션·명명식·구조 패턴 매칭
- 전체 함수 인자 종류, 클로저, 람다, 데코레이터와 generic 함수
- 예외 연결, 예외 그룹, `except*`, 컨텍스트 관리자
- 제너레이터, 코루틴, 비동기 반복·문맥·컴프리헨션과 비동기 제너레이터
- 상속, descriptor, metaclass, private-name mangling과 Python 3.14 클래스 메타데이터
- 형식 매개변수, type alias와 Python 3.14 지연 주석
- HBC 모듈, 상대 import, Python 표준 라이브러리와 설치 패키지 import

네이티브 `import`는 빌드된 HBC 모듈을 우선하며, 없으면 현재 Python 환경의 표준
라이브러리와 설치 패키지를 불러온다.
문법 수용성은 Python 3.14 대표 56개 구문군과 모든 concrete AST 노드군, 실행 의미는 CPython/HBC 차등 매트릭스와
전체 회귀 테스트로 검증한다. 독립 컴파일러의 세부 의미 호환은 계속 확대 중이며
안정판 1.0.1 배포물은 `dist`에 별도로 보존된다.

## 표준 발음

| Python | 하이썬 | Python | 하이썬 |
|---|---|---|---|
| `import` | `인폴트` | `def` | `데프` |
| `class` | `클래스` | `return` | `리턴` |
| `if` | `이프` | `else` | `엘스` |
| `for` | `포` | `while` | `와일` |
| `break` | `브레이크` | `continue` | `컨티뉴` |
| `True` | `트루` | `False` | `폴스` |
| `None` | `넌` | `print` | `프린트` |

전체 표준 철자는 `src/hython/vocabulary.py`가 기준이다.
