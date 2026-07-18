$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot
$Python = "$ProjectRoot\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) { throw '请先运行 scripts\setup.ps1。' }
& $Python -m stock_sentinel demo
Write-Host '演示分析完成。现在运行 scripts\run-frontend.ps1 查看页面。' -ForegroundColor Green
