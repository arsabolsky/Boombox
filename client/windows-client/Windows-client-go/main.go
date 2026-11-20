package main

import (
	"bufio"
	"bytes"
	"context"
	"crypto/rand"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"
)

const maxHTTPResponseBytes = 10 * 1024 * 1024

var uuidPattern = regexp.MustCompile(
	`(?i)^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`,
)

type Config struct {
	APIBaseURL              string
	APIToken                string
	OsqueryPath             string
	ClientIDPath            string
	RunOnce                 bool
	EnableRemediation       bool
	RemediationPollInterval time.Duration
	RemediationTimeout      time.Duration
	QueryTimeout            time.Duration
	HTTPTimeout             time.Duration
	ResultsTimeout          time.Duration
	DefaultPollInterval     time.Duration
	MinimumPollInterval     time.Duration
	MaximumPollInterval     time.Duration
	MaximumQueryOutputBytes int
}

type Identity struct {
	ClientID        string
	Hostname        string
	OperatingSystem string
}

type QueryTask struct {
	Name string `json:"name"`
	SQL  string `json:"sql"`
}

type RegisterRequest struct {
	Hostname  string `json:"hostname"`
	OS        string `json:"os"`
	OSVersion string `json:"os_version"`
}

type RegisterResponse struct {
	ClientID string `json:"client_id"`
}

type QueryResult struct {
	Name  string          `json:"name"`
	Rows  json.RawMessage `json:"rows,omitempty"`
	Error string          `json:"error,omitempty"`
}

type ResultsRequest struct {
	Results []QueryResult `json:"results"`
}

type RemediationCommand struct {
	ID     int64  `json:"id"`
	Script string `json:"script"`
}

type RemediationResult struct {
	ExitCode int    `json:"exit_code"`
	Output   string `json:"output"`
}

type Agent struct {
	config Config
	http   *http.Client
}

