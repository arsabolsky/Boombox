$ErrorActionPreference = "Stop"

$principal = New-Object Security.Principal.WindowsPrincipal(
    [Security.Principal.WindowsIdentity]::GetCurrent()
)
$isAdministrator = $principal.IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)

if (-not $isAdministrator) {
    throw "Run this script from a PowerShell terminal opened as Administrator."
}

$goVersion = "1.27.4"
$goUrl = "https://go.dev/dl/go$goVersion.windows-amd64.msi"
$goInstaller = Join-Path $env:USERPROFILE "Downloads\go.msi"
$goInstallLog = Join-Path $env:USERPROFILE "Downloads\go-install.log"
$goExecutable = "C:\Program Files\Go\bin\go.exe"
$goBin = Split-Path -Parent $goExecutable

$nssmVersionDirectory = "nssm-2.24-101-g897c7ad"
$nssmUrl = "https://nssm.cc/ci/$nssmVersionDirectory.zip"
$nssmArchive = Join-Path $env:USERPROFILE "Downloads\nssm.zip"
$nssmInstallRoot = "C:\Program Files"
$nssmExecutable = Join-Path $nssmInstallRoot "$nssmVersionDirectory\win64\nssm.exe"

function Download-File {
    param(
        [Parameter(Mandatory)]
        [string]$Url,

        [Parameter(Mandatory)]
        [string]$Destination
    )

    Write-Host "Downloading $Url"
    & curl.exe --fail --location --output $Destination $Url

    if ($LASTEXITCODE -ne 0) {
        throw "Download failed with exit code $LASTEXITCODE`: $Url"
    }
}

if (-not (Test-Path -LiteralPath $goExecutable -PathType Leaf)) {
    Download-File -Url $goUrl -Destination $goInstaller

    Write-Host "Installing Go $goVersion..."
    $goInstallation = Start-Process msiexec.exe `
        -ArgumentList "/i `"$goInstaller`" /qn /norestart /L*v `"$goInstallLog`"" `
        -Wait `
        -PassThru

    if ($goInstallation.ExitCode -notin 0, 3010) {
        throw "Go installation failed with exit code $($goInstallation.ExitCode). See $goInstallLog"
    }
} else {
    Write-Host "Go is already installed."
}

# Ensure Go is permanently available to every user and refresh this PowerShell.
$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$machinePathEntries = $machinePath -split ";" | Where-Object { $_ }

if ($machinePathEntries -notcontains $goBin) {
    $updatedMachinePath = ($machinePathEntries + $goBin) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $updatedMachinePath, "Machine")
}

$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$env:Path = "$machinePath;$userPath"

if (-not (Test-Path -LiteralPath $nssmExecutable -PathType Leaf)) {
    Download-File -Url $nssmUrl -Destination $nssmArchive

    Write-Host "Extracting NSSM to $nssmInstallRoot..."
    & tar.exe -xf $nssmArchive -C $nssmInstallRoot

    if ($LASTEXITCODE -ne 0) {
        throw "NSSM extraction failed with exit code $LASTEXITCODE."
    }
} else {
    Write-Host "NSSM is already installed."
}

if (-not (Test-Path -LiteralPath $nssmExecutable -PathType Leaf)) {
    throw "NSSM was not found after extraction: $nssmExecutable"
}

Write-Host ""
Write-Host "Installed dependencies successfully."
& $goExecutable version
Write-Host "NSSM: $nssmExecutable"

if ($goInstallation -and $goInstallation.ExitCode -eq 3010) {
    Write-Warning "The installation succeeded, but Windows recommends restarting."
}
