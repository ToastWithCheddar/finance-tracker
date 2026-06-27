"""Structlog configuration for the finance-tracker ml-worker.

Configures JSON-formatted structured logging with correlation IDs, log-level
control via ``LOG_LEVEL``, and consistent processors across the worker.
See ``docs/runbooks/observability-stack.md`` for the deployment story.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any

import structlog


def _is_dev() -> bool:
    return os.getenv("ENVIRONMENT", "development").lower() == "development"


def configure_logging(service: str) -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = logging.getLevelNamesMapping().get(level_name, logging.INFO)

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        timestamper,
    ]

    if _is_dev():
        renderer: Any = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(handler)
    root.setLevel(level)

    structlog.contextvars.bind_contextvars(service=service)


def get_logger(name: str | None = None) -> Any:
    return structlog.get_logger(name) if name else structlog.get_logger()


def bind_request_id(request_id: str) -> None:
    structlog.contextvars.bind_contextvars(request_id=request_id)


def unbind_request_id() -> None:
    structlog.contextvars.unbind_contextvars("request_id")
