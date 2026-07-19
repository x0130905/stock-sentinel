$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw 'Python was not found. Install Python 3.11+ and select Add Python to PATH.'
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  throw 'Node.js was not found. Install Node.js 20 or newer.'
}
function Assert-CommandSucceeded {
  param([string]$Step)
  if ($LASTEXITCODE -ne 0) {
    throw "$Step failed with exit code $LASTEXITCODE."
  }
}

function Invoke-ProjectPnpm {
  param([string[]]$PnpmArguments)
  if (Get-Command pnpm -ErrorAction SilentlyContinue) {
    & pnpm @PnpmArguments
  }
  elseif (Get-Command npx -ErrorAction SilentlyContinue) {
    & npx --yes pnpm@10.15.1 @PnpmArguments
  }
  elseif (Get-Command corepack -ErrorAction SilentlyContinue) {
    & corepack pnpm @PnpmArguments
  }
  else {
    throw 'pnpm, npx, and corepack were not found. Reinstall Node.js with npm included.'
  }
  Assert-CommandSucceeded 'Running pnpm'
}

python -m venv .venv
Assert-CommandSucceeded 'Creating the Python virtual environment'
& "$ProjectRoot\.venv\Scripts\python.exe" -m pip install --upgrade pip
Assert-CommandSucceeded 'Upgrading pip'
& "$ProjectRoot\.venv\Scripts\python.exe" -m pip install -e '.[dev,yfinance,intraday]'
Assert-CommandSucceeded 'Installing Python dependencies'
Set-Location -LiteralPath "$ProjectRoot\frontend"
Invoke-ProjectPnpm -PnpmArguments @('install', '--frozen-lockfile')
Write-Host 'Setup completed. Next run: powershell -ExecutionPolicy Bypass -File .\scripts\run-demo.ps1' -ForegroundColor Green
