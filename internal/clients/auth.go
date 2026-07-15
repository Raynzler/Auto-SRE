// Package clients holds typed HTTP clients for cross-service calls. Callers
// depend on small interfaces (e.g. handlers.AuthValidator), so these concrete
// clients can be wrapped (circuit breaker) or replaced (tests) freely.
package clients

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/Raynzler/Auto-SRE/internal/middleware"
)

// Auth calls the auth service's POST /validate endpoint.
type Auth struct {
	baseURL string
	client  *http.Client
}

// NewAuth builds an auth client for the given base URL (e.g. http://auth:8001).
func NewAuth(baseURL string) *Auth {
	return &Auth{
		baseURL: baseURL,
		client:  &http.Client{Timeout: 5 * time.Second},
	}
}

// Validate reports whether token is valid. A transport or non-2xx failure
// returns an error (the dependency is unavailable, not the token invalid).
func (a *Auth) Validate(ctx context.Context, token string) (bool, error) {
	body, err := json.Marshal(map[string]string{"token": token})
	if err != nil {
		return false, err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, a.baseURL+"/validate", bytes.NewReader(body))
	if err != nil {
		return false, err
	}
	req.Header.Set("Content-Type", "application/json")
	// Propagate the correlation ID so the whole request chain shares one id.
	if cid := middleware.CorrelationIDFromContext(ctx); cid != "" {
		req.Header.Set("X-Correlation-ID", cid)
	}

	resp, err := a.client.Do(req)
	if err != nil {
		return false, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return false, fmt.Errorf("auth returned status %d", resp.StatusCode)
	}

	var out struct {
		Valid bool `json:"valid"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return false, err
	}
	return out.Valid, nil
}
