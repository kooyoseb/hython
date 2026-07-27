# Hython Studio

Hython Studio는 C#과 WPF로 개발하는 Hython 전용 Windows IDE입니다.

Hython Studio 1.0에 포함된 기능:

- VS Code와 IntelliJ 계열을 조합한 다중 패널 UI
- 프로젝트 폴더 및 파일 탐색기
- 다중 편집기 탭, UTF-8 읽기와 저장
- 설치본, PATH, 저장소 독립 실행본 순서의 Hython 엔진 탐색
- 현재 파일 실행, HBC 컴파일, EXE 빌드 명령 연결
- Hython 분석 프로토콜 기반 한글 문법 진단과 코드 구조 표시
- `Ctrl+Space` 분석 기반 자동완성 메뉴
- 실제 HBC VM 중단점, 단계 실행, 변수 및 출력 디버거
- 프로젝트 전체 검색과 파일·폴더 생성, 이름 변경, 삭제
- PowerShell 터미널과 패키지 설치·업데이트·제거
- PyPI, GitHub MSI, Winget 기반 Hython 엔진 관리
- Python → 완전 Hython 변환과 HBC EXE 메타데이터 빌드
- 수정된 탭 표시, 모두 저장과 종료 전 미저장 파일 보호

빌드:

```console
build-studio.bat
```

출력:

```text
studio\release\HythonStudio.exe
```

Studio 전용 MSI:

```console
build-studio-installer.bat
```

출력:

```text
release\HythonStudio-1.0.0-x64.msi
```
