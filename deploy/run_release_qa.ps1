param(
    [switch]$Strict,
    [switch]$SkipGit
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Report = Join-Path $Root "deploy\last_qa_report.json"

if (-not (Test-Path $Python)) {
    throw "Virtualenv Python not found at .venv\Scripts\python.exe"
}

Push-Location $Root
try {
    & $Python manage.py check
    if ($LASTEXITCODE -ne 0) { throw "Django system check failed." }

    & $Python manage.py makemigrations --check --dry-run
    if ($LASTEXITCODE -ne 0) { throw "Unexpected model changes detected." }

    $Args = @("manage.py", "system_qa", "--json", $Report)
    if ($Strict) { $Args += "--strict" }
    if ($SkipGit) { $Args += "--skip-git" }
    & $Python @Args
    if ($LASTEXITCODE -ne 0) { throw "EverAfter full system QA failed." }

    Write-Host ""
    Write-Host "QA report: $Report" -ForegroundColor Green
} finally {
    Pop-Location
}