func main() {
	config, err := loadConfig()
	if err != nil {
		logLine("Fatal configuration error: %v", err)
		os.Exit(1)
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()

	agent := Agent{
		config: config,
		http: &http.Client{
			// Each request uses its own context deadline.
			Timeout: 0,
		},
	}

	if err := agent.run(ctx); err != nil {
		logLine("Fatal error: %v", err)
		os.Exit(1)
	}
}

func loadConfig() (Config, error) {
	configDirectory, err := findConfigDirectory()
	if err != nil {
		return Config{}, err
	}

	if err := loadEnvFile(filepath.Join(configDirectory, ".env")); err != nil {
		return Config{}, err
	}

	queryTimeout, err := envSeconds("QUERY_TIMEOUT_SECONDS", 30)
	if err != nil {
		return Config{}, err
	}
	httpTimeout, err := envSeconds("HTTP_TIMEOUT_SECONDS", 30)
	if err != nil {
		return Config{}, err
	}
	resultsTimeout, err := envSeconds("RESULTS_TIMEOUT_SECONDS", 180)
	if err != nil {
		return Config{}, err
	}
	defaultPoll, err := envSeconds("DEFAULT_POLL_INTERVAL_SECONDS", 300)
	if err != nil {
		return Config{}, err
	}
	minimumPoll, err := envSeconds("MINIMUM_POLL_INTERVAL_SECONDS", 5)
	if err != nil {
		return Config{}, err
	}
	maximumPoll, err := envSeconds("MAXIMUM_POLL_INTERVAL_SECONDS", 3600)
	if err != nil {
		return Config{}, err
	}
	maximumOutput, err := envInt("MAXIMUM_QUERY_OUTPUT_BYTES", 5*1024*1024)
	if err != nil {
		return Config{}, err
	}
	runOnce, err := envBool("RUN_ONCE", false)
	if err != nil {
		return Config{}, err
	}
	enableRemediation, err := envBool("ENABLE_REMEDIATION", true)
	if err != nil {
		return Config{}, err
	}
	remediationPoll, err := envSeconds("REMEDIATION_POLL_INTERVAL_SECONDS", 300)
	if err != nil {
		return Config{}, err
	}
	remediationTimeout, err := envSeconds("REMEDIATION_TIMEOUT_SECONDS", 60)
	if err != nil {
		return Config{}, err
	}

	apiBaseURL := strings.TrimSpace(envOrDefault("API_BASE_URL", "http://localhost:8080/"))
	parsedBase, err := url.Parse(apiBaseURL)
	if err != nil || parsedBase.Scheme == "" || parsedBase.Host == "" {
		return Config{}, fmt.Errorf("API_BASE_URL must be an absolute HTTP or HTTPS URL")
	}
	if parsedBase.Scheme != "http" && parsedBase.Scheme != "https" {
		return Config{}, fmt.Errorf("API_BASE_URL must use http or https")
	}
	if minimumPoll > maximumPoll {
		return Config{}, fmt.Errorf(
			"MINIMUM_POLL_INTERVAL_SECONDS cannot exceed MAXIMUM_POLL_INTERVAL_SECONDS",
		)
	}
	return Config{
		APIBaseURL:              apiBaseURL,
		APIToken:                strings.TrimSpace(os.Getenv("API_TOKEN")),
		OsqueryPath:             strings.TrimSpace(envOrDefault("OSQUERY_PATH", `C:\Program Files\osquery\osqueryi.exe`)),
		ClientIDPath:            envOrDefault("CLIENT_ID_PATH", filepath.Join(configDirectory, "client-id.txt")),
		RunOnce:                 runOnce,
		EnableRemediation:       enableRemediation,
		RemediationPollInterval: remediationPoll,
		RemediationTimeout:      remediationTimeout,
		QueryTimeout:            queryTimeout,
		HTTPTimeout:             httpTimeout,
		ResultsTimeout:          resultsTimeout,
		DefaultPollInterval:     defaultPoll,
		MinimumPollInterval:     minimumPoll,
		MaximumPollInterval:     maximumPoll,
		MaximumQueryOutputBytes: maximumOutput,
	}, nil
}

func findConfigDirectory() (string, error) {
	executable, err := os.Executable()
	if err != nil {
		return "", fmt.Errorf("find executable directory: %w", err)
	}
	executableDirectory := filepath.Dir(executable)

	workingDirectory, err := os.Getwd()
	if err == nil {
		if _, statErr := os.Stat(filepath.Join(workingDirectory, ".env")); statErr == nil {
			return workingDirectory, nil
		}
	}
	return executableDirectory, nil
}

func loadEnvFile(path string) error {
	file, err := os.Open(path)
	if errors.Is(err, os.ErrNotExist) {
		return nil
	}
	if err != nil {
		return fmt.Errorf("open %s: %w", path, err)
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	lineNumber := 0
	for scanner.Scan() {
		lineNumber++
		line := strings.TrimSpace(strings.TrimPrefix(scanner.Text(), "\ufeff"))
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		key, value, found := strings.Cut(line, "=")
		if !found {
			return fmt.Errorf("invalid .env line %d: expected KEY=VALUE", lineNumber)
		}
		key = strings.TrimSpace(key)
		value = strings.TrimSpace(value)
		if key == "" {
			return fmt.Errorf("invalid .env line %d: empty key", lineNumber)
		}
		if len(value) >= 2 {
			if (value[0] == '"' && value[len(value)-1] == '"') ||
				(value[0] == '\'' && value[len(value)-1] == '\'') {
				value = value[1 : len(value)-1]
			}
		}
		if _, alreadySet := os.LookupEnv(key); !alreadySet {
			if err := os.Setenv(key, value); err != nil {
				return fmt.Errorf("set %s from .env: %w", key, err)
			}
		}
	}
	if err := scanner.Err(); err != nil {
		return fmt.Errorf("read %s: %w", path, err)
	}
	return nil
}

func envOrDefault(name, fallback string) string {
	if value, ok := os.LookupEnv(name); ok {
		return value
	}
	return fallback
}

func envInt(name string, fallback int) (int, error) {
	value := fallback
	if raw, ok := os.LookupEnv(name); ok {
		parsed, err := strconv.Atoi(strings.TrimSpace(raw))
		if err != nil {
			return 0, fmt.Errorf("%s must be an integer", name)
		}
		value = parsed
	}
	if value < 1 {
		return 0, fmt.Errorf("%s must be at least 1", name)
	}
	return value, nil
}

func envSeconds(name string, fallback int) (time.Duration, error) {
	value, err := envInt(name, fallback)
	if err != nil {
		return 0, err
	}
	return time.Duration(value) * time.Second, nil
}

func envBool(name string, fallback bool) (bool, error) {
	raw, ok := os.LookupEnv(name)
	if !ok {
		return fallback, nil
	}
	switch strings.ToLower(strings.TrimSpace(raw)) {
	case "1", "true", "yes", "on":
		return true, nil
	case "0", "false", "no", "off":
		return false, nil
	default:
		return false, fmt.Errorf("%s must be true or false", name)
	}
}

func (a *Agent) run(ctx context.Context) error {
	identity := a.obtainIdentityWithRetry(ctx)
	if identity == nil {
		return nil
	}

	logLine(
		"Boombox client started as %s (%s, %s)",
		identity.ClientID,
		identity.Hostname,
		identity.OperatingSystem,
	)

	var remediationDone chan struct{}
	if a.config.EnableRemediation {
		remediationDone = make(chan struct{})
		go func() {
			defer close(remediationDone)
			a.remediationLoop(ctx, *identity)
		}()
	}

	a.telemetryLoop(ctx, *identity)

	if remediationDone != nil {
		if a.config.RunOnce {
			<-remediationDone
		} else {
			select {
			case <-remediationDone:
			case <-time.After(2 * time.Second):
			}
		}
	}

	logLine("Boombox client stopped")
	return nil
}

func (a *Agent) telemetryLoop(ctx context.Context, identity Identity) {
	failureDelay := 10 * time.Second
	for ctx.Err() == nil {
		queries, err := a.poll(ctx, identity)
		if err != nil {
			logLine("Telemetry loop failed: %v; retrying in %s", err, failureDelay)
			if !waitFor(ctx, failureDelay) {
				break
			}
			failureDelay = minDuration(failureDelay*2, 5*time.Minute)
			continue
		}

		logLine("GET /api/v1/poll/queries returned %d queries", len(queries))

		results := make([]QueryResult, 0, len(queries))
		for _, task := range queries {
			if ctx.Err() != nil {
				break
			}
			name := strings.TrimSpace(task.Name)
			if name == "" {
				name = "unnamed"
			}
			logLine("Running osquery query %s", name)
			results = append(results, a.runOsquery(ctx, name, task.SQL))
		}

		if len(results) > 0 && ctx.Err() == nil {
			if err := a.postResults(ctx, identity, results); err != nil {
				logLine("Telemetry loop failed: %v; retrying in %s", err, failureDelay)
				if !waitFor(ctx, failureDelay) {
					break
				}
				failureDelay = minDuration(failureDelay*2, 5*time.Minute)
				continue
			}
		}

		failureDelay = 10 * time.Second
		if a.config.RunOnce {
			logLine("RUN_ONCE is enabled; stopping telemetry after one poll")
			break
		}

		interval := a.config.DefaultPollInterval
		interval = maxDuration(interval, a.config.MinimumPollInterval)
		interval = minDuration(interval, a.config.MaximumPollInterval)
		logLine("Waiting %s for the next telemetry poll", interval)
		if !waitFor(ctx, interval) {
			break
		}
	}
}

func (a *Agent) obtainIdentityWithRetry(ctx context.Context) *Identity {
	delay := 5 * time.Second
	for ctx.Err() == nil {
		identity, err := a.getIdentity(ctx)
		if err == nil {
			return &identity
		}
		logLine("Could not obtain client identity: %v; retrying in %s", err, delay)
		if !waitFor(ctx, delay) {
			return nil
		}
		delay = minDuration(delay*2, 5*time.Minute)
	}
	return nil
}

func (a *Agent) getIdentity(ctx context.Context) (Identity, error) {
	result := a.runOsquery(
		ctx,
		"client_identity",
		"SELECT hostname FROM system_info;",
	)
	if result.Error != "" {
		return Identity{}, errors.New(result.Error)
	}

	var rows []map[string]any
	if err := json.Unmarshal(result.Rows, &rows); err != nil || len(rows) == 0 {
		return Identity{}, fmt.Errorf("system_info returned no identity row")
	}
	hostname := strings.TrimSpace(fmt.Sprint(rows[0]["hostname"]))
	if hostname == "" || hostname == "<nil>" {
		return Identity{}, fmt.Errorf("system_info did not include a hostname")
	}

	clientID, err := readClientID(a.config.ClientIDPath)
	if err != nil {
		return Identity{}, err
	}
	if clientID == "" {
		osVersion := a.getOSVersion(ctx)
		clientID, err = a.registerClient(ctx, RegisterRequest{
			Hostname:  hostname,
			OS:        "windows",
			OSVersion: osVersion,
		})
		if err != nil {
			return Identity{}, err
		}
		clientID, err = saveClientID(a.config.ClientIDPath, clientID)
		if err != nil {
			return Identity{}, err
		}
	}
	return Identity{
		ClientID:        clientID,
		Hostname:        hostname,
		OperatingSystem: "windows",
	}, nil
}

func (a *Agent) getOSVersion(ctx context.Context) string {
	result := a.runOsquery(
		ctx,
		"operating_system",
		"SELECT name, version FROM os_version LIMIT 1;",
	)
	if result.Error != "" {
		logLine("Could not determine OS version: %s", result.Error)
		return "unknown"
	}

	var rows []map[string]any
	if err := json.Unmarshal(result.Rows, &rows); err != nil || len(rows) == 0 {
		logLine("Could not determine OS version: os_version returned no rows")
		return "unknown"
	}
	name := strings.TrimSpace(fmt.Sprint(rows[0]["name"]))
	version := strings.TrimSpace(fmt.Sprint(rows[0]["version"]))
	value := strings.TrimSpace(name + " " + version)
	if value == "" || value == "<nil> <nil>" {
		return "unknown"
	}
	return value
}

func (a *Agent) registerClient(ctx context.Context, registration RegisterRequest) (string, error) {
	payload, err := json.Marshal(registration)
	if err != nil {
		return "", fmt.Errorf("encode registration: %w", err)
	}
	status, body, err := a.request(
		ctx,
		http.MethodPost,
		"api/v1/clients",
		Identity{},
		payload,
		a.config.HTTPTimeout,
		nil,
	)
	if err != nil {
		return "", err
	}

	var response RegisterResponse
	if err := json.Unmarshal(body, &response); err != nil {
		return "", fmt.Errorf("POST /api/v1/clients returned invalid JSON: %w", err)
	}
	clientID := normalizeUUID(response.ClientID)
	if clientID == "" {
		return "", fmt.Errorf("POST /api/v1/clients returned an invalid client_id")
	}
	logLine("POST /api/v1/clients returned HTTP %d; registration succeeded", status)
	return clientID, nil
}

func readClientID(path string) (string, error) {
	if data, err := os.ReadFile(path); err == nil {
		stored := normalizeUUID(string(data))
		if stored == "" {
			return "", fmt.Errorf("client ID file contains an invalid UUID: %s", path)
		}
		return stored, nil
	} else if !errors.Is(err, os.ErrNotExist) {
		return "", fmt.Errorf("read client ID file: %w", err)
	}
	return "", nil
}

func saveClientID(path, value string) (string, error) {
	clientID := normalizeUUID(value)
	if clientID == "" {
		return "", fmt.Errorf("cannot save an invalid client ID")
	}

	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return "", fmt.Errorf("create client ID directory: %w", err)
	}
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o600)
	if errors.Is(err, os.ErrExist) {
		return readClientID(path)
	}
	if err != nil {
		return "", fmt.Errorf("create client ID file: %w", err)
	}
	if _, err := file.WriteString(clientID + "\n"); err != nil {
		file.Close()
		return "", fmt.Errorf("write client ID file: %w", err)
	}
	if err := file.Close(); err != nil {
		return "", fmt.Errorf("close client ID file: %w", err)
	}
	logLine("Created persistent client ID file at %s", path)
	return clientID, nil
}

