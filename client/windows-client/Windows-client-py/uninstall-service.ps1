param(
    [string]$ServiceName = "BoomboxClient",
    [string]$NssmPath = "C:\Program Files\nssm\win64\nssm.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $NssmPath -PathType Leaf)) {
    throw "NSSM was not found at: $NssmPath"
}

& $NssmPath stop $ServiceName
& $NssmPath remove $ServiceName confirm

Write-Host "Removed the $ServiceName service."
Write-Host "C:\ProgramData\Boombox was left in place so its client ID and logs are preserved."
