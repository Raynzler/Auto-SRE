package config

import (
	"testing"
	"time"
)

func TestLoadServiceDefaults(t *testing.T) {
	cfg, err := LoadService("api", 8000)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfg.Service != "api" || cfg.ListenAddr != ":8000" {
		t.Errorf("got service=%q addr=%q", cfg.Service, cfg.ListenAddr)
	}
	if cfg.RateLimitRPS != 10 || cfg.RateLimitBurst != 20 {
		t.Errorf("got rps=%v burst=%v", cfg.RateLimitRPS, cfg.RateLimitBurst)
	}
}

func TestLoadServiceEnvOverride(t *testing.T) {
	t.Setenv("PORT", "9999")
	t.Setenv("RATE_LIMIT_RPS", "50")
	t.Setenv("FAILURE_LOG_PATH", "/tmp/f.jsonl")
	cfg, err := LoadService("auth", 8001)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfg.ListenAddr != ":9999" {
		t.Errorf("PORT override failed: %q", cfg.ListenAddr)
	}
	if cfg.RateLimitRPS != 50 {
		t.Errorf("RATE_LIMIT_RPS override failed: %v", cfg.RateLimitRPS)
	}
	if cfg.FailureLogPath != "/tmp/f.jsonl" {
		t.Errorf("FAILURE_LOG_PATH override failed: %q", cfg.FailureLogPath)
	}
}

func TestLoadServiceInvalidPort(t *testing.T) {
	t.Setenv("PORT", "not-a-number")
	if _, err := LoadService("api", 8000); err == nil {
		t.Fatal("expected error for invalid PORT, got nil")
	}
}

func TestLoadNetworkDefaults(t *testing.T) {
	cfg, err := LoadNetwork()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfg.ListenAddr != ":2112" {
		t.Errorf("listen addr: %q", cfg.ListenAddr)
	}
	if cfg.PollInterval != 15*time.Second || cfg.Timeout != 5*time.Second {
		t.Errorf("interval=%v timeout=%v", cfg.PollInterval, cfg.Timeout)
	}
}

func TestLoadNetworkEnvOverride(t *testing.T) {
	t.Setenv("NETD_LISTEN_ADDR", ":3000")
	t.Setenv("NETD_POLL_INTERVAL", "30s")
	cfg, err := LoadNetwork()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfg.ListenAddr != ":3000" || cfg.PollInterval != 30*time.Second {
		t.Errorf("got addr=%q interval=%v", cfg.ListenAddr, cfg.PollInterval)
	}
}

func TestLoadNetworkInvalidDuration(t *testing.T) {
	t.Setenv("NETD_TIMEOUT", "not-a-duration")
	if _, err := LoadNetwork(); err == nil {
		t.Fatal("expected error for invalid NETD_TIMEOUT, got nil")
	}
}