func normalizeUUID(value string) string {
	value = strings.ToLower(strings.TrimSpace(value))
	if !uuidPattern.MatchString(value) {
		return ""
	}
	return value
}

func newUUID() (string, error) {
	data := make([]byte, 16)
	if _, err := rand.Read(data); err != nil {
		return "", fmt.Errorf("generate UUID: %w", err)
	}
	data[6] = (data[6] & 0x0f) | 0x40
	data[8] = (data[8] & 0x3f) | 0x80
	return fmt.Sprintf(
		"%08x-%04x-%04x-%04x-%012x",
		data[0:4], data[4:6], data[6:8], data[8:10], data[10:16],
	), nil
}

func (a *Agent) runOsquery(ctx context.Context, name, sql string) QueryResult {
	if strings.TrimSpace(sql) == "" {
		return failedQuery(name, "The server returned an empty SQL query.", nil, "")
	}

	queryCtx, cancel := context.WithTimeout(ctx, a.config.QueryTimeout)
	defer cancel()

	command := exec.CommandContext(queryCtx, a.config.OsqueryPath, "--json", sql)
	var stdout bytes.Buffer
	var stderr bytes.Buffer
	command.Stdout = &stdout
	command.Stderr = &stderr

	err := command.Run()
	if errors.Is(queryCtx.Err(), context.DeadlineExceeded) {
		return failedQuery(
			name,
			fmt.Sprintf("The osquery query exceeded %s.", a.config.QueryTimeout),
			nil,
			stderr.String(),
		)
	}
	if err != nil {
		var exitError *exec.ExitError
		if errors.As(err, &exitError) {
			exitCode := exitError.ExitCode()
			return failedQuery(
				name,
				"osquery returned a nonzero exit code.",
				&exitCode,
				stderr.String(),
			)
		}
		return failedQuery(name, "Could not start osqueryi.exe: "+err.Error(), nil, "")
	}

	if stdout.Len() > a.config.MaximumQueryOutputBytes {
		return failedQuery(
			name,
			fmt.Sprintf(
				"osquery output exceeded %d bytes.",
				a.config.MaximumQueryOutputBytes,
			),
			nil,
			stderr.String(),
		)
	}

	var rows []json.RawMessage
	if err := json.Unmarshal(stdout.Bytes(), &rows); err != nil {
		return failedQuery(name, "osquery returned invalid JSON: "+err.Error(), nil, stderr.String())
	}
	compactRows, err := json.Marshal(rows)
	if err != nil {
		return failedQuery(name, "Could not encode osquery rows: "+err.Error(), nil, stderr.String())
	}
	if warning := strings.TrimSpace(stderr.String()); warning != "" {
		logLine("osquery warning for %s: %s", name, warning)
	}
	return QueryResult{Name: name, Rows: compactRows}
}

