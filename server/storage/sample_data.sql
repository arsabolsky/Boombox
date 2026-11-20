
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
