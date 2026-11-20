// Package api exposes the dashboard REST API. Routes and JSON shapes match the
// original FastAPI service (server/api/app.py) so the Vue frontend works as-is.
package api

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/boombox/dashboard/backend/internal/db"
)

// Server holds dependencies for the HTTP handlers.
type Server struct {
	DB *db.DB
}

// Routes builds the HTTP handler with all routes registered.
func (s *Server) Routes() http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /health", s.health)

	// Client / endpoint routes
	mux.HandleFunc("GET /api/v1/endpoints", s.listEndpoints)

	// Client query routes
	mux.HandleFunc(
		"GET /api/v1/clients/{client_id}/queries",
		s.listClientQueries,
	)
	mux.HandleFunc(
		"POST /api/v1/client-queries",
		s.createClientQuery,
	)
	mux.HandleFunc(
		"PUT /api/v1/client-queries/{id}",
		s.updateClientQuery,
	)

	// Remediation routes
	mux.HandleFunc("GET /api/v1/remediations", s.listRemediations)
	mux.HandleFunc("POST /api/v1/remediations", s.createRemediation)
	mux.HandleFunc("GET /api/v1/remediations/{id}", s.getRemediation)
	mux.HandleFunc(
		"POST /api/v1/remediations/{id}/approve",
		s.reviewHandler("approved"),
	)
	mux.HandleFunc(
		"POST /api/v1/remediations/{id}/deny",
		s.reviewHandler("denied"),
	)

	return logRequests(mux)
}

// ============================================================
// HEALTH
// ============================================================

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()

	if err := s.DB.Ping(ctx); err != nil {
		writeJSON(
			w,
			http.StatusServiceUnavailable,
			map[string]string{
				"status":   "degraded",
				"database": "unreachable",
			},
		)
		return
	}

	writeJSON(
		w,
		http.StatusOK,
		map[string]string{
			"status":   "ok",
			"database": "ok",
		},
	)
}

// ============================================================
// CLIENT / ENDPOINT ROUTES
// ============================================================

func (s *Server) listEndpoints(w http.ResponseWriter, r *http.Request) {
	rows, err := s.DB.ListEndpoints(r.Context())
	if err != nil {
		internalError(w, err)
		return
	}

	writeJSON(w, http.StatusOK, rows)
}

// ============================================================
// CLIENT QUERY ROUTES
// ============================================================

type clientQueryRequest struct {
	ClientID           string         `json:"client_id"`
	QueryName          string         `json:"query_name"`
	QueryConfiguration map[string]any `json:"query_configuration"`
	Enabled            bool           `json:"enabled"`
}

type clientQueryUpdateRequest struct {
	QueryConfiguration map[string]any `json:"query_configuration"`
	Enabled            bool           `json:"enabled"`
}

// createClientQuery creates a query assigned to a specific client.
func (s *Server) createClientQuery(
	w http.ResponseWriter,
	r *http.Request,
) {
	var req clientQueryRequest

	if !decodeJSON(w, r, &req) {
		return
	}

	var missing []string

	if strings.TrimSpace(req.ClientID) == "" {
		missing = append(missing, "client_id")
	}

	if strings.TrimSpace(req.QueryName) == "" {
		missing = append(missing, "query_name")
	}

	if req.QueryConfiguration == nil {
		missing = append(missing, "query_configuration")
	}

	if len(missing) > 0 {
		writeDetail(
			w,
			http.StatusUnprocessableEntity,
			"missing required fields: "+strings.Join(missing, ", "),
		)
		return
	}

	queryID, err := s.DB.CreateClientQuery(
		r.Context(),
		db.NewClientQuery{
			ClientID:           req.ClientID,
			QueryName:          req.QueryName,
			QueryConfiguration: req.QueryConfiguration,
			Enabled:            req.Enabled,
		},
	)

	if err != nil {
		internalError(w, err)
		return
	}

	writeJSON(
		w,
		http.StatusOK,
		map[string]any{
			"query_id":  queryID,
			"client_id": req.ClientID,
		},
	)
}

