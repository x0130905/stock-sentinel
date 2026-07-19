$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath "$ProjectRoot\frontend"

if (Get-Command pnpm -ErrorAction SilentlyContinue) {
  & pnpm dev --host 0.0.0.0
}
elseif (Get-Command npx -ErrorAction SilentlyContinue) {
  & npx --yes pnpm@10.15.1 dev --host 0.0.0.0
}
elseif (Get-Command corepack -ErrorAction SilentlyContinue) {
  & corepack pnpm dev --host 0.0.0.0
}
else {
  throw 'pnpm, npx, and corepack were not found. Reinstall Node.js with npm included.'
}
if ($LASTEXITCODE -ne 0) {
  throw "Starting the frontend failed with exit code $LASTEXITCODE."
}
