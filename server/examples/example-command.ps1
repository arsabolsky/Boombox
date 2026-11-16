# Step 1: say where we are running
Write-Output "Boombox example command on $env:COMPUTERNAME as $env:USERNAME"

# Step 2: show the current time
Get-Date

# Step 3: write a file, so you can check the script really ran
"Boombox example ran at $(Get-Date)" | Out-File -FilePath "$env:TEMP\boombox-example.txt"
Write-Output "Wrote $env:TEMP\boombox-example.txt"

Write-Output 'Boombox remediation finished'
