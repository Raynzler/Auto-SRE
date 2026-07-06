// Package prober orchestrates periodic network checks against configured
// targets and records the results as Prometheus metrics. It only observes —
// it never restarts, reroutes, or otherwise remediates a failing dependency.
package prober

import (
	"context"
	"log/slog"
	"net"
	"net/http"
	"strconv"
	"time"

	"github.com/Raynzler/Auto-SRE/internal/config"
	"github.com/Raynzler/Auto-SRE/pkg/netcheck"
)

// Prober runs the check loop for all targets.
type Prober struct {
	cfg      *config.Config
	metrics  *Metrics
	logger   *slog.Logger
	client   *http.Client
	resolver *net.Resolver
}

// New constructs a Prober.
func New(cfg *config.Config, m *Metrics, logger *slog.Logger) *Prober {
	return &Prober{
		cfg:      cfg,
		metrics:  m,
		logger:   logger,
		client:   &http.Client{Timeout: cfg.Timeout},
		resolver: &net.Resolver{},
	}
}

// Run probes every target immediately, then on each tick until ctx is done.
func (p *Prober) Run(ctx context.Context) {
	ticker := time.NewTicker(p.cfg.PollInterval)
	defer ticker.Stop()

	p.logger.Info("prober started",
		"interval", p.cfg.PollInterval.String(), "targets", len(p.cfg.Targets))

	p.probeAll(ctx)
	for {
		select {
		case <-ctx.Done():
			p.logger.Info("prober stopping")
			return
		case <-ticker.C:
			p.probeAll(ctx)
		}
	}
}

func (p *Prober) probeAll(ctx context.Context) {
	for _, t := range p.cfg.Targets {
		p.probeTarget(ctx, t)
	}
}

// probeTarget runs whichever checks the target's fields enable. Note on packet
// loss: true ICMP loss needs raw sockets (CAP_NET_RAW), which a default
// container lacks, so loss is surfaced indirectly via network_failures_total /
// network_requests_total rather than ICMP probing.
func (p *Prober) probeTarget(ctx context.Context, t config.Target) {
	cctx, cancel := context.WithTimeout(ctx, p.cfg.Timeout)
	defer cancel()

	if t.Host != "" {
		r := netcheck.DNSLookup(cctx, p.resolver, t.Host)
		p.record(t.Name, "dns", r)
		p.metrics.DNSLookup.WithLabelValues(t.Name).Observe(r.Latency.Seconds())
	}

	if t.Host != "" && t.Port > 0 {
		addr := net.JoinHostPort(t.Host, strconv.Itoa(t.Port))
		r := netcheck.TCPConnect(cctx, addr, p.cfg.Timeout)
		p.metrics.TCPConnections.WithLabelValues(t.Name).Inc()
		p.record(t.Name, "tcp", r)
	}

	if t.HTTP != "" {
		r, code := netcheck.HTTPCheck(cctx, p.client, t.HTTP)
		p.record(t.Name, "http", r)
		p.logger.Debug("http check",
			"target", t.Name, "status", code, "latency_ms", r.Latency.Milliseconds())
	}
}

func (p *Prober) record(target, check string, r netcheck.Result) {
	p.metrics.Requests.WithLabelValues(target, check).Inc()
	p.metrics.Latency.WithLabelValues(target, check).Observe(r.Latency.Seconds())

	if r.TimedOut {
		p.metrics.Timeouts.WithLabelValues(target, check).Inc()
	}
	if r.Err != nil {
		p.metrics.Failures.WithLabelValues(target, check).Inc()
		p.logger.Warn("check failed",
			"target", target, "check", check,
			"err", r.Err.Error(), "timed_out", r.TimedOut)
	}
}
