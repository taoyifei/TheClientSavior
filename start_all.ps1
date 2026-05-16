Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendDir = Join-Path $root "frontend"
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython) {
    $pythonPath = $venvPython
} else {
    $pythonPath = "python"
}

$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npmCommand) {
    $npmCommand = Get-Command npm -ErrorAction Stop
}
$npmPath = $npmCommand.Source

$backendOutLog = Join-Path $root "backend_dev.out.log"
$backendErrLog = Join-Path $root "backend_dev.err.log"
$frontendOutLog = Join-Path $root "frontend_dev.out.log"
$frontendErrLog = Join-Path $root "frontend_dev.err.log"

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $FilePath $($Arguments -join ' ')"
    }
}

function Ensure-BackendDependencies {
    param(
        [string]$PythonPath,
        [string]$ProjectRoot
    )
    $checkCode = "import fastapi, uvicorn, pydantic, dotenv, openai"
    & $PythonPath -c $checkCode | Out-Null
    if ($LASTEXITCODE -eq 0) {
        return
    }

    $requirementsPath = Join-Path $ProjectRoot "backend\requirements.txt"
    Write-Host "Installing backend dependencies from backend/requirements.txt..."
    Invoke-Checked -FilePath $PythonPath -Arguments @(
        "-m",
        "pip",
        "install",
        "-r",
        $requirementsPath
    )
}

function Get-PortProcessIds {
    param([int]$Port)
    return Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
}

function Stop-SpawnChildren {
    param([int]$ParentProcessId)
    $children = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            ([string]$_.CommandLine).Contains("parent_pid=$ParentProcessId")
        }
    foreach ($child in $children) {
        Write-Host "Stopping orphan child process: PID $($child.ProcessId)"
        Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Stop-ProjectProcessOnPort {
    param(
        [int]$Port,
        [string]$ProjectRoot
    )
    $processIds = Get-PortProcessIds -Port $Port
    foreach ($processId in $processIds) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$processId" -ErrorAction SilentlyContinue
        if (-not $process) {
            Stop-SpawnChildren -ParentProcessId $processId
            continue
        }

        $commandLine = [string]$process.CommandLine
        $isProjectProcess = (
            $commandLine.Contains($ProjectRoot) -or
            $commandLine.Contains("backend.main:app") -or
            $commandLine.Contains("vite --host 0.0.0.0 --port 5173") -or
            ($Port -eq 8000 -and $commandLine.Contains("uvicorn")) -or
            ($Port -eq 5173 -and $commandLine.Contains("vite"))
        )
        if ($isProjectProcess) {
            Write-Host "Stopping old project process on port ${Port}: PID $processId"
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
            Stop-SpawnChildren -ParentProcessId $processId
        } else {
            throw "Port ${Port} is occupied by another process. PID: $processId"
        }
    }
}

