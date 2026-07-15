package handlers

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"strings"
	"time"
)

// AuthValidator validates a bearer token against the auth service. The api's
// dependency on auth goes through this seam so tests inject fakes and the
// circuit breaker (a later milestone) can wrap the real client transparently.
type AuthValidator interface {
	Validate(ctx context.Context, token string) (bool, error)
}

// simulatedWork mirrors the original implementation's small processing delay.
const simulatedWork = 50 * time.Millisecond

// orderRequest is the strict order payload: unknown fields are rejected and
// values are range-checked, preserving the platform's 422 validation contract.
type orderRequest struct {
	Item     string `json:"item"`
	Quantity int    `json:"quantity"`
}

func (o *orderRequest) validate() error {
	if l := len(o.Item); l < 1 || l > 100 {
		return errors.New("item must be 1-100 characters")
	}
	if o.Quantity < 1 || o.Quantity > 1000 {
		return errors.New("quantity must be between 1 and 1000")
	}
	return nil
}

// CreateOrder handles POST /orders: validate input, validate the caller's
// token against auth, then create the order.
//
// Status contract (preserved from the original service):
//
//	422 invalid body · 401 invalid token · 502 auth unreachable · 200 created
func (h *Handlers) CreateOrder(w http.ResponseWriter, r *http.Request) {
	var req orderRequest
	dec := json.NewDecoder(io.LimitReader(r.Body, 1<<20))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&req); err != nil {
		writeJSON(w, http.StatusUnprocessableEntity, map[string]any{"detail": err.Error()})
		return
	}
	if err := req.validate(); err != nil {
		writeJSON(w, http.StatusUnprocessableEntity, map[string]any{"detail": err.Error()})
		return
	}

	token := strings.TrimSpace(strings.TrimPrefix(r.Header.Get("Authorization"), "Bearer "))
	if token == "" {
		token = "demo-token"
	}

	valid, err := h.auth.Validate(r.Context(), token)
	if err != nil {
		writeJSON(w, http.StatusBadGateway, map[string]any{"detail": "auth dependency unavailable"})
		return
	}
	if !valid {
		writeJSON(w, http.StatusUnauthorized, map[string]any{"detail": "invalid token"})
		return
	}

	// Simulated order processing; abandon quietly if the client went away.
	select {
	case <-time.After(simulatedWork):
	case <-r.Context().Done():
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"order_id": "order_" + shortID(),
		"status":   "created",
		"item":     req.Item,
		"quantity": req.Quantity,
	})
}

// shortID returns an 8-hex-char id (matches the original order_id shape).
func shortID() string {
	var b [4]byte
	_, _ = rand.Read(b[:])
	return hex.EncodeToString(b[:])
}
