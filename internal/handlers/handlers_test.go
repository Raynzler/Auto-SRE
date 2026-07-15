package handlers

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/Raynzler/Auto-SRE/internal/config"
)

func decode(t *testing.T, rr *httptest.ResponseRecorder) map[string]any {
	t.Helper()
	var body map[string]any
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
		t.Fatalf("bad json: %v", err)
	}
	return body
}

func TestHealth(t *testing.T) {
	h := New(&config.ServiceConfig{Service: "api"}, nil)
	rr := httptest.NewRecorder()
	h.Health(rr, httptest.NewRequest(http.MethodGet, "/health", nil))
	if rr.Code != http.StatusOK {
		t.Fatalf("status = %d", rr.Code)
	}
	b := decode(t, rr)
	if b["status"] != "Healthy" || b["service"] != "api" {
		t.Errorf("body = %v", b)
	}
}

func TestReady(t *testing.T) {
	h := New(&config.ServiceConfig{Service: "auth"}, nil)
	rr := httptest.NewRecorder()
	h.Ready(rr, httptest.NewRequest(http.MethodGet, "/ready", nil))
	if rr.Code != http.StatusOK {
		t.Fatalf("status = %d", rr.Code)
	}
	b := decode(t, rr)
	if b["ready"] != true || b["service"] != "auth" {
		t.Errorf("body = %v", b)
	}
}

func TestStatus(t *testing.T) {
	h := New(&config.ServiceConfig{Service: "worker"}, nil)
	rr := httptest.NewRecorder()
	h.Status(rr, httptest.NewRequest(http.MethodGet, "/", nil))
	if rr.Code != http.StatusOK {
		t.Fatalf("status = %d", rr.Code)
	}
	b := decode(t, rr)
	if b["service"] != "worker" || b["status"] != "ok" {
		t.Errorf("body = %v", b)
	}
}