func failedQuery(name, message string, exitCode *int, stderr string) QueryResult {
	details := []string{strings.TrimSuffix(message, ".")}
	if exitCode != nil {
		details = append(details, fmt.Sprintf("exit code %d", *exitCode))
	}
	if stderr = strings.TrimSpace(stderr); stderr != "" {
		details = append(details, stderr)
	}
	return QueryResult{Name: name, Error: strings.Join(details, ": ")}
}

func (a *Agent) poll(ctx context.Context, identity Identity) ([]QueryTask, error) {
	status, body, err := a.request(
		ctx,
		http.MethodGet,
		"api/v1/poll/queries",
		identity,
		nil,
		a.config.HTTPTimeout,
		nil,
	)
	if err != nil {
		return nil, err
	}
	if status == http.StatusNoContent || len(body) == 0 {
		return []QueryTask{}, nil
	}

	var queries []QueryTask
	if err := json.Unmarshal(body, &queries); err != nil {
		return nil, fmt.Errorf("GET /api/v1/poll/queries returned invalid JSON: %w", err)
	}
	if queries == nil {
		queries = []QueryTask{}
	}
	return queries, nil
}

func (a *Agent) postResults(ctx context.Context, identity Identity, results []QueryResult) error {
	payload, err := json.Marshal(ResultsRequest{Results: results})
	if err != nil {
		return fmt.Errorf("encode results: %w", err)
	}
	submissionID, err := newUUID()
	if err != nil {
		return err
	}
	status, body, err := a.request(
		ctx,
		http.MethodPost,
		"api/v1/results",
		identity,
		payload,
		a.config.ResultsTimeout,
		map[string]string{"Idempotency-Key": submissionID},
	)
	if err != nil {
		return err
	}
	logLine("POST /api/v1/results submission %s returned HTTP %d", submissionID, status)

	if len(body) > 0 {
		var response struct {
			Verdict  string            `json:"verdict"`
			Findings []json.RawMessage `json:"findings"`
		}
		if err := json.Unmarshal(body, &response); err != nil {
			return fmt.Errorf("POST /api/v1/results returned invalid JSON: %w", err)
		}
		if response.Verdict != "" {
			logLine("Server decision: %s (%d findings)", response.Verdict, len(response.Findings))
		}
	}
	return nil
}

