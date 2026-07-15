package handlers

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/Raynzler/Auto-SRE/internal/config"
)

// fakeAuth implements AuthValidator for tests.
type fakeAuth struct {
	valid bool
	err   error
	token string // records the token it was asked to validate
}

func (f *fakeAuth) Validate(_ context.Context, token string) (bool, error) {
	f.token = token
	return f.valid, f.err
}

func postOrder(h *Handlers, body, authz string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(http.MethodPost, "/orders", strings.NewReader(body))
	if authz != "" {
		req.Header.Set("Authorization", authz)
	}
	rr := httptest.NewRecorder()
	h.CreateOrder(rr, req)
	return rr
}

func newOrderHandlers(auth AuthValidator) *Handlers {
	return New(&config.ServiceConfig{Service: "api"}, auth)
}

func TestCreateOrderSuccess(t *testing.T) {
	fa := &fakeAuth{valid: true}
	rr := postOrder(newOrderHandlers(fa), `{"item":"laptop","quantity":1}`, "Bearer tok123")
	if rr.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", rr.Code, rr.Body)
	}
	b := decode(t, rr)
	id, _ := b["order_id"].(string)
	if !strings.HasPrefix(id, "order_") || len(id) != len("order_")+8 {
		t.Errorf("order_id = %q", id)
	}
	if b["status"] != "created" || b["item"] != "laptop" || b["quantity"] != float64(1) {
		t.Errorf("body = %v", b)
	}
	if fa.token != "tok123" {
		t.Errorf("validated token = %q, want tok123", fa.token)
	}
}

func TestCreateOrderDefaultsToken(t *testing.T) {
	fa := &fakeAuth{valid: true}
	if rr := postOrder(newOrderHandlers(fa), `{"item":"x","quantity":1}`, ""); rr.Code != http.StatusOK {
		t.Fatalf("status = %d", rr.Code)
	}
	if fa.token != "demo-token" {
		t.Errorf("token = %q, want demo-token", fa.token)
	}
}

func TestCreateOrderValidation422(t *testing.T) {
	cases := map[string]string{
		"missing item":     `{"quantity":1}`,
		"empty item":       `{"item":"","quantity":1}`,
		"item too long":    `{"item":"` + strings.Repeat("a", 101) + `","quantity":1}`,
		"zero quantity":    `{"item":"x","quantity":0}`,
		"too big quantity": `{"item":"x","quantity":1001}`,
		"unknown field":    `{"item":"x","quantity":1,"evil":true}`,
		"wrong type":       `{"item":"x","quantity":"one"}`,
		"not json":         `not json at all`,
	}
	h := newOrderHandlers(&fakeAuth{valid: true})
	for name, body := range cases {
		if rr := postOrder(h, body, ""); rr.Code != http.StatusUnprocessableEntity {
			t.Errorf("%s: status = %d, want 422", name, rr.Code)
		}
	}
}

func TestCreateOrderInvalidToken401(t *testing.T) {
	rr := postOrder(newOrderHandlers(&fakeAuth{valid: false}), `{"item":"x","quantity":1}`, "Bearer bad")
	if rr.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401", rr.Code)
	}
}

func TestCreateOrderAuthDown502(t *testing.T) {
	fa := &fakeAuth{err: errors.New("connection refused")}
	rr := postOrder(newOrderHandlers(fa), `{"item":"x","quantity":1}`, "")
	if rr.Code != http.StatusBadGateway {
		t.Fatalf("status = %d, want 502", rr.Code)
	}
}
