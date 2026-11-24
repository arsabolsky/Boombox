# Windows Client

Runs on every monitored Windows host (Mateo). The client is in
[`Windows-client-go/`](Windows-client-go/README.md): a Go program, built as
`BoomboxClient.exe` and installed as a Windows service with NSSM. It registers, polls for
queries (`poll/queries`), sends results (`results`), and polls for approved fix scripts
(`poll/remediations`), which it runs as PowerShell.

It needs osquery installed (https://osquery.io/downloads). Build and install steps are in
[`Windows-client-go/README.md`](Windows-client-go/README.md).
