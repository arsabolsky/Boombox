// Package db owns the PostgreSQL connection pool and all queries against the
// Boombox schema (server/storage/schema.sql).
package db

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
)

// ErrNotFound is returned when a row targeted by id does not exist.
var ErrNotFound = errors.New("not found")

// ErrEventNotFound is returned when inserting a remediation whose event_id
// does not reference an existing event.
var ErrEventNotFound = errors.New("event does not exist")

// ErrNotPending is returned when editing a remediation that has already been
// reviewed (approved or denied) and is therefore no longer editable.
var ErrNotPending = errors.New("remediation is not pending review")

// DB wraps a pgx connection pool.
type DB struct {
	Pool *pgxpool.Pool
}

// Connect opens a connection pool to databaseURL and verifies it with a ping.
func Connect(ctx context.Context, databaseURL string) (*DB, error) {
	cfg, err := pgxpool.ParseConfig(databaseURL)
	if err != nil {
		return nil, fmt.Errorf("parse DATABASE_URL: %w", err)
	}

	cfg.MaxConns = 10
	cfg.MaxConnIdleTime = 5 * time.Minute

	pool, err := pgxpool.NewWithConfig(ctx, cfg)
	if err != nil {
		return nil, fmt.Errorf("create pool: %w", err)
	}

	pingCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	if err := pool.Ping(pingCtx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("ping database: %w", err)
	}

	return &DB{Pool: pool}, nil
}

// Close releases all pooled connections.
func (d *DB) Close() {
	d.Pool.Close()
}

// Ping checks the database is reachable.
func (d *DB) Ping(ctx context.Context) error {
	return d.Pool.Ping(ctx)
}

// ============================================================
// CLIENT / ENDPOINT FUNCTIONS
// ============================================================

// Endpoint represents the data the dashboard needs for each Boombox client.
type Endpoint struct {
	ClientID        string     `json:"client_id"`
	Hostname        string     `json:"hostname"`
	OS              *string    `json:"os"`
	LastSeen        *time.Time `json:"last_seen"`
	EventCount      int64      `json:"event_count"`
	Events24h       int64      `json:"events_24h"`
	PendingCritical int64      `json:"pending_critical"`
	PendingHigh     int64      `json:"pending_high"`
	PendingMedium   int64      `json:"pending_medium"`
	PendingLow      int64      `json:"pending_low"`
	LastAlertAt     *time.Time `json:"last_alert_at"`
}

// ListEndpoints returns all registered Boombox clients with dashboard
// statistics such as event counts and pending remediation counts.
func (d *DB) ListEndpoints(ctx context.Context) ([]Endpoint, error) {
	rows, err := d.Pool.Query(ctx, `
		SELECT
			c.client_id::text,
			c.hostname,
			CASE
				WHEN c.os_version IS NOT NULL
					AND c.os_version <> ''
					AND c.os IS NOT NULL
				THEN c.os || ' ' || c.os_version
				ELSE c.os
			END AS os,
			c.last_seen_at,

			COUNT(DISTINCT e.id)::bigint AS event_count,

			COUNT(DISTINCT e.id)
				FILTER (
					WHERE e.timestamp >= NOW() - INTERVAL '24 hours'
				)::bigint AS events_24h,

			COUNT(DISTINCT r.id)
				FILTER (
					WHERE r.status = 'pending_review'
					AND LOWER(r.severity) = 'critical'
				)::bigint AS pending_critical,

			COUNT(DISTINCT r.id)
				FILTER (
					WHERE r.status = 'pending_review'
					AND LOWER(r.severity) = 'high'
				)::bigint AS pending_high,

			COUNT(DISTINCT r.id)
				FILTER (
					WHERE r.status = 'pending_review'
					AND LOWER(r.severity) = 'medium'
				)::bigint AS pending_medium,

			COUNT(DISTINCT r.id)
				FILTER (
					WHERE r.status = 'pending_review'
					AND LOWER(r.severity) = 'low'
				)::bigint AS pending_low,

			MAX(r.created_at) AS last_alert_at

		FROM clients c

		LEFT JOIN events e
			ON e.client_id = c.client_id

		LEFT JOIN remediations r
			ON r.client_id = c.client_id

		GROUP BY
			c.client_id,
			c.hostname,
			c.os,
			c.os_version,
			c.last_seen_at

		ORDER BY c.hostname;
	`)
	if err != nil {
		return nil, err
	}

	out, err := pgx.CollectRows(
		rows,
		pgx.RowToStructByPos[Endpoint],
	)
	if err != nil {
		return nil, err
	}

	if out == nil {
		out = []Endpoint{}
	}

	return out, nil
}

