import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


LOG_FORMAT = "[%(asctime)s] [%(levelname)-7s] [%(name)s:%(lineno)d] [%(funcName)s] - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> None:
    """Configures centralized logging with console and rotating file output."""
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    log_level = logging.DEBUG if settings.DEBUG else getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    # 1. Console Handler (Streams directly to docker logs / terminal)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # 2. Rotating File Handler for all application logs (10 MB x 5 backups)
    app_log_file = settings.LOGS_DIR / "app.log"
    file_handler = RotatingFileHandler(
        app_log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # 3. Rotating File Handler for error and critical alerts only
    error_log_file = settings.LOGS_DIR / "errors.log"
    error_file_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers on reloads
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_file_handler)

    # Quieten overly noisy third-party libraries unless debug
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = True
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Convenience helper to retrieve namespaced logger."""
    return logging.getLogger(name)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs incoming HTTP requests, duration in milliseconds, and status codes."""

    def __init__(self, app):
        super().__init__(app)
        self.logger = logging.getLogger("app.api.access")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        query = str(request.url.query)
        full_path = f"{path}?{query}" if query else path

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            log_msg = f"{client_ip} - \"{method} {full_path}\" {response.status_code} ({duration_ms:.1f}ms)"
            if response.status_code >= 500:
                self.logger.error(log_msg)
            elif response.status_code >= 400:
                self.logger.warning(log_msg)
            else:
                self.logger.info(log_msg)

            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            self.logger.error(
                f"{client_ip} - \"{method} {full_path}\" FAILED after {duration_ms:.1f}ms: {exc}",
                exc_info=True,
            )
            raise

