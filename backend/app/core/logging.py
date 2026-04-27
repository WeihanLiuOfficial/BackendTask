"""Structured logging configuration using structlog.

Configures JSON-formatted structured logging for production observability.
Every log entry includes contextual metadata (request_id, prompt_hash,
cache_hit, latency_ms, token_usage) for debugging and analytics.
"""

import logging
import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog for structured JSON logging.

    Args:
        log_level: The minimum logging verbosity level.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
