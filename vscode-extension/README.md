# Hython Development

VS Code에서 Hython 편집기의 핵심 언어 기능을 사용할 수 있게 하는 공식 확장입니다.

요구 사항: Hython 2.0.4 이상과 VS Code 1.95 이상

## 기능

- `.hy` 파일 인식, 공식 Hython 파일 아이콘과 문법 강조
- Hython 엔진 기반 한글 문법 오류 표시
- 설치 패키지 문법까지 반영하는 자동완성
- 함수, 비동기 함수와 클래스 코드 구조
- 정의로 이동, 모든 참조 찾기, 문서 하이라이트와 이름 변경
- 엔진 정보가 표시되는 Hython 호버
- 함수·클래스·조건문·반복문·예외 처리 스니펫
- 현재 파일 실행
- 독립 HBC 컴파일
- HBC 기반 Windows EXE 빌드
- F5 HBC VM 디버깅
- 중단점, 계속, 한 단계 실행과 지역 변수 보기
- 전용 Hython 터미널과 엔진 상태 표시
- 새 프로젝트 생성과 `.vscode` 실행·디버그 설정 자동 구성
- VS Code에서 패키지 설치와 엔진·문법 업데이트
- PATH, 프로젝트의 `release\hython.exe`, 사용자 지정 엔진 경로 탐색

언어 분석은 확장 안에 별도의 문법 복사본을 두지 않고 현재 Hython 엔진의
`ide analyze` 프로토콜을 사용합니다. 따라서 Hython 업데이트와 패키지 사전
변경 사항이 자동완성과 진단에 반영됩니다.

## 사용

1. Hython을 설치합니다.
2. VS Code에서 `.hy` 파일을 엽니다.
3. 우측 상단의 실행 또는 HBC 버튼을 누릅니다.
4. 엔진을 찾지 못하면 명령 팔레트에서 `Hython: 엔진 경로 선택`을 실행합니다.

## 디버깅

`.hy` 파일을 연 뒤 `F5`를 누르거나 우측 상단의 디버그 버튼을 누릅니다.
편집기 여백을 클릭해 중단점을 설정할 수 있으며, VS Code의 실행 및 디버그
화면에서 현재 줄과 지역 변수를 확인할 수 있습니다.

## 설정

- `hython.executablePath`: `hython.exe` 경로
- `hython.analysis.enabled`: 실시간 분석 사용 여부
- `hython.analysis.delay`: 입력 후 분석 지연 시간
- `hython.run.saveBeforeRun`: 실행 전 자동 저장

## 개발 및 패키징

```console
npm install
npm run check
npm run test:integration
npm run package
```
