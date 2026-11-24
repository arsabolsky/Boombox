package main

import (
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"
	"strconv"
	"time"

	"github.com/joho/godotenv"
)

// main loads configuration, registers the client, and polls for work.
func main() {
	// Load from ENV: Query interval, api paths, etc
	err := godotenv.Load()
	if err != nil {
		fmt.Println("INFO: .env not found, ensure systemd environment variables are set")
	}

	server := os.Getenv("API_HOST")
	client := &http.Client{
		Timeout: 10 * time.Second, // Don't let unanswered requests hang the program
	}

	authToken := sendRegisterRequest(client, server)
	if authToken == "" {
		log.Fatal("FATAL: Failed to get authentication token")
	}
	os.Setenv("AUTHTOKEN", authToken)

	// Set up time-based interval
	interval_seconds, _ := strconv.Atoi(os.Getenv("QUERY_INTERVAL"))
	interval := time.Duration(interval_seconds) * time.Second
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for range ticker.C {
		// Fetch queries
		queries := getQueries(client, server)
		results := []QueryResult{}
		for _, query := range queries {
			// Execute the query
			fmt.Println("INFO: Executing query:", query.Name)
			cmd := exec.Command("osqueryi", "--json", query.SQL)
			out, err := cmd.Output()
			var result QueryResult
			if err != nil {
				result = QueryResult{
					Name:  query.Name,
					Error: err.Error(),
				}
			} else {
				result = QueryResult{
					Name: query.Name,
					Rows: out,
				}
			}
			results = append(results, result)
		}

		sendQueryResults(client, server, results)

		remediations := getRemediations(client, server)
		for index, remediation := range remediations {
			// Execute the command
			fmt.Println("INFO: Executing remediation:", remediation.Script)
			cmd := exec.Command("/bin/bash", "-c", remediation.Script)
			output, err := cmd.Output()
			var result CommandResult
			if err != nil {
				fmt.Printf("WARNING: Command %d failed: %s\n", index, err)
				var exitCode int
				if exitErr, ok := errors.AsType[*exec.ExitError](err); ok {
					exitCode = exitErr.ExitCode()
				}
				result = CommandResult{
					ExitCode: exitCode,
					Output:   string(output),
				}
			} else {
				result = CommandResult{
					ExitCode: 0,
					Output:   string(output),
				}
			}

			sendCommandResults(client, server, result)
		}
	}
}
