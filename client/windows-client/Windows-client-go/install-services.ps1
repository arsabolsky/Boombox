param(
    [string]$ServiceName = "BoomboxClient",
    [string]$InstallDirectory = "C:\ProgramData\Boombox",
    [string]$NssmPath = "C:\Program Files\nssm-2.24-101-g897c7ad\win64\nssm.exe",
    [string]$ExecutablePath = "$PSScriptRoot\BoomboxClient.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $NssmPath -PathType Leaf)) {
    throw "NSSM was not found at: $NssmPath"
}
if (-not (Test-Path -LiteralPath $ExecutablePath -PathType Leaf)) {
    throw "The compiled client was not found at: $ExecutablePath"
}

$envExample = Join-Path $PSScriptRoot ".env.example"
$executableTarget = Join-Path $InstallDirectory "BoomboxClient.exe"
$envTarget = Join-Path $InstallDirectory ".env"
$stdoutLog = Join-Path $InstallDirectory "client.log"
$stderrLog = Join-Path $InstallDirectory "client-error.log"

New-Item -ItemType Directory -Path $InstallDirectory -Force | Out-Null
Copy-Item -LiteralPath $ExecutablePath -Destination $executableTarget -Force

if (-not (Test-Path -LiteralPath $envTarget)) {
    Copy-Item -LiteralPath $envExample -Destination $envTarget
    Write-Warning "Created $envTarget. Edit API_BASE_URL before starting the service."
}

& icacls.exe $InstallDirectory /inheritance:r `
    /grant:r "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" | Out-Null

& $NssmPath install $ServiceName $executableTarget
& $NssmPath set $ServiceName AppDirectory $InstallDirectory
& $NssmPath set $ServiceName ObjectName LocalSystem
& $NssmPath set $ServiceName AppStdout $stdoutLog
& $NssmPath set $ServiceName AppStderr $stderrLog
& $NssmPath set $ServiceName AppRotateFiles 1
& $NssmPath set $ServiceName AppRotateOnline 1
& $NssmPath set $ServiceName AppRotateBytes 10485760
& $NssmPath set $ServiceName Start SERVICE_DEMAND_START

Write-Host "Installed $ServiceName but did not start it."
Write-Host "Edit $envTarget, then run:"
Write-Host "  & `"$NssmPath`" start $ServiceName"
