$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

$form = New-Object System.Windows.Forms.Form
$form.Text = "Hython PyPI 배포"
$form.ClientSize = New-Object System.Drawing.Size(520, 145)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.TopMost = $true

$label = New-Object System.Windows.Forms.Label
$label.Text = "PyPI API 토큰을 입력하세요."
$label.SetBounds(20, 18, 480, 24)

$tokenBox = New-Object System.Windows.Forms.TextBox
$tokenBox.SetBounds(20, 48, 480, 26)
$tokenBox.UseSystemPasswordChar = $true

$okButton = New-Object System.Windows.Forms.Button
$okButton.Text = "배포"
$okButton.SetBounds(342, 92, 76, 32)
$okButton.DialogResult = [System.Windows.Forms.DialogResult]::OK

$cancelButton = New-Object System.Windows.Forms.Button
$cancelButton.Text = "취소"
$cancelButton.SetBounds(424, 92, 76, 32)
$cancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel

$form.Controls.AddRange(@($label, $tokenBox, $okButton, $cancelButton))
$form.AcceptButton = $okButton
$form.CancelButton = $cancelButton
$form.Add_Shown({ $tokenBox.Focus() })

if ($form.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
    exit 1
}
if (-not $tokenBox.Text.StartsWith("pypi-")) {
    [System.Windows.Forms.MessageBox]::Show(
        "올바른 PyPI API 토큰을 입력하세요.",
        "Hython PyPI 배포",
        "OK",
        "Error"
    ) | Out-Null
    exit 1
}

$env:TWINE_PASSWORD = $tokenBox.Text
$tokenBox.Clear()

try {
    & "$PSScriptRoot\publish-pypi.bat" pypi
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "PyPI 배포가 종료 코드 $exitCode(으)로 실패했습니다."
    }
    Write-Host ""
    Write-Host "[완료] PyPI 배포 성공" -ForegroundColor Green
    [System.Windows.Forms.MessageBox]::Show(
        "Hython 2.0.5 PyPI 배포가 완료되었습니다.",
        "Hython PyPI 배포",
        "OK",
        "Information"
    ) | Out-Null
}
finally {
    Remove-Item Env:TWINE_PASSWORD -ErrorAction SilentlyContinue
}
