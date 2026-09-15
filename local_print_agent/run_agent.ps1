$ErrorActionPreference = "Stop"
$Here = $PSScriptRoot
$Python = Join-Path $Here ".agent-venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Agent virtual environment not found. Run .\install_agent.ps1 first."
}
& $Python (Join-Path $Here "agent.py") @args
exit $LASTEXITCODE
