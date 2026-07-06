// Command network-daemon is the AutoSRE network observability daemon. It
// periodically probes configured targets (DNS/TCP/HTTP) and exports network_*
// metrics for Prometheus. It performs NO remediation — observe, measure, export.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"

	"github.com/Raynzler/Auto-SRE/internal/config"
	"github.com/Raynzler/Auto-SRE/internal/prober"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))

	cfg, err := config.LoadNetwork()
	if err != nil {
		logger.Error("failed to load config", "err", err)
		os.Exit(1)
	}
	logger.Info("config loaded",
		"listen", cfg.ListenAddr,
		"interval", cfg.PollInterval.String(),
		"timeout", cfg.Timeout.String(),
		"targets", len(cfg.Targets),
	)

	m := prober.NewMetrics()
	p := prober.New(cfg, m, logger)
	srv := newServer(cfg.ListenAddr, m.Registry)

	// Cancel the root context on SIGINT/SIGTERM for graceful shutdown.
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	proberDone := make(chan struct{})
	go func() {
		p.Run(ctx)
		close(proberDone)
	}()

	go func() {
		logger.Info("http server listening", "addr", cfg.ListenAddr)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Error("http server error", "err", err)
			stop() // trigger shutdown if the server dies
		}
	}()

	<-ctx.Done()
	logger.Info("shutdown signal received")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		logger.Error("graceful shutdown failed", "err", err)
	}

	<-proberDone
	logger.Info("daemon stopped")
}

// newServer builds the daemon's minimal HTTP surface: /metrics for Prometheus
// scraping and /health for liveness. (App services get the richer shared server
// introduced in a later milestone; the daemon only needs these two routes.)
func newServer(addr string, reg *prometheus.Registry) *http.Server {
	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.HandlerFor(reg, promhttp.HandlerOpts{}))
	mux.HandleFunc("/health", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_ = json.NewEncoder(w).Encode(map[string]string{
			"status":  "healthy",
			"service": "network-daemon",
		})
	})
	return &http.Server{Addr: addr, Handler: mux}
}
