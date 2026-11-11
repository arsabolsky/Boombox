INSERT INTO endpoints (
    hostname,
    os,
    last_seen
)
VALUES (
    'DESKTOP-01',
    'Windows 11',
    NOW()
);

INSERT INTO events (
    endpoint_id,
    event_type,
    raw_data
)
VALUES (
    1,
    'process',
    '{
        "name": "powershell.exe",
        "pid": 5124,
        "parent": 2200,
        "cmdline": "powershell.exe -EncodedCommand TEST"
    }'::jsonb
);

INSERT INTO remediations (
    event_id,
    title,
    summary,
    proposed_script,
    severity
)
VALUES (
    1,
    'Suspicious PowerShell Execution',
    'An encoded PowerShell command was detected on the endpoint.',
    'Write-Output "Sample remediation only"',
    'high'
);
