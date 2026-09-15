$ErrorActionPreference = "Stop"
$Here = $PSScriptRoot
$Venv = Join-Path $Here ".agent-venv"
$Python = Join-Path $Venv "Scripts\python.exe"

Write-Host "EverAfter v12.3 - Local Print Agent setup"
if ($env:OS -ne "Windows_NT") {
    throw "This print agent setup is intended for Windows."
}

$PyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($PyLauncher) {
    & py -3 -m venv $Venv
} else {
    $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonCmd) { throw "Python 3 was not found. Install Python first." }
    & python -m venv $Venv
}
if (-not (Test-Path $Python)) { throw "Could not create agent virtual environment." }

& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
& $Python -m pip install -r (Join-Path $Here "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Agent dependency installation failed." }

$Config = Join-Path $Here "agent.env"
if (-not (Test-Path $Config)) {
    Copy-Item (Join-Path $Here "agent.env.example") $Config
    Write-Host "Created: $Config"
}

Write-Host ""
Write-Host "Agent environment ready."
Write-Host "1. Create a Local Print Agent token in EverAfter > Printing."
Write-Host "2. Put the server URL/token/printer in: $Config"
Write-Host "3. List printers: .\run_agent.ps1 --list-printers"
Write-Host "4. Test safely:  .\run_agent.ps1 --once --dry-run"
Write-Host "5. Start agent:  .\run_agent.ps1"
