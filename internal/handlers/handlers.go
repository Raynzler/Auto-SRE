// Package handlers implements the AutoSRE service HTTP endpoints. Handlers hold
// no transport concerns (routing, middleware, timeouts) — those live in the
// router, middleware, and server packages.
package handlers

import (
	"encoding/json"
	"net/http"

	"github.com/Raynzler/Auto-SRE/internal/config"
)

// Handlers carries the dependencies the endpoints need.
type Handlers struct {
	cfg *config.ServiceConfig
}

// New builds the handler set for a service.
func New(cfg *config.ServiceConfig) *Handlers {
	return &Handlers{cfg: cfg}
}

// writeJSON writes v as an indented JSON response with the given status.
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

// Health is the liveness probe: 200 while the process is alive.
func (h *Handlers) Health(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"status":  "Healthy",
		"service": h.cfg.Service,
	})
}

// Ready is the readiness probe: is the service fit to serve? For now it is
// always ready; dependency/chaos-driven readiness is layered on in later
// milestones.
func (h *Handlers) Ready(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"status":  "ready",
		"ready":   true,
		"service": h.cfg.Service,
	})
}

// Status is the root endpoint: basic service identity.
func (h *Handlers) Status(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"service": h.cfg.Service,
		"status":  "ok",
	})
}
