package main

import (
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

func main() {
	//Load from ENV: Queries to run, server address
	err := godotenv.Load()
	if err != nil {
		log.Fatal(".env not found")
	}

	server := os.Getenv("SERVER_HOST")
	client := &http.Client{
		Timeout: 10 * time.Second, // Don't let unanswered requests hang the program
	}

	// Set up time-based interval
	interval_seconds, _ := strconv.Atoi(os.Getenv("QUERY_INTERVAL"))
	interval := time.Duration(interval_seconds) * time.Second
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C: // Timer reached the set interval
			// Fetch queries
			queries := getQueries(client, server)
			for index, query := range query_list {
				// Execute the query
				cmd := exec.Command("osqueryi", "--json", query)
				out, err := cmd.Output()
				if err != nil {
					fmt.Printf("Query %d failed: %s", index, err)
				}
				fmt.Println(index, "\n", string(out))

				// TODO: send query results to server
			}

			remediations := getRemediations(client, server)
			for index, command := range remediations {
				// Execute the command
				cmd := exec.Command(command)
				_, err := cmd.Output()
				if err != nil {
					fmt.Printf("Command %d failed: %s", index, err)
					// Should failed commands be logged to the server?
				}
			}
		}
	}
}

type Queries struct {
	// TODO: Add fields as defined by Andrew or others
}

func getQueries(client *http.Client, server string) []string {
	queryPath := server + os.Getenv("QUERIES_PATH")
	queryRequest, err := http.NewRequest("GET", queryPath, nil)
	if err != nil {
		fmt.Println("Error creating query request:", err)
		return nil
	}

	authToken := os.Getenv("AUTHTOKEN")
	queryRequest.Header.Set("Authorization", "Bearer "+authToken)

	resp, err := client.Do(queryRequest)
	if err != nil {
		fmt.Println("Error fetching queries:", err)
		return nil
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)

	// TODO: split into query list

	return string(body)
}

type Remediations struct {
	// TODO: Add fields as defined by Andrew or others
}

func getRemediations(client *http.Client, server string) []string {
	remediationPath := server + os.Getenv("REMEDIATIONS_PATH")
	remediationRequest, err := http.NewRequest("GET", remediationPath, nil)
	if err != nil {
		fmt.Println("Error creating query request:", err)
		return nil
	}

	authToken := os.Getenv("AUTHTOKEN")
	remediationRequest.Header.Set("Authorization", "Bearer "+authToken)

	resp, err := client.Do(remediationRequest)
	if err != nil {
		fmt.Println("Error fetching remediations:", err)
		return nil
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)

	// TODO: split into remediation list

	return string(body)
}