func (a *Agent) remediationLoop(ctx context.Context, identity Identity) {
	completedIDs := map[int64]bool{}
	failureDelay := 10 * time.Second

	for ctx.Err() == nil {
		commands, err := a.getRemediationCommands(ctx, identity)
		if err != nil {
			logLine("Remediation loop failed: %v; retrying in %s", err, failureDelay)
			if !waitFor(ctx, failureDelay) {
				return
			}
			failureDelay = minDuration(failureDelay*2, 5*time.Minute)
			continue
		}
		logLine("Remediation poll returned %d command(s)", len(commands))

		for _, command := range commands {
			if ctx.Err() != nil {
				return
			}
			if command.ID <= 0 {
				logLine("Skipping remediation command without an id")
				continue
			}
			if completedIDs[command.ID] {
				logLine("Skipping already executed remediation %d", command.ID)
				continue
			}

			logLine("Running remediation %d", command.ID)
			result := a.executeRemediation(ctx, command)
			completedIDs[command.ID] = true
			if result.ExitCode == 0 {
				logLine("Remediation %d completed successfully", command.ID)
			} else {
				logLine("Remediation %d failed with exit code %d", command.ID, result.ExitCode)
			}
			if result.Output != "" {
				logLine("Remediation %d output: %s", command.ID, result.Output)
			}
		}

		failureDelay = 10 * time.Second
		if a.config.RunOnce {
			logLine("RUN_ONCE is enabled; stopping remediation after one poll")
			return
		}
		if !waitFor(ctx, a.config.RemediationPollInterval) {
			return
		}
	}
}

