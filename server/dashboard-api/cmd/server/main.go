// Command server runs the Boombox dashboard API.
package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/joho/godotenv"

	"github.com/boombox/dashboard/backend/internal/api"
	"github.com/boombox/dashboard/backend/internal/db"
)

func main() {
	// Config lives in the repo-root .env. Try the working directory first, then
	// the repo root relative to dashboard/backend. Real env vars take precedence.
	for _, p := range []string{".env", "../../.env"} {
		if err := godotenv.Load(p); err == nil {
			log.Printf("loaded config from %s", p)
			break
		}
	}

	databaseURL := os.Getenv("DATABASE_URL")
	if databaseURL == "" {
		log.Fatal("DATABASE_URL is not set")
	}

	addr := os.Getenv("DASHBOARD_API_ADDR")
	if addr == "" {
		addr = ":8000" // matches the Vite dev proxy in dashboard/frontend
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	database, err := db.Connect(ctx, databaseURL)
	if err != nil {
		log.Fatalf("database: %v", err)
	}
	defer database.Close()
	log.Print("connected to PostgreSQL")

	srv := &http.Server{
		Addr:              addr,
		Handler:           (&api.Server{DB: database}).Routes(),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	go func() {
		log.Printf("Boombox dashboard API listening on %s", addr)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Fatalf("listen: %v", err)
		}
	}()

	<-ctx.Done()
	log.Print("shutting down")
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Printf("shutdown: %v", err)
	}
}
