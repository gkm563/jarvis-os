"""
Main Entry Point & System Launcher for JARVIS OS.
Bootstraps environment, logger, security vault, database migrations, and API microservice.
"""

import sys
import uvicorn
from jarvis.config.settings import settings
from jarvis.utils.logger import get_logger
from jarvis.api.server import app

logger = get_logger("Main")


def main():
    """Application lifecycle launcher."""
    print("================================================================")
    print("                     STARTING JARVIS OS                         ")
    print("        Enterprise AI Desktop Operating Layer v1.0.0            ")
    print("================================================================")
    logger.info(f"Bootstrapping {settings.APP_NAME} in environment '{settings.APP_ENV}'")
    logger.info(f"API Server listening at http://{settings.HOST}:{settings.PORT}")

    uvicorn.run(
        "jarvis.api.server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
