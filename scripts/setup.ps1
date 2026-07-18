$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw '没有找到 Python。请先安装 Python 3.11 或更高版本，并勾选 Add Python to PATH。'
}
if (-not (Get-Command corepack -ErrorAction SilentlyContinue)) {
  throw '没有找到 Node.js/Corepack。请先安装 Node.js 20 或更高版本。'
}

python -m venv .venv
& "$ProjectRoot\.venv\Scripts\python.exe" -m pip install --upgrade pip
& "$ProjectRoot\.venv\Scripts\python.exe" -m pip install -e '.[dev,yfinance]'
corepack enable
Set-Location -LiteralPath "$ProjectRoot\frontend"
pnpm install --frozen-lockfile
Write-Host '安装完成。下一步运行 scripts\run-demo.ps1。' -ForegroundColor Green
