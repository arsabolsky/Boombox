package main

import (
  "fmt"
  "os"
  "os/exec"
  "log"
  "strings"
  "time"
  "strconv"

  "github.com/joho/godotenv"
)

func main() {
	//Load from ENV: Queries to run, server address
	err := godotenv.Load()
	if err != nil {
		log.Fatal(".env not found")
	}
	queries := os.Getenv("QUERIES")
	//remote_address := os.Getenv("REMOTE_ADDRESS")

	var query_list []string = strings.Split(queries, ":")

	// Run each query and send result every 60 seconds
	interval_seconds, _ := strconv.Atoi(os.Getenv("QUERY_INTERVAL"))
	interval := time.Duration(interval_seconds) * time.Second
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			for index, query := range query_list {
				cmd := exec.Command("osqueryi", "--csv", query)
				out, err := cmd.Output()
				if err != nil {
					fmt.Printf("Query %d failed: %s", index, err)
				}
				fmt.Println(index,"\n",string(out))
			}
		}
	}
	//Send to remote

	//Have a socket listening
	//Accept commands
	//Run commands
}

