param(
    [string]$ServiceName = "BoomboxClient",
    [string]$InstallDirectory = "C:\ProgramData\Boombox",
    [string]$NssmPath = "C:\Program Files\nssm\win64\nssm.exe",
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $NssmPath -PathType Leaf)) {
    throw "NSSM was not found at: $NssmPath"
}

if (-not $PythonPath) {
    $pythonCommand = Get-Command python.exe -ErrorAction Stop
    $PythonPath = $pythonCommand.Source
}

if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    throw "Python was not found at: $PythonPath"
}

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$agentSource = Join-Path $scriptDirectory "agent.py"
$envExample = Join-Path $scriptDirectory ".env.example"
$agentTarget = Join-Path $InstallDirectory "agent.py"
$envTarget = Join-Path $InstallDirectory ".env"
$stdoutLog = Join-Path $InstallDirectory "client.log"
$stderrLog = Join-Path $InstallDirectory "client-error.log"

New-Item -ItemType Directory -Path $InstallDirectory -Force | Out-Null
Copy-Item -LiteralPath $agentSource -Destination $agentTarget -Force

if (-not (Test-Path -LiteralPath $envTarget)) {
    Copy-Item -LiteralPath $envExample -Destination $envTarget
    Write-Warning "Created $envTarget. Edit API_BASE_URL before starting the service."
}

# Limit access to LocalSystem and the local Administrators group. The SID form
# works even when Windows is using a language other than English.
& icacls.exe $InstallDirectory /inheritance:r `
    /grant:r "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" | Out-Null

& $NssmPath install $ServiceName $PythonPath
& $NssmPath set $ServiceName AppParameters "-u `"$agentTarget`""
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
