# Boombox Windows Client (Go + NSSM)

This is the Go version of the polling client. 

It implements the current Boombox client API:

1. If `client-id.txt` does not exist, register with `POST /api/v1/clients`.
2. Save the server-issued `client_id` and send it as `X-Client-Id`.
3. Poll `GET /api/v1/poll/queries` and run the returned SQL through osquery.
4. Send rows or string errors to `POST /api/v1/results`.
5. Separately poll `GET /api/v1/poll/remediations`.
6. Run each returned remediation as a PowerShell script.
7. Use configured polling intervals and retry HTTP failures with backoff.

The current API does not provide an endpoint for remediation results. The
client writes each remediation exit code and output to its own log instead.


## Build

From an Administrator PowerShell terminal, Go and NSSM can be installed with:

```powershell
.\install-dependencies.ps1
```

Then build the client with:

```powershell
go build -trimpath -ldflags="-s -w" -o BoomboxClient.exe .
```

Only `BoomboxClient.exe` and `.env` are needed on the target VM. osquery must
also be installed there.

## Install with NSSM

From an Administrator PowerShell terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
Unblock-File .\install-service.ps1
.\install-service.ps1
```
If using Command Prompt:
```cmd
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\install-service.ps1"
```

The installer copies the executable and configuration to
`C:\ProgramData\Boombox`, restricts the directory to LocalSystem and local
administrators, configures manual startup and rotating logs, and leaves the
service stopped so `.env` can be edited first.

Start it after configuration:

```powershell
& "C:\Program Files\nssm-2.24-101-g897c7ad\win64\nssm.exe" start BoomboxClient
```

Logs are written to:

```text
C:\ProgramData\Boombox\client.log
C:\ProgramData\Boombox\client-error.log
```
