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
// does not reference an existing event (foreign key violation).
var ErrEventNotFound = errors.New("event does not exist")

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
func (d *DB) Close() { d.Pool.Close() }

// Ping checks the database is reachable.
func (d *DB) Ping(ctx context.Context) error { return d.Pool.Ping(ctx) }

// Remediation mirrors a row of the remediations table.
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
		SELECT id, event_id, title, summary, proposed_script, severity,
		       status, created_at, reviewed_at, reviewed_by
		FROM remediations
		ORDER BY created_at DESC`)
	if err != nil {
		return nil, err
	}

	out, err := pgx.CollectRows(rows, pgx.RowToStructByPos[Remediation])
	if err != nil {
		return nil, err
	}
	if out == nil {
		out = []Remediation{} // encode as [] rather than null
	}
	return out, nil
}

// GetRemediation returns a single remediation by id.
func (d *DB) GetRemediation(ctx context.Context, id int64) (*Remediation, error) {
	rows, err := d.Pool.Query(ctx, `
		SELECT id, event_id, title, summary, proposed_script, severity,
		       status, created_at, reviewed_at, reviewed_by
		FROM remediations
		WHERE id = $1`, id)
	if err != nil {
		return nil, err
	}

	r, err := pgx.CollectExactlyOneRow(rows, pgx.RowToStructByPos[Remediation])
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return &r, nil
}

// InsertRemediation creates a remediation in pending_review and returns its id.
func (d *DB) InsertRemediation(ctx context.Context, r NewRemediation) (int64, error) {
	var id int64
	err := d.Pool.QueryRow(ctx, `
		INSERT INTO remediations (event_id, title, summary, proposed_script, severity)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING id`,
		r.EventID, r.Title, r.Summary, r.ProposedScript, r.Severity,
	).Scan(&id)

	var pgErr *pgconn.PgError
	if errors.As(err, &pgErr) && pgErr.Code == "23503" { // foreign_key_violation
		return 0, ErrEventNotFound
	}
	return id, err
}

// ReviewRemediation sets status (approved/denied) and records the reviewer.
func (d *DB) ReviewRemediation(ctx context.Context, id int64, status, reviewedBy string) (*ReviewResult, error) {
	var res ReviewResult
	err := d.Pool.QueryRow(ctx, `
		UPDATE remediations
		SET status = $1, reviewed_at = NOW(), reviewed_by = $2
		WHERE id = $3
		RETURNING id, status, reviewed_at, reviewed_by`,
		status, reviewedBy, id,
	).Scan(&res.ID, &res.Status, &res.ReviewedAt, &res.ReviewedBy)

	if errors.Is(err, pgx.ErrNoRows) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return &res, nil
}
