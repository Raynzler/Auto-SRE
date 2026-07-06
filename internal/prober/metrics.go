// Metrics for the network daemon: a private registry exporting exactly the
// network_* series (plus Go/process metrics). Lives in the prober package
// because the prober is their sole owner and emitter.
package prober

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/collectors"
)

// Metrics holds the network observability collectors and their registry.
type Metrics struct {
	Registry *prometheus.Registry

	Latency        *prometheus.HistogramVec
	Requests       *prometheus.CounterVec
	Failures       *prometheus.CounterVec
	DNSLookup      *prometheus.HistogramVec
	TCPConnections *prometheus.CounterVec
	Timeouts       *prometheus.CounterVec
}

// NewMetrics builds the collectors and registers them on a dedicated registry.
func NewMetrics() *Metrics {
	reg := prometheus.NewRegistry()

	m := &Metrics{
		Registry: reg,
		Latency: prometheus.NewHistogramVec(prometheus.HistogramOpts{
			Name:    "network_latency_seconds",
			Help:    "Latency of network checks in seconds.",
			Buckets: prometheus.DefBuckets,
		}, []string{"target", "check"}),
		Requests: prometheus.NewCounterVec(prometheus.CounterOpts{
			Name: "network_requests_total",
			Help: "Total network checks performed.",
		}, []string{"target", "check"}),
		Failures: prometheus.NewCounterVec(prometheus.CounterOpts{
			Name: "network_failures_total",
			Help: "Total failed network checks.",
		}, []string{"target", "check"}),
		DNSLookup: prometheus.NewHistogramVec(prometheus.HistogramOpts{
			Name:    "network_dns_lookup_seconds",
			Help:    "DNS resolution time in seconds.",
			Buckets: prometheus.DefBuckets,
		}, []string{"target"}),
		TCPConnections: prometheus.NewCounterVec(prometheus.CounterOpts{
			Name: "network_tcp_connections_total",
			Help: "Total TCP connection attempts.",
		}, []string{"target"}),
		Timeouts: prometheus.NewCounterVec(prometheus.CounterOpts{
			Name: "network_timeouts_total",
			Help: "Total network checks that timed out.",
		}, []string{"target", "check"}),
	}

	reg.MustRegister(
		m.Latency,
		m.Requests,
		m.Failures,
		m.DNSLookup,
		m.TCPConnections,
		m.Timeouts,
		collectors.NewGoCollector(),
		collectors.NewProcessCollector(collectors.ProcessCollectorOpts{}),
	)

	return m
}
