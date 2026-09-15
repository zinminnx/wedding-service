$ErrorActionPreference = "Stop"
$TaskName = "EverAfter Local Print Agent"
$Existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($Existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed startup task: $TaskName"
} else {
    Write-Host "Startup task was not installed."
}
