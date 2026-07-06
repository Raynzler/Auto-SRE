// Package config loads daemon configuration from a YAML file with environment
// variable overrides. Adding new target types or fields here requires no change
// to the prober, so future dependency/external-API monitoring drops in cleanly.
package config

import (
	"os"
	"time"

	"gopkg.in/yaml.v3"
)

// Target describes one thing to probe. Any subset of checks runs depending on
// which fields are set: DNS+TCP need Host(+Port); HTTP needs the URL.
type Target struct {
	Name string `yaml:"name"`
	Host string `yaml:"host"`
	Port int    `yaml:"port"`
	HTTP string `yaml:"http"`
}

// Config is the resolved, typed configuration used by the daemon.
type Config struct {
	ListenAddr   string
	PollInterval time.Duration
	Timeout      time.Duration
	Targets      []Target
}

// rawConfig mirrors the on-disk YAML (durations as strings) before conversion.
type rawConfig struct {
	ListenAddr   string   `yaml:"listen_addr"`
	PollInterval string   `yaml:"poll_interval"`
	Timeout      string   `yaml:"timeout"`
	Targets      []Target `yaml:"targets"`
}

// Load reads the YAML config (path from NETD_CONFIG, default "config.yaml"),
// then applies environment overrides which take precedence over the file.
func Load() (*Config, error) {
	raw := rawConfig{
		ListenAddr:   ":2112",
		PollInterval: "15s",
		Timeout:      "5s",
	}

	path := getenv("NETD_CONFIG", "config.yaml")
	data, err := os.ReadFile(path)
	switch {
	case err == nil:
		if err := yaml.Unmarshal(data, &raw); err != nil {
			return nil, err
		}
	case !os.IsNotExist(err):
		return nil, err
	}

	raw.ListenAddr = getenv("NETD_LISTEN_ADDR", raw.ListenAddr)
	raw.PollInterval = getenv("NETD_POLL_INTERVAL", raw.PollInterval)
	raw.Timeout = getenv("NETD_TIMEOUT", raw.Timeout)

	interval, err := time.ParseDuration(raw.PollInterval)
	if err != nil {
		return nil, err
	}
	timeout, err := time.ParseDuration(raw.Timeout)
	if err != nil {
		return nil, err
	}

	return &Config{
		ListenAddr:   raw.ListenAddr,
		PollInterval: interval,
		Timeout:      timeout,
		Targets:      raw.Targets,
	}, nil
}

func getenv(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}
