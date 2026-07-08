// Package server provides a production-grade net/http server wrapper with
// sensible timeouts and graceful startup/shutdown, reusable by every AutoSRE
// service.
package server

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"time"
)

// Timeout defaults. WriteTimeout exceeds the router's per-request timeout so the
// TimeoutHandler can write its 503 before the server severs the connection.
const (
	readHeaderTimeout = 5 * time.Second
	readTimeout       = 15 * time.Second
	writeTimeout      = 35 * time.Second
	idleTimeout       = 120 * time.Second
	shutdownTimeout   = 10 * time.Second
)

// Server owns an *http.Server and runs it with graceful shutdown.
type Server struct {
	http   *http.Server
	logger *slog.Logger
}

// New builds a Server bound to addr serving handler.
func New(addr string, handler http.Handler, logger *slog.Logger) *Server {
	return &Server{
		http: &http.Server{
			Addr:              addr,
			Handler:           handler,
			ReadHeaderTimeout: readHeaderTimeout,
			ReadTimeout:       readTimeout,
			WriteTimeout:      writeTimeout,
			IdleTimeout:       idleTimeout,
		},
		logger: logger,
	}
}

// Run serves until ctx is cancelled (e.g. SIGTERM), then drains connections
// within shutdownTimeout. It returns the first fatal error, or nil on a clean
// shutdown.
func (s *Server) Run(ctx context.Context) error {
	errCh := make(chan error, 1)
	go func() {
		s.logger.Info("http server listening", "addr", s.http.Addr)
		if err := s.http.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			errCh <- err
		}
	}()

	select {
	case err := <-errCh:
		return err
	case <-ctx.Done():
		s.logger.Info("shutdown signal received")
		shutdownCtx, cancel := context.WithTimeout(context.Background(), shutdownTimeout)
		defer cancel()
		if err := s.http.Shutdown(shutdownCtx); err != nil {
			return err
		}
		s.logger.Info("http server stopped")
		return nil
	}
}
