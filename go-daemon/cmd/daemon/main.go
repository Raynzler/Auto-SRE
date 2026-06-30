// Command daemon is the AutoSRE network observability daemon. It periodically
// probes configured targets (DNS/TCP/HTTP) and exports network_* metrics for
// Prometheus. It performs NO remediation — observe, measure, export only.
package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/Raynzler/Auto-SRE/go-daemon/config"
	"github.com/Raynzler/Auto-SRE/go-daemon/internal/metrics"
	"github.com/Raynzler/Auto-SRE/go-daemon/internal/prober"
	"github.com/Raynzler/Auto-SRE/go-daemon/internal/server"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))

	cfg, err := config.Load()
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

	m := metrics.New()
	p := prober.New(cfg, m, logger)
	srv := server.New(cfg.ListenAddr, m.Registry)

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
