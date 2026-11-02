"""Entry point: `service serve` (API). Add `worker` / `consume` subcommands as
separate processes.
"""

from __future__ import annotations

import argparse

import uvicorn

from .observability import service_logging as slog
from .settings import get_settings


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="service")
    parser.add_argument("command", choices=["serve"])
    parser.parse_args(argv)
    settings = get_settings()
    # SERVICE_NAME, DEVELOPMENT_ENVIRONMENT|ENV_NAME, NODE_NAME, LOG_LEVEL
    slog.configure_from_env()
    uvicorn.run(
        "service.api.app:create_app",
        factory=True,
        host=settings.http_host,
        port=settings.http_port,
        proxy_headers=True,
        log_config=None,
        timeout_graceful_shutdown=15,
    )


if __name__ == "__main__":
    main()
