package middleware

import (
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func discardLogger() *slog.Logger {
	return slog.New(slog.NewTextHandler(io.Discard, nil))
}

func TestRequestIDGeneratedAndEchoed(t *testing.T) {
	var ctxID string
	next := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ctxID = RequestIDFromContext(r.Context())
		w.WriteHeader(http.StatusOK)
	})
	rr := httptest.NewRecorder()
	RequestID(next).ServeHTTP(rr, httptest.NewRequest(http.MethodGet, "/", nil))

	if ctxID == "" {
		t.Error("request id not in context")
	}
	if rr.Header().Get("X-Request-ID") != ctxID {
		t.Errorf("header %q != ctx %q", rr.Header().Get("X-Request-ID"), ctxID)
	}
}

func TestRequestIDHonoursInbound(t *testing.T) {
	var got string
	next := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		got = RequestIDFromContext(r.Context())
	})
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	req.Header.Set("X-Request-ID", "abc123")
	RequestID(next).ServeHTTP(httptest.NewRecorder(), req)
	if got != "abc123" {
		t.Errorf("got %q, want abc123", got)
	}
}

func TestCorrelationDefaultsToRequestID(t *testing.T) {
	var corr string
	inner := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		corr = CorrelationIDFromContext(r.Context())
	})
	// RequestID must run before CorrelationID for the default to apply.
	h := Chain(inner, RequestID, CorrelationID)
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	req.Header.Set("X-Request-ID", "rid-1")
	h.ServeHTTP(httptest.NewRecorder(), req)
	if corr != "rid-1" {
		t.Errorf("correlation = %q, want rid-1", corr)
	}
}

func TestRecoverConvertsPanicTo500(t *testing.T) {
	next := http.HandlerFunc(func(http.ResponseWriter, *http.Request) {
		panic("boom")
	})
	rr := httptest.NewRecorder()
	Recover(discardLogger())(next).ServeHTTP(rr, httptest.NewRequest(http.MethodGet, "/", nil))
	if rr.Code != http.StatusInternalServerError {
		t.Errorf("status = %d, want 500", rr.Code)
	}
}

func TestTimeoutReturns503(t *testing.T) {
	next := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		time.Sleep(50 * time.Millisecond)
		w.WriteHeader(http.StatusOK)
	})
	rr := httptest.NewRecorder()
	Timeout(10*time.Millisecond)(next).ServeHTTP(rr, httptest.NewRequest(http.MethodGet, "/", nil))
	if rr.Code != http.StatusServiceUnavailable {
		t.Errorf("status = %d, want 503", rr.Code)
	}
}
