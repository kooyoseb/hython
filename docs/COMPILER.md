# 하이썬 독립 컴파일러 방향

하이썬 호환 실행기는 생태계 호환을 위해 Python 변환 백엔드를 제공한다. 네이티브
컴파일러는 0.8부터 하이썬 전용 AST와 Pratt 파서를 사용한다.
2.0 개발판은 Python AST/바이트코드와 분리된 다음 구조를 사용한다.

```text
.hy 소스 → 하이썬 파서 → HIR → 최적화 IR → HBC 바이트코드 → Hython VM
                                  └→ 선택적 네이티브 백엔드
```

## 설계 원칙

- HIR(Hython Intermediate Representation)은 HBC로 낮추기 전의 독립 스택 IR이며 Python AST를 저장하지 않는다.
- HBC는 CPython opcode 및 `.pyc` 형식과 호환되지 않는 독자 컨테이너를 쓴다.
- Python 표준 라이브러리와 설치 패키지는 VM의 native import bridge를 통해 불러오며 HBC 모듈을 우선한다.
- HBC v6는 명령어별 소스 줄 정보와 순차 클래스 인자 조립 명령을 저장해 독립 VM 진단, traceback note, 정확한 인자 평가 순서에 사용한다.
- 파일 서명과 무결성 검사는 제공하지만, 암호화를 디컴파일 불가능의 근거로 삼지 않는다.

어떤 실행 파일도 충분한 시간과 권한이 있으면 분석될 수 있다. 목표는 기존 Python
디컴파일 도구와 직접 호환되지 않게 하고 원본 구조 복원 비용을 높이는 것이지, 불가능을 약속하는
것이 아니다.
