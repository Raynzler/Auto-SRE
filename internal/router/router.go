// Package router wires the service endpoints onto a net/http ServeMux (Go 1.22
// method-aware patterns) and applies the shared middleware chain.
package router

import (
	"log/slog"
	"net/http"
	"time"

	"github.com/prometheus/client_golang/prometheus/promhttp"

	"github.com/Raynzler/Auto-SRE/internal/handlers"
	"github.com/Raynzler/Auto-SRE/internal/middleware"
)

// requestTimeout is the per-request deadline. It is generous enough to allow the
// bounded chaos latency injection (added in a later milestone) without tripping.
const requestTimeout = 30 * time.Second

// New returns the fully-wired HTTP handler for a service.
func New(h *handlers.Handlers, logger *slog.Logger) http.Handler {
	mux := http.NewServeMux()

	// Platform surface. "GET /{$}" matches exactly "/" (not a catch-all).
	mux.HandleFunc("GET /health", h.Health)
	mux.HandleFunc("GET /ready", h.Ready)
	mux.HandleFunc("GET /{$}", h.Status)
	mux.Handle("GET /metrics", promhttp.Handler())

	// Outermost → innermost. Logger sits outside Timeout so timed-out requests
	// are still logged; Recover sits inside Timeout so handler panics are caught.
	return middleware.Chain(mux,
		middleware.RequestID,
		middleware.CorrelationID,
		middleware.Logger(logger),
		middleware.Timeout(requestTimeout),
		middleware.Recover(logger),
	)
}