function Wait-PortFree {
    param(
        [int]$Port,
        [int]$TimeoutSeconds = 20
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (-not (Get-PortProcessIds -Port $Port)) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Wait-HttpReady {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 60
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3 | Out-Null
            return $true
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    return $false
}

function Get-LanIp {
    $ip = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.AddressState -eq "Preferred" -and
            $_.IPAddress -match "^(192\.168\.|10\.|172\.(1[6-9]|2\d|3[0-1])\.)" -and
            $_.InterfaceAlias -notmatch "vEthernet|WSL|Docker|Loopback"
        } |
        Sort-Object @{
            Expression = {
                if ($_.IPAddress -like "192.168.*") {
                    0
                } elseif ($_.IPAddress -like "10.*") {
                    1
                } else {
                    2
                }
            }
        } |
        Select-Object -First 1 -ExpandProperty IPAddress
    return $ip
}

function Show-LogTail {
    param(
        [string]$Title,
        [string]$Path
    )
    Write-Host ""
    Write-Host $Title
    if (Test-Path -LiteralPath $Path) {
        Get-Content -LiteralPath $Path -Tail 80 -ErrorAction SilentlyContinue
    } else {
        Write-Host "(log file not found)"
    }
}

Set-Location $root

Ensure-BackendDependencies -PythonPath $pythonPath -ProjectRoot $root

if (-not (Test-Path -LiteralPath (Join-Path $frontendDir "node_modules"))) {
    Write-Host "First run: installing frontend dependencies with npm install..."
    Push-Location $frontendDir
    Invoke-Checked -FilePath $npmPath -Arguments @("install")
    Pop-Location
}

Stop-ProjectProcessOnPort -Port 8000 -ProjectRoot $root
Stop-ProjectProcessOnPort -Port 5173 -ProjectRoot $root
if (-not (Wait-PortFree -Port 8000)) {
    throw "Port 8000 is still busy after stopping old backend."
}
if (-not (Wait-PortFree -Port 5173)) {
    throw "Port 5173 is still busy after stopping old frontend."
}

Remove-Item $backendOutLog,$backendErrLog,$frontendOutLog,$frontendErrLog -ErrorAction SilentlyContinue

$backendProcess = Start-Process `
    -FilePath $pythonPath `
    -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000") `
    -WorkingDirectory $root `
    -WindowStyle Hidden `
    -RedirectStandardOutput $backendOutLog `
    -RedirectStandardError $backendErrLog `
    -PassThru

$frontendProcess = Start-Process `
    -FilePath $npmPath `
    -ArgumentList @("run", "dev", "--", "--host", "0.0.0.0", "--port", "5173") `
    -WorkingDirectory $frontendDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $frontendOutLog `
    -RedirectStandardError $frontendErrLog `
    -PassThru

Write-Host "Waiting for services..."
$backendReady = Wait-HttpReady -Url "http://127.0.0.1:8000/api/health" -TimeoutSeconds 60
$frontendReady = Wait-HttpReady -Url "http://127.0.0.1:5173" -TimeoutSeconds 60
if (-not $backendReady) {
    Show-LogTail -Title "Backend stderr:" -Path $backendErrLog
    Show-LogTail -Title "Backend stdout:" -Path $backendOutLog
    throw "Backend was not ready in 60 seconds. Check backend_dev.err.log."
}
if (-not $frontendReady) {
    Show-LogTail -Title "Frontend stderr:" -Path $frontendErrLog
    Show-LogTail -Title "Frontend stdout:" -Path $frontendOutLog
    throw "Frontend was not ready in 60 seconds. Check frontend_dev.err.log."
}

$lanIp = Get-LanIp
Write-Host ""
Write-Host "The Client Savior is running:"
Write-Host "Local:   http://localhost:5173"
if ($lanIp) {
    Write-Host "LAN:     http://$($lanIp):5173"
}
Write-Host "Backend: http://localhost:8000"
Write-Host "Backend log:  backend_dev.err.log"
Write-Host "Frontend log: frontend_dev.out.log"
Write-Host ""
Write-Host "Keep this window open. Press Ctrl+C to stop services."
Write-Host "If the browser still shows stale content, press Ctrl+F5 once."

try {
    while ($true) {
        if ($backendProcess.HasExited) {
            Show-LogTail -Title "Backend stderr:" -Path $backendErrLog
            throw "Backend process exited."
        }
        if ($frontendProcess.HasExited) {
            Show-LogTail -Title "Frontend stderr:" -Path $frontendErrLog
            Show-LogTail -Title "Frontend stdout:" -Path $frontendOutLog
            throw "Frontend process exited."
        }
        Start-Sleep -Seconds 2
    }
} finally {
    Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $frontendProcess.Id -Force -ErrorAction SilentlyContinue
    Stop-ProjectProcessOnPort -Port 8000 -ProjectRoot $root
    Stop-ProjectProcessOnPort -Port 5173 -ProjectRoot $root
}
