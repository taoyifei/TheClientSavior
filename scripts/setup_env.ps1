param(
    [switch]$Recreate,
    [string]$Python
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Get-PythonVersion {
    param([string]$PythonExe)
    try {
        $versionText = & $PythonExe --version 2>&1
        if ($versionText -match "Python\s+(\d+)\.(\d+)\.(\d+)") {
            return [PSCustomObject]@{
                Exe = $PythonExe
                Major = [int]$Matches[1]
                Minor = [int]$Matches[2]
                Patch = [int]$Matches[3]
                Text = $versionText.ToString()
            }
        }
    } catch {
        return $null
    }
    return $null
}

function Add-PythonCandidate {
    param(
        [System.Collections.Generic.List[string]]$Candidates,
        [string]$PythonExe
    )
    if ([string]::IsNullOrWhiteSpace($PythonExe)) {
        return
    }
    try {
        $resolved = (Resolve-Path -LiteralPath $PythonExe -ErrorAction Stop).Path
    } catch {
        $command = Get-Command $PythonExe -ErrorAction SilentlyContinue
        if (-not $command) {
            return
        }
        $resolved = $command.Source
    }
    if (-not $Candidates.Contains($resolved)) {
        $Candidates.Add($resolved) | Out-Null
    }
}

function Find-Python {
    param([string]$RequestedPython)

    $candidates = [System.Collections.Generic.List[string]]::new()
    Add-PythonCandidate -Candidates $candidates -PythonExe $RequestedPython

    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        foreach ($version in @("3.11", "3.12", "3.10")) {
            try {
                $exe = & py "-$version" -c "import sys; print(sys.executable)" 2>$null
                Add-PythonCandidate -Candidates $candidates -PythonExe $exe
            } catch {
                continue
            }
        }
    }

    foreach ($name in @("python3.11", "python3.12", "python3.10", "python")) {
        Add-PythonCandidate -Candidates $candidates -PythonExe $name
    }

    $conda = Get-Command conda -ErrorAction SilentlyContinue
    if ($conda) {
        try {
            $condaBase = (& conda info --base 2>$null).Trim()
            if ($condaBase) {
                $envRoot = Join-Path $condaBase "envs"
                if (Test-Path -LiteralPath $envRoot) {
                    Get-ChildItem -Path $envRoot -Directory | ForEach-Object {
                        Add-PythonCandidate `
                            -Candidates $candidates `
                            -PythonExe (Join-Path $_.FullName "python.exe")
                    }
                }
                Add-PythonCandidate `
                    -Candidates $candidates `
                    -PythonExe (Join-Path $condaBase "python.exe")
            }
        } catch {
            Write-Host "Skip conda scan: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }

    $versionInfos = @()
    foreach ($candidate in $candidates) {
        $info = Get-PythonVersion -PythonExe $candidate
        if ($info -and $info.Major -eq 3) {
            $versionInfos += $info
        }
    }

    foreach ($minor in @(11, 12, 10)) {
        $match = $versionInfos |
            Where-Object { $_.Minor -eq $minor } |
            Select-Object -First 1
        if ($match) {
            return $match
        }
    }

    if ($versionInfos.Count -gt 0) {
        return $versionInfos[0]
    }

    throw "No usable Python 3 found. Install Python 3.11 or pass -Python path."
}

function Remove-VenvSafely {
    param(
        [string]$ProjectRoot,
        [string]$VenvDir
    )
    if (-not (Test-Path -LiteralPath $VenvDir)) {
        return
    }

    $resolvedRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
    $resolvedVenv = (Resolve-Path -LiteralPath $VenvDir).Path
    if (-not $resolvedVenv.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refuse to delete venv outside project: $resolvedVenv"
    }
    if ((Split-Path -Leaf $resolvedVenv) -ne ".venv") {
        throw "Refuse to delete non-.venv directory: $resolvedVenv"
    }

    Remove-Item -LiteralPath $resolvedVenv -Recurse -Force
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDir "..")).Path
$venvDir = Join-Path $projectRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

Set-Location $projectRoot

Write-Step "Select Python"
$pythonInfo = Find-Python -RequestedPython $Python
Write-Host "Using: $($pythonInfo.Text) -> $($pythonInfo.Exe)"
if ($pythonInfo.Minor -gt 12) {
    Write-Host "Warning: Python is newer than recommended. Prefer 3.11 or 3.12 for demo stability." -ForegroundColor Yellow
}

if ($Recreate) {
    Write-Step "Recreate .venv"
    Remove-VenvSafely -ProjectRoot $projectRoot -VenvDir $venvDir
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Step "Create virtual environment"
    & $pythonInfo.Exe -m venv $venvDir
} else {
    Write-Step "Reuse existing virtual environment"
    & $venvPython --version
}

Write-Step "Install dependencies"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $projectRoot "requirements.txt")

$envFile = Join-Path $projectRoot ".env"
$envExample = Join-Path $projectRoot ".env.example"
if (-not (Test-Path -LiteralPath $envFile)) {
    Write-Step "Create .env"
    Copy-Item -LiteralPath $envExample -Destination $envFile
    Write-Host "Created .env. Fill DASHSCOPE_API_KEY before live LLM demo."
} else {
    Write-Step "Check .env"
    Write-Host ".env exists. Keeping it unchanged."
}

Write-Step "Run smoke test"
& $venvPython (Join-Path $projectRoot "scripts\smoke_test.py")

Write-Step "Done"
Write-Host "Start app with:" -ForegroundColor Green
Write-Host ".\.venv\Scripts\streamlit.exe run app.py" -ForegroundColor Green