func (a *Agent) getRemediationCommands(ctx context.Context, identity Identity) ([]RemediationCommand, error) {
	endpoint := "api/v1/poll/remediations"
	status, body, err := a.request(ctx, http.MethodGet, endpoint, identity, nil, a.config.HTTPTimeout, nil)
	if err != nil {
		return nil, err
	}
	if status == http.StatusNoContent || len(body) == 0 {
		return []RemediationCommand{}, nil
	}
	var commands []RemediationCommand
	if err := json.Unmarshal(body, &commands); err != nil {
		return nil, fmt.Errorf("GET /%s returned invalid JSON: %w", endpoint, err)
	}
	if commands == nil {
		commands = []RemediationCommand{}
	}
	return commands, nil
}

func (a *Agent) executeRemediation(ctx context.Context, remediation RemediationCommand) RemediationResult {
	if strings.TrimSpace(remediation.Script) == "" {
		return RemediationResult{ExitCode: -1, Output: "Remediation did not include a script."}
	}

	temporary, err := os.CreateTemp("", "boombox-*.ps1")
	if err != nil {
		return RemediationResult{ExitCode: -1, Output: "Could not create temporary script: " + err.Error()}
	}
	scriptPath := temporary.Name()
	defer os.Remove(scriptPath)
	if _, err := temporary.WriteString(remediation.Script + "\n"); err != nil {
		temporary.Close()
		return RemediationResult{ExitCode: -1, Output: "Could not write temporary script: " + err.Error()}
	}
	if err := temporary.Close(); err != nil {
		return RemediationResult{ExitCode: -1, Output: "Could not close temporary script: " + err.Error()}
	}

	commandCtx, cancel := context.WithTimeout(ctx, a.config.RemediationTimeout)
	defer cancel()
	command := exec.CommandContext(
		commandCtx,
		"powershell.exe",
		"-NoProfile",
		"-NonInteractive",
		"-ExecutionPolicy",
		"Bypass",
		"-File",
		scriptPath,
	)
	var stdout bytes.Buffer
	var stderr bytes.Buffer
	command.Stdout = &stdout
	command.Stderr = &stderr
	err = command.Run()
	output := a.combineCommandOutput(stdout.String(), stderr.String())
	if errors.Is(commandCtx.Err(), context.DeadlineExceeded) {
		if output != "" {
			output += "\n"
		}
		output += fmt.Sprintf("Remediation exceeded %s and was stopped.", a.config.RemediationTimeout)
		return RemediationResult{ExitCode: -1, Output: output}
	}
	if err != nil {
		var exitError *exec.ExitError
		if errors.As(err, &exitError) {
			return RemediationResult{ExitCode: exitError.ExitCode(), Output: output}
		}
		return RemediationResult{ExitCode: -1, Output: "Could not run PowerShell remediation: " + err.Error()}
	}
	return RemediationResult{ExitCode: 0, Output: output}
}

