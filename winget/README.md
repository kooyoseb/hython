# Hython Winget 등록

패키지 식별자는 `kooyoseb.Hython`입니다. 기존 Winget 게시자 경로가 소문자
`kooyoseb`으로 등록되어 있으므로 식별자와 폴더의 대소문자를 동일하게 유지합니다.

## 최초 등록 순서

1. `build-hython.bat`으로 정식 버전의 `hython.exe`를 빌드합니다.
2. `build-installer.bat`으로 같은 버전의 MSI를 빌드합니다.
3. GitHub에 `v버전` 릴리스를 만들고 MSI를 릴리스 자산으로 올립니다.
4. `prepare-winget.bat`을 실행해 SHA-256과 MSI ProductCode가 들어간 매니페스트를 생성합니다.
5. `winget validate winget\manifests\k\Kooyoseb\Hython\버전`으로 검사합니다.
6. `microsoft/winget-pkgs`를 포크하고 생성된 매니페스트 폴더를 같은 경로에 복사한 뒤 Pull Request를 보냅니다.

GitHub 릴리스 파일은 제출 뒤 교체하지 않습니다. 파일이 바뀌면 SHA-256이 달라져 Winget 설치가 실패하므로 새 버전을 발행해야 합니다.

## 다음 버전

새 MSI와 GitHub Release를 만든 뒤 아래처럼 다시 생성합니다.

```console
prepare-winget.bat -Version 2.0.1
```

공식 도구를 사용할 경우 `wingetcreate update kooyoseb.Hython -u 새_MSI_URL`로 업데이트 매니페스트를 만들 수 있습니다.