// ============================================================
// REMEDIATION FUNCTIONS
// ============================================================

// Remediation mirrors the dashboard-facing fields of a remediation row.
//
// ClientID and Hostname identify which monitored client the alert came from.
// They are LEFT JOINed from the clients table and may be null for a remediation
// whose client row has gone away.
type Remediation struct {
	ID             int64      `json:"id"`
	EventID        int64      `json:"event_id"`
	Title          string     `json:"title"`
	Summary        *string    `json:"summary"`
	ProposedScript *string    `json:"proposed_script"`
	Severity       *string    `json:"severity"`
	Status         *string    `json:"status"`
	CreatedAt      *time.Time `json:"created_at"`
	ReviewedAt     *time.Time `json:"reviewed_at"`
	ReviewedBy     *string    `json:"reviewed_by"`
	ClientID       *string    `json:"client_id"`
	Hostname       *string    `json:"hostname"`
}

// NewRemediation holds the fields needed to insert a remediation.
type NewRemediation struct {
	EventID        int64
	Title          string
	Summary        *string
	ProposedScript *string
	Severity       string
}

// ReviewResult is what an approve/deny update returns.
type ReviewResult struct {
	ID         int64      `json:"id"`
	Status     string     `json:"status"`
	ReviewedAt *time.Time `json:"reviewed_at"`
	ReviewedBy *string    `json:"reviewed_by"`
}

// ListRemediations returns all remediations, newest first.
func (d *DB) ListRemediations(ctx context.Context) ([]Remediation, error) {
	rows, err := d.Pool.Query(ctx, `
		SELECT
			r.id,
			r.event_id,
			r.title,
			r.summary,
			r.proposed_script,
			r.severity,
			r.status,
			r.created_at,
			r.reviewed_at,
			r.reviewed_by,
			r.client_id::text,
			c.hostname
		FROM remediations r
		LEFT JOIN clients c
			ON c.client_id = r.client_id
		ORDER BY r.created_at DESC;
	`)
	if err != nil {
		return nil, err
	}

	out, err := pgx.CollectRows(
		rows,
		pgx.RowToStructByPos[Remediation],
	)
	if err != nil {
		return nil, err
	}

	if out == nil {
		out = []Remediation{}
	}

	return out, nil
}

// GetRemediation returns a single remediation by id.
func (d *DB) GetRemediation(
	ctx context.Context,
	id int64,
) (*Remediation, error) {
	rows, err := d.Pool.Query(ctx, `
		SELECT
			r.id,
			r.event_id,
			r.title,
			r.summary,
			r.proposed_script,
			r.severity,
			r.status,
			r.created_at,
			r.reviewed_at,
			r.reviewed_by,
			r.client_id::text,
			c.hostname
		FROM remediations r
		LEFT JOIN clients c
			ON c.client_id = r.client_id
		WHERE r.id = $1;
	`, id)

	if err != nil {
		return nil, err
	}

	r, err := pgx.CollectExactlyOneRow(
		rows,
		pgx.RowToStructByPos[Remediation],
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return nil, ErrNotFound
	}

	if err != nil {
		return nil, err
	}

	return &r, nil
}

// UpdateRemediationScript replaces the proposed_script of a pending remediation
// and returns the updated row. Only remediations still awaiting review can be
// edited; an already approved/denied fix is locked.
func (d *DB) UpdateRemediationScript(
	ctx context.Context,
	id int64,
	script *string,
) (*Remediation, error) {
	tag, err := d.Pool.Exec(ctx, `
		UPDATE remediations
		SET proposed_script = $1
		WHERE id = $2
			AND status = 'pending_review';
	`, script, id)
	if err != nil {
		return nil, err
	}

	// No row updated: either the id is unknown, or it is no longer pending.
	if tag.RowsAffected() == 0 {
		if _, err := d.GetRemediation(ctx, id); err != nil {
			return nil, err // ErrNotFound when the id is unknown
		}
		return nil, ErrNotPending
	}

	return d.GetRemediation(ctx, id)
}

// InsertRemediation creates a remediation in pending_review.
//
// client_id is derived from the event rather than supplied by the caller.
// This guarantees that the remediation belongs to the same client as the
// event it is associated with.
func (d *DB) InsertRemediation(
	ctx context.Context,
	r NewRemediation,
) (int64, error) {
	var id int64

	err := d.Pool.QueryRow(ctx, `
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
			$2,
			$3,
			$4,
			$5
		FROM events
		WHERE id = $1
		RETURNING id;
	`,
		r.EventID,
		r.Title,
		r.Summary,
		r.ProposedScript,
		r.Severity,
	).Scan(&id)

	if errors.Is(err, pgx.ErrNoRows) {
		return 0, ErrEventNotFound
	}

	var pgErr *pgconn.PgError
	if errors.As(err, &pgErr) && pgErr.Code == "23503" {
		return 0, ErrEventNotFound
	}

	if err != nil {
		return 0, err
	}

	return id, nil
}

