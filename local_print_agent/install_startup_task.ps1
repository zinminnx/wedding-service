$ErrorActionPreference = "Stop"
$Here = $PSScriptRoot
$RunAgent = Join-Path $Here "run_agent.ps1"
$TaskName = "EverAfter Local Print Agent"

if (-not (Test-Path (Join-Path $Here ".agent-venv\Scripts\python.exe"))) {
    throw "Agent environment not found. Run .\install_agent.ps1 first."
}
if (-not (Test-Path (Join-Path $Here "agent.env"))) {
    throw "agent.env not found. Configure the agent token first."
}

$UserId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$RunAgent`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $UserId
$Principal = New-ScheduledTaskPrincipal -UserId $UserId -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Description "EverAfter trusted wedding print queue agent" -Force | Out-Null
Write-Host "Startup task installed: $TaskName"
Write-Host "It will start when $UserId logs in."