func (a *Agent) combineCommandOutput(stdout, stderr string) string {
	parts := []string{}
	if stdout = strings.TrimSpace(stdout); stdout != "" {
		parts = append(parts, stdout)
	}
	if stderr = strings.TrimSpace(stderr); stderr != "" {
		parts = append(parts, "[stderr]\n"+stderr)
	}
	output := strings.Join(parts, "\n")
	if len(output) > a.config.MaximumQueryOutputBytes {
		output = output[:a.config.MaximumQueryOutputBytes] + "\n[output truncated]"
	}
	return output
}

func (a *Agent) request(
	ctx context.Context,
	method string,
	endpoint string,
	identity Identity,
	payload []byte,
	timeout time.Duration,
	extraHeaders map[string]string,
) (int, []byte, error) {
	requestURL, err := resolveEndpoint(a.config.APIBaseURL, endpoint)
	if err != nil {
		return 0, nil, err
	}

	requestCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	var body io.Reader
	if payload != nil {
		body = bytes.NewReader(payload)
	}
	request, err := http.NewRequestWithContext(requestCtx, method, requestURL, body)
	if err != nil {
		return 0, nil, fmt.Errorf("create %s request: %w", method, err)
	}
	request.Header.Set("Accept", "application/json")
	if identity.ClientID != "" {
		request.Header.Set("X-Client-Id", identity.ClientID)
	}
	if payload != nil {
		request.Header.Set("Content-Type", "application/json")
	}
	if a.config.APIToken != "" {
		request.Header.Set("Authorization", "Bearer "+a.config.APIToken)
	}
	for key, value := range extraHeaders {
		request.Header.Set(key, value)
	}

	response, err := a.http.Do(request)
	if err != nil {
		return 0, nil, fmt.Errorf("%s %s failed: %w", method, requestURL, err)
	}
	defer response.Body.Close()

	limited := io.LimitReader(response.Body, maxHTTPResponseBytes+1)
	responseBody, err := io.ReadAll(limited)
	if err != nil {
		return 0, nil, fmt.Errorf("read %s %s response: %w", method, requestURL, err)
	}
	if len(responseBody) > maxHTTPResponseBytes {
		return 0, nil, fmt.Errorf("%s %s response exceeded %d bytes", method, requestURL, maxHTTPResponseBytes)
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		message := strings.TrimSpace(string(responseBody))
		return response.StatusCode, responseBody, fmt.Errorf(
			"%s %s returned HTTP %d: %s",
			method,
			requestURL,
			response.StatusCode,
			message,
		)
	}
	return response.StatusCode, responseBody, nil
}

func resolveEndpoint(baseURL, endpoint string) (string, error) {
	base, err := url.Parse(baseURL)
	if err != nil {
		return "", fmt.Errorf("parse API_BASE_URL: %w", err)
	}
	if !strings.HasSuffix(base.Path, "/") {
		base.Path += "/"
	}
	reference, err := url.Parse(strings.TrimPrefix(endpoint, "/"))
	if err != nil {
		return "", fmt.Errorf("parse endpoint: %w", err)
	}
	return base.ResolveReference(reference).String(), nil
}

func waitFor(ctx context.Context, duration time.Duration) bool {
	timer := time.NewTimer(duration)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return false
	case <-timer.C:
		return true
	}
}

func minDuration(left, right time.Duration) time.Duration {
	if left < right {
		return left
	}
	return right
}

func maxDuration(left, right time.Duration) time.Duration {
	if left > right {
		return left
	}
	return right
}

func logLine(format string, values ...any) {
	message := fmt.Sprintf(format, values...)
	fmt.Printf("%s %s\n", time.Now().UTC().Format(time.RFC3339), message)
}
