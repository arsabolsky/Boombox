package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"strconv"
	"time"

	"github.com/joho/godotenv"
)

type Result struct {
	Name  string          `json:"name"`
	Rows  json.RawMessage `json:"rows,omitempty"`
	Error string          `json:"error,omitempty"`
}

func main() {
	//Load from ENV: Query interval, api paths, etc
	err := godotenv.Load()
	if err != nil {
		log.Fatal(".env not found")
	}

	// TODO: Register the client with the server and get an authtoken back

	server := os.Getenv("API_HOST")
	client := &http.Client{
		Timeout: 10 * time.Second, // Don't let unanswered requests hang the program
	}

	// Set up time-based interval
	interval_seconds, _ := strconv.Atoi(os.Getenv("QUERY_INTERVAL"))
	interval := time.Duration(interval_seconds) * time.Second
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for range ticker.C {
		// Fetch queries
		queries := getQueries(client, server)
		results := []Result{}
		for _, query := range queries.Queries {
			// Execute the query
			cmd := exec.Command("osqueryi", "--json", query.SQL)
			out, err := cmd.Output()
			var result Result
			if err != nil {
				result = Result{
					Name:  query.Name,
					Error: err.Error(),
				}
			} else {
				result = Result{
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
			cmd := exec.Command("/bin/bash", "-c", remediation.Script)
			_, err := cmd.Output()
			if err != nil {
				fmt.Printf("Command %d failed: %s", index, err)
				// TODO add failed commands to results
			}
		}
		// TODO Send remediation results to server
	}
}

type Results struct {
	Results []Result `json:"results"`
}

func sendQueryResults(client *http.Client, server string, results []Result) {
	resultsPath := server + os.Getenv("RESULTS_PATH")
	body := Results{Results: results}
	out, err := json.Marshal(body)
	if err != nil {
		fmt.Println("Error parsing results JSON:", err)
		return
	}
	resultsRequest, err := http.NewRequest("POST", resultsPath, bytes.NewReader(out))
	if err != nil {
		fmt.Println("Error creating results request:", err)
		return
	}

	setHeaders(resultsRequest)

	resp, err := client.Do(resultsRequest)
	if err != nil {
		fmt.Println("Error posting query results:", err)
		return
	}
	defer resp.Body.Close()
	if logHTTPError(resp) {
		return
	}
}

type Queries struct {
	Queries []struct {
		Name string `json:"name"`
		SQL  string `json:"sql"`
	} `json:"queries"`
}

func getQueries(client *http.Client, server string) Queries {
	queryPath := server + os.Getenv("QUERIES_PATH")
	queryRequest, err := http.NewRequest("GET", queryPath, nil)
	if err != nil {
		fmt.Println("Error creating query request:", err)
		return Queries{}
	}

	setHeaders(queryRequest)

	resp, err := client.Do(queryRequest)
	if err != nil {
		fmt.Println("Error fetching queries:", err)
		return Queries{}
	}
	defer resp.Body.Close()
	if logHTTPError(resp) {
		return Queries{}
	}
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Println("Error reading queries response:", err)
		return Queries{}
	}

	var q Queries
	if err := json.Unmarshal(body, &q); err != nil {
		fmt.Println("Queries unmarshal error:", err)
		return Queries{}
	}

	return q
}

type Remediations []struct {
	ID     string `json:"id"`
	Shell  string `json:"shell"`
	Script string `json:"script"`
}

func getRemediations(client *http.Client, server string) Remediations {
	remediationPath := server + os.Getenv("REMEDIATIONS_PATH")
	remediationRequest, err := http.NewRequest("GET", remediationPath, nil)
	if err != nil {
		fmt.Println("Error creating remediations request:", err)
		return Remediations{}
	}

	setHeaders(remediationRequest)

	resp, err := client.Do(remediationRequest)
	if err != nil {
		fmt.Println("Error fetching remediations:", err)
		return Remediations{}
	}
	defer resp.Body.Close()
	if logHTTPError(resp) {
		return Remediations{}
	}
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Println("Error reading remediations response:", err)
		return Remediations{}
	}

	var r Remediations
	if err := json.Unmarshal(body, &r); err != nil {
		fmt.Println("Remediations unmarshal error:", err)
		return Remediations{}
	}

	return r
}

func logHTTPError(resp *http.Response) bool {
	if resp.StatusCode >= http.StatusOK && resp.StatusCode < http.StatusMultipleChoices {
		return false
	}

	body, err := io.ReadAll(resp.Body)
	fmt.Printf("HTTP request failed with status %s: %s\n", resp.Status, body)
	if err != nil {
		fmt.Println("Error reading HTTP error response body:", err)
	}
	return true
}

func setHeaders(request *http.Request) {
	request.Header.Set("Authorization", "Bearer "+os.Getenv("AUTHTOKEN"))
	request.Header.Set("x-client-os", os.Getenv("CLIENT_OS"))
	request.Header.Set("x-client-id", "1") // TEMPORARY, WILL JUST USE AUTHTOKEN
}
