package main

import "encoding/json"

// RegisterRequest describes the Linux host during client registration.
type RegisterRequest struct {
	Hostname  string `json:"hostname"`
	Os        string `json:"os"`
	OsVersion string `json:"os_version"`
}

// RegisterResponse contains the client identifier returned after registration.
type RegisterResponse struct {
	ClientID string `json:"client_id"`
}

// QueryResult reports the output or error from an osquery task.
type QueryResult struct {
	Name  string          `json:"name"`
	Rows  json.RawMessage `json:"rows,omitempty"`
	Error string          `json:"error,omitempty"`
}

// Results wraps query results for submission to the API.
type Results struct {
	Results []QueryResult `json:"results"`
}

// CommandResult reports the exit status and output from a remediation command.
type CommandResult struct {
	ExitCode int    `json:"exit_code"`
	Output   string `json:"output"`
}

// Queries lists osquery tasks returned by the server.
type Queries []struct {
	Name string `json:"name"`
	SQL  string `json:"sql"`
}

// Remediations lists remediation scripts returned by the server.
type Remediations []struct {
	ID     int    `json:"id"`
	Script string `json:"script"`
}
