$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath "$ProjectRoot\frontend"
pnpm dev --host 0.0.0.0
