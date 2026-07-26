"""
Structured Logging Module for JARVIS OS.
Provides enterprise logging via Loguru with JSON formatting, file sinks, and level controls.
"""

import sys
import os
from pathlib import Path
from loguru import logger

# Ensure logs directory exists
LOGS_DIR = Path(os.getenv("JARVIS_LOG_DIR", "./logs"))
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Remove default logger handler
logger.remove()

# Add Console Sink with colored output
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=os.getenv("LOG_LEVEL", "INFO"),
    colorize=True,
)

# Add File Sink for general application logs
logger.add(
    LOGS_DIR / "jarvis_app.log",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
)

# Add Audit Log Sink specifically for security events
logger.add(
    LOGS_DIR / "security_audit.log",
    filter=lambda record: "audit" in record["extra"],
    rotation="50 MB",
    retention="90 days",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | AUDIT | {message}",
    level="INFO",
)


def get_logger(name: str):
    """
    Returns a contextual logger bound to the provided module name.

    Args:
        name (str): Module or package name.

    Returns:
        logger: Bound Loguru logger instance.
    """
    return logger.bind(module=name)
