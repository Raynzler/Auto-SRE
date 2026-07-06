// Package netcheck provides stateless, reusable network probe primitives
// (DNS, TCP, HTTP). It has no dependency on the daemon's config or metrics, so
// it can be reused by other services or tools unchanged.
package netcheck

import (
	"context"
	"errors"
	"fmt"
	"net"
	"net/http"
	"os"
	"time"
)

// Result captures the outcome of a single network check.
type Result struct {
	Latency  time.Duration
	TimedOut bool
	Err      error
}

// DNSLookup resolves host and reports how long resolution took.
func DNSLookup(ctx context.Context, resolver *net.Resolver, host string) Result {
	start := time.Now()
	_, err := resolver.LookupHost(ctx, host)
	return newResult(start, err)
}

// TCPConnect dials addr ("host:port") and reports the connect latency.
func TCPConnect(ctx context.Context, addr string, timeout time.Duration) Result {
	start := time.Now()
	d := net.Dialer{Timeout: timeout}
	conn, err := d.DialContext(ctx, "tcp", addr)
	if conn != nil {
		_ = conn.Close()
	}
	return newResult(start, err)
}

// HTTPCheck performs a GET and treats a >=400 status as a failure. It returns
// the result and the observed status code (0 if the request never completed).
func HTTPCheck(ctx context.Context, client *http.Client, url string) (Result, int) {
	start := time.Now()
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return Result{Latency: time.Since(start), Err: err}, 0
	}
	resp, err := client.Do(req)
	if err != nil {
		return newResult(start, err), 0
	}
	defer resp.Body.Close()

	res := newResult(start, nil)
	if resp.StatusCode >= 400 {
		res.Err = fmt.Errorf("unhealthy status: %s", resp.Status)
	}
	return res, resp.StatusCode
}

func newResult(start time.Time, err error) Result {
	return Result{
		Latency:  time.Since(start),
		Err:      err,
		TimedOut: err != nil && isTimeout(err),
	}
}

func isTimeout(err error) bool {
	var ne net.Error
	if errors.As(err, &ne) {
		return ne.Timeout()
	}
	return errors.Is(err, context.DeadlineExceeded) || errors.Is(err, os.ErrDeadlineExceeded)
}
