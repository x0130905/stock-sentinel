$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot
$Python = "$ProjectRoot\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
  throw 'The virtual environment was not found. Run scripts\setup.ps1 first.'
}
& $Python -m stock_sentinel demo
if ($LASTEXITCODE -ne 0) {
  throw "Demo generation failed with exit code $LASTEXITCODE."
}
Write-Host 'Demo data is ready. Next run: powershell -ExecutionPolicy Bypass -File .\scripts\run-frontend.ps1' -ForegroundColor Green