// ReviewRemediation sets status to approved or denied and records the reviewer.
func (d *DB) ReviewRemediation(
	ctx context.Context,
	id int64,
	status string,
	reviewedBy string,
) (*ReviewResult, error) {
	var res ReviewResult

	err := d.Pool.QueryRow(ctx, `
		UPDATE remediations
		SET
			status = $1,
			reviewed_at = NOW(),
			reviewed_by = $2
		WHERE id = $3
		RETURNING
			id,
			status,
			reviewed_at,
			reviewed_by;
	`,
		status,
		reviewedBy,
		id,
	).Scan(
		&res.ID,
		&res.Status,
		&res.ReviewedAt,
		&res.ReviewedBy,
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return nil, ErrNotFound
	}

	if err != nil {
		return nil, err
	}

	return &res, nil
}

// ============================================================
// CLIENT QUERY FUNCTIONS
// ============================================================

// ClientQuery represents a query assigned to a specific client.
type ClientQuery struct {
	QueryID            int64          `json:"query_id"`
	ClientID           string         `json:"client_id"`
	QueryName          string         `json:"query_name"`
	QueryConfiguration map[string]any `json:"query_configuration"`
	Enabled            bool           `json:"enabled"`
	Version            int            `json:"version"`
	CreatedAt          time.Time      `json:"created_at"`
	UpdatedAt          time.Time      `json:"updated_at"`
}

// NewClientQuery contains the fields required to create a client query.
type NewClientQuery struct {
	ClientID           string
	QueryName          string
	QueryConfiguration map[string]any
	Enabled            bool
}

// UpdateClientQuery contains the fields that can be changed on an existing query.
type UpdateClientQuery struct {
	QueryConfiguration map[string]any
	Enabled            bool
}

// CreateClientQuery creates a query for a registered client.
func (d *DB) CreateClientQuery(
	ctx context.Context,
	q NewClientQuery,
) (int64, error) {
	var queryID int64

	err := d.Pool.QueryRow(ctx, `
		INSERT INTO client_queries (
			client_id,
			query_name,
			query_configuration,
			enabled
		)
		VALUES (
			$1::uuid,
			$2,
			$3,
			$4
		)
		RETURNING query_id;
	`,
		q.ClientID,
		q.QueryName,
		q.QueryConfiguration,
		q.Enabled,
	).Scan(&queryID)

	if err != nil {
		return 0, err
	}

	return queryID, nil
}

// ListClientQueries returns queries assigned to one client.
func (d *DB) ListClientQueries(
	ctx context.Context,
	clientID string,
	enabledOnly bool,
) ([]ClientQuery, error) {
	query := `
		SELECT
			query_id,
			client_id::text,
			query_name,
			query_configuration,
			enabled,
			version,
			created_at,
			updated_at
		FROM client_queries
		WHERE client_id = $1::uuid
	`

	if enabledOnly {
		query += ` AND enabled = TRUE`
	}

	query += ` ORDER BY query_name;`

	rows, err := d.Pool.Query(
		ctx,
		query,
		clientID,
	)

	if err != nil {
		return nil, err
	}

	out, err := pgx.CollectRows(
		rows,
		pgx.RowToStructByPos[ClientQuery],
	)

	if err != nil {
		return nil, err
	}

	if out == nil {
		out = []ClientQuery{}
	}

	return out, nil
}

// UpdateClientQuery updates a query and increments its version.
func (d *DB) UpdateClientQuery(
	ctx context.Context,
	queryID int64,
	update UpdateClientQuery,
) (*ClientQuery, error) {
	rows, err := d.Pool.Query(ctx, `
		UPDATE client_queries
		SET
			query_configuration = $1,
			enabled = $2,
			version = version + 1,
			updated_at = NOW()
		WHERE query_id = $3
		RETURNING
			query_id,
			client_id::text,
			query_name,
			query_configuration,
			enabled,
			version,
			created_at,
			updated_at;
	`,
		update.QueryConfiguration,
		update.Enabled,
		queryID,
	)

	if err != nil {
		return nil, err
	}

	result, err := pgx.CollectExactlyOneRow(
		rows,
		pgx.RowToStructByPos[ClientQuery],
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return nil, ErrNotFound
	}

	if err != nil {
		return nil, err
	}

	return &result, nil
}
