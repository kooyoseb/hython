param(
    [string]$Version = "",
    [string]$InstallerUrl = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

if (-not $Version) {
    $Version = (& py -3.14 -c "import sys; sys.path.insert(0, r'$Root\src'); import hython; print(hython.__version__)").Trim()
}
if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    throw "Winget에는 정식 버전만 등록할 수 있습니다: $Version"
}

$MsiPath = Join-Path $Root "release\Hython-$Version-x64.msi"
if (-not (Test-Path -LiteralPath $MsiPath)) {
    throw "MSI가 없습니다: $MsiPath`nbuild-hython.bat과 build-installer.bat을 먼저 실행하세요."
}
if (-not $InstallerUrl) {
    $InstallerUrl = "https://github.com/kooyoseb/hython/releases/download/v$Version/Hython-$Version-x64.msi"
}

$Sha256 = [System.Security.Cryptography.SHA256]::Create()
$Stream = [System.IO.File]::OpenRead($MsiPath)
try {
    $Hash = ([System.BitConverter]::ToString($Sha256.ComputeHash($Stream))).Replace("-", "")
}
finally {
    $Stream.Dispose()
    $Sha256.Dispose()
}
$WindowsInstaller = New-Object -ComObject WindowsInstaller.Installer
$Database = $WindowsInstaller.OpenDatabase($MsiPath, 0)
$View = $Database.OpenView("SELECT ``Value`` FROM ``Property`` WHERE ``Property``='ProductCode'")
$View.Execute()
$Record = $View.Fetch()
$ProductCode = $Record.StringData(1)
$View.Close()

$ManifestDir = Join-Path $Root "winget\manifests\k\kooyoseb\Hython\$Version"
New-Item -ItemType Directory -Path $ManifestDir -Force | Out-Null

@"
# Created by Hython's Winget preparation script.
# yaml-language-server: `$schema=https://aka.ms/winget-manifest.version.1.10.0.schema.json
PackageIdentifier: kooyoseb.Hython
PackageVersion: $Version
DefaultLocale: en-US
ManifestType: version
ManifestVersion: 1.10.0
"@ | Set-Content -LiteralPath (Join-Path $ManifestDir "kooyoseb.Hython.yaml") -Encoding utf8

@"
# Created by Hython's Winget preparation script.
# yaml-language-server: `$schema=https://aka.ms/winget-manifest.installer.1.10.0.schema.json
PackageIdentifier: kooyoseb.Hython
PackageVersion: $Version
InstallerType: wix
Scope: machine
InstallModes:
- interactive
- silent
- silentWithProgress
UpgradeBehavior: install
ReleaseDate: $(Get-Date -Format yyyy-MM-dd)
Installers:
- Architecture: x64
  InstallerUrl: $InstallerUrl
  InstallerSha256: $Hash
  ProductCode: '$ProductCode'
  AppsAndFeaturesEntries:
  - DisplayName: Hython
    Publisher: Kooyoseb
    DisplayVersion: $Version
    ProductCode: '$ProductCode'
ManifestType: installer
ManifestVersion: 1.10.0
"@ | Set-Content -LiteralPath (Join-Path $ManifestDir "kooyoseb.Hython.installer.yaml") -Encoding utf8

@"
# Created by Hython's Winget preparation script.
# yaml-language-server: `$schema=https://aka.ms/winget-manifest.defaultLocale.1.10.0.schema.json
PackageIdentifier: kooyoseb.Hython
PackageVersion: $Version
PackageLocale: en-US
Publisher: Kooyoseb
PublisherUrl: https://github.com/kooyoseb
PublisherSupportUrl: https://github.com/kooyoseb/hython/issues
Author: Kooyoseb
PackageName: Hython
PackageUrl: https://github.com/kooyoseb/hython
License: MIT
LicenseUrl: https://github.com/kooyoseb/hython/blob/main/LICENSE
Copyright: Copyright (c) 2026 Kooyoseb and Hython contributors
ShortDescription: Python, pronounced in Hangul.
Description: Hython is a Korean-pronounced esoteric programming language with Python-compatible syntax, package support, an HBC compiler, and native Windows distribution.
Moniker: hython
Tags:
- compiler
- esoteric-language
- korean
- programming-language
- python
ReleaseNotesUrl: https://github.com/kooyoseb/hython/releases/tag/v$Version
ManifestType: defaultLocale
ManifestVersion: 1.10.0
"@ | Set-Content -LiteralPath (Join-Path $ManifestDir "kooyoseb.Hython.locale.en-US.yaml") -Encoding utf8

$OldKoreanLocale = Join-Path $ManifestDir "kooyoseb.Hython.locale.ko-KR.yaml"
if (Test-Path -LiteralPath $OldKoreanLocale) {
    Remove-Item -LiteralPath $OldKoreanLocale -Force
}

Write-Host "Manifest directory: $ManifestDir"
Write-Host "Installer URL: $InstallerUrl"
Write-Host "SHA-256: $Hash"
Write-Host "ProductCode: $ProductCode"
Write-Host ""
Write-Host "GitHub Release에 MSI를 올린 뒤 다음 명령으로 검사하세요:"
Write-Host "  winget validate `"$ManifestDir`""
