CREATE TABLE endpoints (
    id BIGSERIAL PRIMARY KEY,
    hostname TEXT NOT NULL,
    os TEXT,
    last_seen TIMESTAMPTZ
);

CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    endpoint_id BIGINT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    event_type TEXT NOT NULL,
    raw_data JSONB NOT NULL,

    CONSTRAINT fk_events_endpoint
        FOREIGN KEY (endpoint_id)
        REFERENCES endpoints(id)
        ON DELETE CASCADE
);

CREATE TABLE remediations (
    id BIGSERIAL PRIMARY KEY,
    event_id BIGINT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    proposed_script TEXT,
    severity TEXT,
    status TEXT DEFAULT 'pending_review',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    reviewed_by TEXT,

    CONSTRAINT fk_remediations_event
        FOREIGN KEY (event_id)
        REFERENCES events(id)
        ON DELETE CASCADE
);
