package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
)

// sendRegisterRequest registers the host and returns its client identifier.
func sendRegisterRequest(client *http.Client, server string) string {
	registerPath := server + os.Getenv("REGISTER_PATH")
	name, err := os.Hostname()
	if err != nil {
		fmt.Println("WARNING: Failed to get hostname:", err)
		return ""
	}
	body := RegisterRequest{
		Hostname:  name,
		Os:        os.Getenv("CLIENT_OS"),
		OsVersion: os.Getenv("OS_VERSION"),
	}
	out, err := json.Marshal(body)
	if err != nil {
		fmt.Println("WARNING: Error marshaling register JSON:", err)
		return ""
	}
	registerRequest, err := http.NewRequest("POST", registerPath, bytes.NewReader(out))
	if err != nil {
		fmt.Println("WARNING: Error creating register request:", err)
		return ""
	}

	setHeaders(registerRequest)

	resp, err := client.Do(registerRequest)
	if err != nil {
		fmt.Println("WARNING: Error posting register request:", err)
		return ""
	}
	defer resp.Body.Close()
	if logHTTPError(resp) {
		return ""
	}
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Println("WARNING: Error reading register response:", err)
		return ""
	}
	var registerResponse RegisterResponse
	if err := json.Unmarshal(respBody, &registerResponse); err != nil {
		fmt.Println("WARNING: Error unmarshaling register response:", err)
		return ""
	}
	return registerResponse.ClientID
}

// sendQueryResults submits osquery task results to the API.
func sendQueryResults(client *http.Client, server string, results []QueryResult) {
	resultsPath := server + os.Getenv("QRESULTS_PATH")
	body := Results{Results: results}
	out, err := json.Marshal(body)
	if err != nil {
		fmt.Println("WARNING: Error parsing results JSON:", err)
		return
	}
	resultsRequest, err := http.NewRequest("POST", resultsPath, bytes.NewReader(out))
	if err != nil {
		fmt.Println("WARNING: Error creating results request:", err)
		return
	}

	setHeaders(resultsRequest)

	resp, err := client.Do(resultsRequest)
	if err != nil {
		fmt.Println("WARNING: Error posting query results:", err)
		return
	}
	defer resp.Body.Close()
	if logHTTPError(resp) {
		return
	}
}

// sendCommandResults submits remediation command output to the API.
func sendCommandResults(client *http.Client, server string, result CommandResult) {
	resultsPath := server + os.Getenv("RRESULTS_PATH")
	out, err := json.Marshal(result)
	if err != nil {
		fmt.Println("WARNING: Error parsing command result:", err)
		return
	}
	resultsRequest, err := http.NewRequest("POST", resultsPath, bytes.NewReader(out))
	if err != nil {
		fmt.Println("WARNING: Error creating results request:", err)
		return
	}

	setHeaders(resultsRequest)

	resp, err := client.Do(resultsRequest)
	if err != nil {
		fmt.Println("WARNING: Error posting command results:", err)
		return
	}
	defer resp.Body.Close()
	if logHTTPError(resp) {
		return
	}
}

// getQueries fetches pending osquery tasks from the API.
func getQueries(client *http.Client, server string) Queries {
	queryPath := server + os.Getenv("QUERIES_PATH")
	queryRequest, err := http.NewRequest("GET", queryPath, nil)
	if err != nil {
		fmt.Println("WARNING: Error creating query request:", err)
		return Queries{}
	}

	setHeaders(queryRequest)

	resp, err := client.Do(queryRequest)
	if err != nil {
		fmt.Println("WARNING: Error fetching queries:", err)
		return Queries{}
	}
	defer resp.Body.Close()
	if logHTTPError(resp) {
		return Queries{}
	}
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Println("WARNING: Error reading queries response:", err)
		return Queries{}
	}

	var q Queries
	if err := json.Unmarshal(body, &q); err != nil {
		fmt.Println("WARNING: Error unmarshaling queries response:", err)
		return Queries{}
	}

	return q
}

// getRemediations fetches pending remediation scripts from the API.
func getRemediations(client *http.Client, server string) Remediations {
	remediationPath := server + os.Getenv("REMEDIATIONS_PATH")
	remediationRequest, err := http.NewRequest("GET", remediationPath, nil)
	if err != nil {
		fmt.Println("WARNING: Error creating remediations request:", err)
		return Remediations{}
	}

	setHeaders(remediationRequest)

	resp, err := client.Do(remediationRequest)
	if err != nil {
		fmt.Println("WARNING: Error fetching remediations:", err)
		return Remediations{}
	}
	defer resp.Body.Close()
	if logHTTPError(resp) {
		return Remediations{}
	}
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Println("WARNING: Error reading remediations response:", err)
		return Remediations{}
	}

	var r Remediations
	if err := json.Unmarshal(body, &r); err != nil {
		fmt.Println("WARNING: Error unmarshaling remediations response:", err)
		return Remediations{}
	}

	return r
}
