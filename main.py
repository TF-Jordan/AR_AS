#!/usr/bin/env python3
"""
Main entry point for the AR_AS RaaS Platform.

Commands:
    python main.py api          - Start FastAPI server
    python main.py init-db      - Initialize database schema
"""

import argparse
import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_api():
    """Start the FastAPI API server."""
    import uvicorn
    from src.config import settings

    logger.info(f"Starting API server on {settings.api_host}:{settings.api_port}")

    uvicorn.run(
        "src.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


def run_init_db():
    """Initialize database tables."""
    from src.database.connection import init_database

    logger.info("Initializing database schema...")
    asyncio.run(init_database())
    logger.info("Database schema initialized successfully")


def main():
    parser = argparse.ArgumentParser(
        description="AR_AS RaaS Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  api           Start the FastAPI server
  init-db       Initialize database schema
        """,
    )

    parser.add_argument(
        "command",
        choices=["api", "init-db"],
        help="Command to execute",
    )

    args = parser.parse_args()

    commands = {
        "api": run_api,
        "init-db": run_init_db,
    }

    commands[args.command]()


if __name__ == "__main__":
    main()
