package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
)

// logHTTPError reports non-success HTTP responses and indicates whether to stop processing.
func logHTTPError(resp *http.Response) bool {
	if resp.StatusCode >= http.StatusOK && resp.StatusCode < http.StatusMultipleChoices {
		return false
	}

	body, err := io.ReadAll(resp.Body)
	fmt.Printf("WARNING: HTTP request failed with status %s: %s\n", resp.Status, body)
	if err != nil {
		fmt.Println("WARNING: Error reading HTTP error response body:", err)
	}
	return true
}

// setHeaders adds client identity and JSON content headers to an API request.
func setHeaders(request *http.Request) {
	request.Header.Set("x-client-os", os.Getenv("CLIENT_OS"))
	request.Header.Set("x-client-id", os.Getenv("AUTHTOKEN"))
	if request.Method == "POST" {
		request.Header.Set("Content-Type", "application/json")
	}
}
