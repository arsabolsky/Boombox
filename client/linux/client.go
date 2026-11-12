package main

import (
  "fmt"
  "os"
  "os/exec"
  "log"
  "strings"
  "time"
  "strconv"
  "net/http"

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
		Timeout: 10 * time.Second // Don't let unanswered requests hang the program
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
			queries = getQueries(client, server)
			// TODO: split queries into a list, either here or in getQueries
			for index, query := range query_list {
				// Execute the query
				cmd := exec.Command("osqueryi", "--json", query)
				out, err := cmd.Output()
				if err != nil {
					fmt.Printf("Query %d failed: %s", index, err)
				}
				fmt.Println(index,"\n",string(out))

				// TODO: query results to server
			}

			// TODO: Get and execute remediations
		}
	}
}

func getQueries(client *http.Client, server string) string {
	queryPath := server + os.Getenv("QUERIES_PATH")
	queryRequest, err := http.NewRequest("GET", queryPath, nil)
	if err != nil {
		fmt.Println("Error creating query request:", err)
		return ''
	}

	authToken := os.Getenv("AUTHTOKEN")
	queryRequest.Header.Set("Authorization", "Bearer " + authToken)

	resp, err = client.Do(queryRequest)
	if err != nil {
		fmt.Println("Error fetching queries:", err)
		return ''
	}
	defer resp.Body.Close()

	return resp.Body
}

func getRemediations(client *http.Client, server string) string {
	remediationPath := server + os.Getenv("REMEDIATIONS_PATH")
	remediationRequest, err := http.NewRequest("GET", remediationPath, nil)
	if err != nil {
		fmt.Println("Error creating query request:", err)
		return
	}

	authToken := os.Getenv("AUTHTOKEN")
	remediationRequest.Header.Set("Authorization", "Bearer " + authtoken)

	resp, err = client.Do(remediationRequest)
	if err != nil {
		fmt.Println("Error fetching remediations:", err)
		return ''
	}
	defer resp.Body.Close()

	return resp.Body
}