// listClientQueries returns queries belonging to one client.
func (s *Server) listClientQueries(
	w http.ResponseWriter,
	r *http.Request,
) {
	clientID := r.PathValue("client_id")

	if strings.TrimSpace(clientID) == "" {
		writeDetail(
			w,
			http.StatusUnprocessableEntity,
			"client_id is required",
		)
		return
	}

	enabledOnly := true

	if value := r.URL.Query().Get("enabled_only"); value != "" {
		parsed, err := strconv.ParseBool(value)

		if err != nil {
			writeDetail(
				w,
				http.StatusUnprocessableEntity,
				"enabled_only must be true or false",
			)
			return
		}

		enabledOnly = parsed
	}

	rows, err := s.DB.ListClientQueries(
		r.Context(),
		clientID,
		enabledOnly,
	)

	if err != nil {
		internalError(w, err)
		return
	}

	writeJSON(w, http.StatusOK, rows)
}

// updateClientQuery changes configuration/enabled state and increments version.
func (s *Server) updateClientQuery(
	w http.ResponseWriter,
	r *http.Request,
) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}

	var req clientQueryUpdateRequest

	if !decodeJSON(w, r, &req) {
		return
	}

	if req.QueryConfiguration == nil {
		writeDetail(
			w,
			http.StatusUnprocessableEntity,
			"missing required fields: query_configuration",
		)
		return
	}

	result, err := s.DB.UpdateClientQuery(
		r.Context(),
		id,
		db.UpdateClientQuery{
			QueryConfiguration: req.QueryConfiguration,
			Enabled:            req.Enabled,
		},
	)

	if errors.Is(err, db.ErrNotFound) {
		writeDetail(
			w,
			http.StatusNotFound,
			fmt.Sprintf("Client query %d does not exist", id),
		)
		return
	}

	if err != nil {
		internalError(w, err)
		return
	}

	writeJSON(w, http.StatusOK, result)
}

// ============================================================
// REMEDIATION ROUTES
// ============================================================

func (s *Server) listRemediations(
	w http.ResponseWriter,
	r *http.Request,
) {
	rows, err := s.DB.ListRemediations(r.Context())
	if err != nil {
		internalError(w, err)
		return
	}

	writeJSON(w, http.StatusOK, rows)
}

func (s *Server) getRemediation(
	w http.ResponseWriter,
	r *http.Request,
) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}

	rem, err := s.DB.GetRemediation(r.Context(), id)

	if errors.Is(err, db.ErrNotFound) {
		writeDetail(
			w,
			http.StatusNotFound,
			fmt.Sprintf("Remediation %d does not exist", id),
		)
		return
	}

	if err != nil {
		internalError(w, err)
		return
	}

	writeJSON(w, http.StatusOK, rem)
}

type remediationRequest struct {
	EventID        *int64  `json:"event_id"`
	Title          string  `json:"title"`
	Summary        *string `json:"summary"`
	ProposedScript *string `json:"proposed_script"`
	Severity       string  `json:"severity"`
}

func (s *Server) createRemediation(
	w http.ResponseWriter,
	r *http.Request,
) {
	var req remediationRequest

	if !decodeJSON(w, r, &req) {
		return
	}

	var missing []string

	if req.EventID == nil {
		missing = append(missing, "event_id")
	}

	if strings.TrimSpace(req.Title) == "" {
		missing = append(missing, "title")
	}

	if strings.TrimSpace(req.Severity) == "" {
		missing = append(missing, "severity")
	}

	if len(missing) > 0 {
		writeDetail(
			w,
			http.StatusUnprocessableEntity,
			"missing required fields: "+strings.Join(missing, ", "),
		)
		return
	}

	id, err := s.DB.InsertRemediation(
		r.Context(),
		db.NewRemediation{
			EventID:        *req.EventID,
			Title:          req.Title,
			Summary:        req.Summary,
			ProposedScript: req.ProposedScript,
			Severity:       req.Severity,
		},
	)

	if errors.Is(err, db.ErrEventNotFound) {
		writeDetail(
			w,
			http.StatusNotFound,
			fmt.Sprintf(
				"Event %d does not exist",
				*req.EventID,
			),
		)
		return
	}

	if err != nil {
		internalError(w, err)
		return
	}

	writeJSON(
		w,
		http.StatusOK,
		map[string]any{
			"id":     id,
			"status": "pending_review",
		},
	)
}

