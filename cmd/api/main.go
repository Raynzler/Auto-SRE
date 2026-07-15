// Command api is the AutoSRE API service. main stays intentionally tiny: it
// wires configuration, handlers, router, and server together and runs until a
// termination signal, then shuts down gracefully.
package main

import (
	"context"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	"github.com/Raynzler/Auto-SRE/internal/clients"
	"github.com/Raynzler/Auto-SRE/internal/config"
	"github.com/Raynzler/Auto-SRE/internal/handlers"
	"github.com/Raynzler/Auto-SRE/internal/router"
	"github.com/Raynzler/Auto-SRE/internal/server"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))

	cfg, err := config.LoadService("api", 8000)
	if err != nil {
		logger.Error("failed to load config", "err", err)
		os.Exit(1)
	}
	logger.Info("config loaded", "service", cfg.Service, "listen", cfg.ListenAddr)

	h := handlers.New(cfg, clients.NewAuth(cfg.AuthURL))
	handler := router.New(h, logger, func(mux *http.ServeMux) {
		mux.HandleFunc("POST /orders", h.CreateOrder)
	})
	srv := server.New(cfg.ListenAddr, handler, logger)

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	if err := srv.Run(ctx); err != nil {
		logger.Error("server error", "err", err)
		os.Exit(1)
	}
	logger.Info("api stopped")
}
