Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $root "frontend")

if (-not (Test-Path -LiteralPath "node_modules")) {
    npm install
}

npm run dev -- --host 0.0.0.0 --port 5173
