Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython) {
    $pythonPath = $venvPython
} else {
    $pythonPath = "python"
}

$checkCode = "import fastapi, uvicorn, pydantic, dotenv, openai"
& $pythonPath -c $checkCode | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing backend dependencies from backend/requirements.txt..."
    & $pythonPath -m pip install -r (Join-Path $root "backend\requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Backend dependency installation failed."
    }
}

& $pythonPath -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
