// Package config provides strongly-typed configuration for AutoSRE services,
// loaded from environment variables with an optional YAML file overlay and
// fail-fast validation. Env values take precedence over the file.
//
//   - ServiceConfig — the HTTP services (api, auth, worker).
//   - NetworkConfig — the network-daemon.
package config

import (
	"errors"
	"fmt"
	"os"
	"strconv"
	"time"

	"gopkg.in/yaml.v3"
)

// env is a small helper that reads and parses environment variables, applying
// defaults and accumulating parse errors so all problems surface at once.
type env struct{ errs []error }

func (e *env) str(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func (e *env) int(key string, def int) int {
	v := os.Getenv(key)
	if v == "" {
		return def
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		e.errs = append(e.errs, fmt.Errorf("%s=%q: not a valid integer", key, v))
		return def
	}
	return n
}

func (e *env) float(key string, def float64) float64 {
	v := os.Getenv(key)
	if v == "" {
		return def
	}
	f, err := strconv.ParseFloat(v, 64)
	if err != nil {
		e.errs = append(e.errs, fmt.Errorf("%s=%q: not a valid number", key, v))
		return def
	}
	return f
}

func (e *env) duration(key, def string) time.Duration {
	raw := e.str(key, def)
	d, err := time.ParseDuration(raw)
	if err != nil {
		e.errs = append(e.errs, fmt.Errorf("%s=%q: not a valid duration", key, raw))
		return 0
	}
	return d
}

// err returns a single combined error if any parse failed, else nil.
func (e *env) err() error {
	if len(e.errs) == 0 {
		return nil
	}
	return fmt.Errorf("invalid configuration: %w", errors.Join(e.errs...))
}

// loadYAML overlays a YAML file onto dst if the path is set and the file exists.
func loadYAML(path string, dst any) error {
	if path == "" {
		return nil
	}
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	return yaml.Unmarshal(data, dst)
}

// ServiceConfig is the shared configuration for the HTTP services.
type ServiceConfig struct {
	Service        string  `yaml:"service"`
	ListenAddr     string  `yaml:"listen_addr"`
	FailureLogPath string  `yaml:"failure_log_path"`
	RateLimitRPS   float64 `yaml:"rate_limit_rps"`
	RateLimitBurst float64 `yaml:"rate_limit_burst"`
}

// LoadService builds a ServiceConfig for the named service. Precedence:
// defaults < YAML file ($CONFIG_FILE) < environment variables.
func LoadService(service string, defaultPort int) (*ServiceConfig, error) {
	cfg := &ServiceConfig{
		Service:        service,
		ListenAddr:     fmt.Sprintf(":%d", defaultPort),
		FailureLogPath: "data/failures.jsonl",
		RateLimitRPS:   10,
		RateLimitBurst: 20,
	}
	if err := loadYAML(os.Getenv("CONFIG_FILE"), cfg); err != nil {
		return nil, err
	}

	e := &env{}
	cfg.ListenAddr = fmt.Sprintf(":%d", e.int("PORT", defaultPort))
	cfg.FailureLogPath = e.str("FAILURE_LOG_PATH", cfg.FailureLogPath)
	cfg.RateLimitRPS = e.float("RATE_LIMIT_RPS", cfg.RateLimitRPS)
	cfg.RateLimitBurst = e.float("RATE_LIMIT_BURST", cfg.RateLimitBurst)
	if err := e.err(); err != nil {
		return nil, err
	}
	return cfg, nil
}

// Target describes one thing the network-daemon probes. Any subset of checks
// runs depending on which fields are set: DNS+TCP need Host(+Port); HTTP needs
// the URL.
type Target struct {
	Name string `yaml:"name"`
	Host string `yaml:"host"`
	Port int    `yaml:"port"`
	HTTP string `yaml:"http"`
}

// NetworkConfig is the resolved configuration for the network-daemon.
type NetworkConfig struct {
	ListenAddr   string
	PollInterval time.Duration
	Timeout      time.Duration
	Targets      []Target
}

// netFile mirrors the on-disk YAML (durations as strings) before conversion.
type netFile struct {
	ListenAddr   string   `yaml:"listen_addr"`
	PollInterval string   `yaml:"poll_interval"`
	Timeout      string   `yaml:"timeout"`
	Targets      []Target `yaml:"targets"`
}

// LoadNetwork reads the daemon YAML (path from NETD_CONFIG, default
// "config.yaml"), then applies NETD_* environment overrides.
func LoadNetwork() (*NetworkConfig, error) {
	file := netFile{ListenAddr: ":2112", PollInterval: "15s", Timeout: "5s"}
	e := &env{}
	if err := loadYAML(e.str("NETD_CONFIG", "config.yaml"), &file); err != nil {
		return nil, err
	}

	// Env overrides use the file value (or built-in default) as their fallback.
	listen := e.str("NETD_LISTEN_ADDR", file.ListenAddr)
	interval := e.duration("NETD_POLL_INTERVAL", file.PollInterval)
	timeout := e.duration("NETD_TIMEOUT", file.Timeout)
	if err := e.err(); err != nil {
		return nil, err
	}
	return &NetworkConfig{
		ListenAddr:   listen,
		PollInterval: interval,
		Timeout:      timeout,
		Targets:      file.Targets,
	}, nil
}