type reviewRequest struct {
	ReviewedBy string `json:"reviewed_by"`
}

func (s *Server) reviewHandler(status string) http.HandlerFunc {
	return func(
		w http.ResponseWriter,
		r *http.Request,
	) {
		id, ok := pathID(w, r)
		if !ok {
			return
		}

		var req reviewRequest

		if !decodeJSON(w, r, &req) {
			return
		}

		if strings.TrimSpace(req.ReviewedBy) == "" {
			writeDetail(
				w,
				http.StatusUnprocessableEntity,
				"missing required fields: reviewed_by",
			)
			return
		}

		res, err := s.DB.ReviewRemediation(
			r.Context(),
			id,
			status,
			req.ReviewedBy,
		)

		if errors.Is(err, db.ErrNotFound) {
			writeDetail(
				w,
				http.StatusNotFound,
				fmt.Sprintf(
					"Remediation %d does not exist",
					id,
				),
			)
			return
		}

		if err != nil {
			internalError(w, err)
			return
		}

		writeJSON(w, http.StatusOK, res)
	}
}

// ============================================================
// HELPERS
// ============================================================

func pathID(
	w http.ResponseWriter,
	r *http.Request,
) (int64, bool) {
	id, err := strconv.ParseInt(
		r.PathValue("id"),
		10,
		64,
	)

	if err != nil || id <= 0 {
		writeDetail(
			w,
			http.StatusUnprocessableEntity,
			"id must be a positive integer",
		)
		return 0, false
	}

	return id, true
}

func decodeJSON(
	w http.ResponseWriter,
	r *http.Request,
	dst any,
) bool {
	r.Body = http.MaxBytesReader(
		w,
		r.Body,
		1<<20,
	)

	if err := json.NewDecoder(r.Body).Decode(dst); err != nil {
		writeDetail(
			w,
			http.StatusUnprocessableEntity,
			"invalid JSON body: "+err.Error(),
		)
		return false
	}

	return true
}

func writeJSON(
	w http.ResponseWriter,
	status int,
	v any,
) {
	w.Header().Set(
		"Content-Type",
		"application/json",
	)

	w.WriteHeader(status)

	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf(
			"encode response: %v",
			err,
		)
	}
}

func writeDetail(
	w http.ResponseWriter,
	status int,
	detail string,
) {
	writeJSON(
		w,
		status,
		map[string]string{
			"detail": detail,
		},
	)
}

func internalError(
	w http.ResponseWriter,
	err error,
) {
	log.Printf(
		"internal error: %v",
		err,
	)

	writeDetail(
		w,
		http.StatusInternalServerError,
		"internal server error",
	)
}

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (s *statusRecorder) WriteHeader(code int) {
	s.status = code
	s.ResponseWriter.WriteHeader(code)
}

func logRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(
		func(
			w http.ResponseWriter,
			r *http.Request,
		) {
			start := time.Now()

			rec := &statusRecorder{
				ResponseWriter: w,
				status:         http.StatusOK,
			}

			next.ServeHTTP(rec, r)

			log.Printf(
				"%s %s %d %s",
				r.Method,
				r.URL.Path,
				rec.status,
				time.Since(start).Round(time.Millisecond),
			)
		},
	)
}
