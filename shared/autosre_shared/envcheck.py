"""Fail-fast environment validation.

Called at service startup so a malformed config (e.g. PORT="abc") surfaces
immediately with a clear message instead of an obscure failure later.
"""

import os

# Known numeric env vars and their expected type.
_NUMERIC = {
    "PORT": int,
    "RATE_LIMIT_RPS": float,
    "RATE_LIMIT_BURST": float,
    "WORKER_INTERVAL": float,
    "WORKER_JOB_SECONDS": float,
    "AUTH_DEP_LATENCY": float,
}


def validate_env(required: tuple[str, ...] = ()) -> None:
    """Validate the process environment, raising RuntimeError on any problem."""
    problems: list[str] = []

    for name in required:
        if not os.getenv(name):
            problems.append(f"missing required env var: {name}")

    for name, caster in _NUMERIC.items():
        raw = os.getenv(name)
        if raw:
            try:
                caster(raw)
            except ValueError:
                problems.append(f"{name}={raw!r} is not a valid {caster.__name__}")

    if problems:
        raise RuntimeError("environment validation failed: " + "; ".join(problems))
