param(
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$streamlitExe = Join-Path $projectRoot ".venv\Scripts\streamlit.exe"

if (-not (Test-Path -LiteralPath $streamlitExe)) {
    $streamlitExe = "streamlit"
}

$ips = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.InterfaceAlias -notlike "*vEthernet*" -and
        $_.PrefixOrigin -ne "WellKnown"
    } |
    Select-Object -ExpandProperty IPAddress

Write-Host "LAN URLs:" -ForegroundColor Green
foreach ($ip in $ips) {
    Write-Host "http://$ip`:$Port"
}

Write-Host ""
Write-Host "If other devices cannot open it, allow Python/Streamlit through Windows Firewall."
Write-Host ""

Push-Location $projectRoot
try {
    & $streamlitExe run app.py --server.address 0.0.0.0 --server.port $Port
} finally {
    Pop-Location
}
