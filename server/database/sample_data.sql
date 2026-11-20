
-- ============================================
-- BOOMBOX SAMPLE DATA
-- ============================================

-- 1. SAMPLE CLIENTS

INSERT INTO clients (
    client_id,
    hostname,
    os,
    os_version,
    agent_version,
    system_information,
    last_seen_at,
    last_poll_at,
    status
)
VALUES
(
    '11111111-1111-4111-8111-111111111111',
    'DESKTOP-01',
    'Windows',
    '11',
    '1.0.0',
    '{"architecture": "x64", "processor": "Intel"}',
    NOW(),
    NOW(),
    'active'
),
(
    '22222222-2222-4222-8222-222222222222',
    'LAPTOP-02',
    'Windows',
    '11',
    '1.0.0',
    '{"architecture": "x64", "processor": "AMD"}',
    NOW(),
    NOW(),
    'active'
);


-- 2. SAMPLE SECURITY EVENT

WITH inserted_event AS (
    INSERT INTO events (
        client_id,
        event_type,
        raw_data
    )
    VALUES (
        '11111111-1111-4111-8111-111111111111',
        'process',
        '{
            "name": "powershell.exe",
            "pid": 5124,
            "parent": 2200,
            "cmdline": "powershell.exe -EncodedCommand TEST"
        }'::jsonb
    )
    RETURNING id, client_id
)

-- 3. SAMPLE REMEDIATION

INSERT INTO remediations (
    client_id,
    event_id,
    title,
    summary,
    proposed_script,
    severity
)
SELECT
    client_id,
    id,
    'Suspicious PowerShell Execution',
    'An encoded PowerShell command was detected on the endpoint.',
    'Write-Output "Sample remediation only"',
    'high'
FROM inserted_event;


-- 4. SECOND SAMPLE EVENT

INSERT INTO events (
    client_id,
    event_type,
    raw_data
)
VALUES (
    '22222222-2222-4222-8222-222222222222',
    'process',
    '{
        "name": "cmd.exe",
        "pid": 3100,
        "parent": 1500,
        "cmdline": "cmd.exe /c whoami"
    }'::jsonb
);


-- 5. SAMPLE CLIENT QUERIES

INSERT INTO client_queries (
    client_id,
    query_name,
    query_configuration,
    enabled
)
VALUES
(
    '11111111-1111-4111-8111-111111111111',
    'suspicious_processes',
    '{
        "description": "Monitor suspicious PowerShell processes",
        "interval_seconds": 60,
        "query": "SELECT name, pid, parent FROM processes WHERE name = ''powershell.exe'';"
    }'::jsonb,
    TRUE
),
(
    '22222222-2222-4222-8222-222222222222',
    'process_monitoring',
    '{
        "description": "Monitor running command-line processes",
        "interval_seconds": 120,
        "query": "SELECT name, pid, parent FROM processes;"
    }'::jsonb,
    TRUE
);


-- ============================================
-- TEST DATA FOR CLIENT DEVELOPERS
-- ============================================
-- A Linux client, plus one APPROVED fix script per OS, so the clients can test
-- "get an approved script, run it, report back" without the AI or the dashboard.
-- The scripts are harmless: they print some info and write one file to a temp folder.
--
--   Linux client:   X-Client-Id: 33333333-3333-4333-8333-333333333333
--   Windows client: X-Client-Id: 22222222-2222-4222-8222-222222222222

-- 6. SAMPLE LINUX CLIENT

INSERT INTO clients (
    client_id,
    hostname,
    os,
    os_version,
    agent_version,
    last_seen_at,
    status
)
VALUES (
    '33333333-3333-4333-8333-333333333333',
    'ubuntu-01',
    'linux',
    'Ubuntu 24.04',
    '1.0.0',
    NOW(),
    'active'
);


-- 7. APPROVED TEST SCRIPT FOR THE LINUX CLIENT

WITH test_event AS (
    INSERT INTO events (client_id, event_type, raw_data)
    VALUES (
        '33333333-3333-4333-8333-333333333333',
        'test',
        '{"note": "test data for client developers"}'::jsonb
    )
    RETURNING id, client_id
)
INSERT INTO remediations (
    client_id, event_id, title, summary, proposed_script, severity,
    status, reviewed_at, reviewed_by
)
SELECT
    client_id,
    id,
    'Test script for client developers',
    'Harmless test: prints some info and writes /tmp/boombox-test.txt.',
    $script$#!/usr/bin/env bash
# Step 1: say where we are running
echo "Boombox test script on $(hostname) as $(whoami)"

# Step 2: write a file, so you can check the script really ran
echo "Boombox test ran at $(date)" > /tmp/boombox-test.txt
echo "Wrote /tmp/boombox-test.txt"
$script$,
    'low',
    'approved',
    NOW(),
    'sample data'
FROM test_event;


-- 8. APPROVED TEST SCRIPT FOR THE WINDOWS CLIENT

WITH test_event AS (
    INSERT INTO events (client_id, event_type, raw_data)
    VALUES (
        '22222222-2222-4222-8222-222222222222',
        'test',
        '{"note": "test data for client developers"}'::jsonb
    )
    RETURNING id, client_id
)
INSERT INTO remediations (
    client_id, event_id, title, summary, proposed_script, severity,
    status, reviewed_at, reviewed_by
)
SELECT
    client_id,
    id,
    'Test script for client developers',
    'Harmless test: prints some info and writes boombox-test.txt to the temp folder.',
    $script$# Step 1: say where we are running
Write-Output "Boombox test script on $env:COMPUTERNAME as $env:USERNAME"

# Step 2: write a file, so you can check the script really ran
"Boombox test ran at $(Get-Date)" | Out-File -FilePath "$env:TEMP\boombox-test.txt"
Write-Output "Wrote $env:TEMP\boombox-test.txt"
$script$,
    'low',
    'approved',
    NOW(),
    'sample data'
FROM test_event;
