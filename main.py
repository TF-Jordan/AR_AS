#!/usr/bin/env python3
"""
Main entry point for the RaaS Multi-Tenant Platform.
"""

import argparse

from src.logging_config import configure_logging


def run_api():
    """Start the FastAPI server."""
    import uvicorn
    from src.config import settings

    uvicorn.run(
        "src.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


def init_db():
    """Initialize database tables."""
    import asyncio
    from src.database.connection import init_database

    asyncio.run(init_database())
    print("Database initialized successfully")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="RaaS Multi-Tenant Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  api       Start the FastAPI server
  init-db   Initialize database tables

Examples:
  python main.py api
  python main.py init-db
        """,
    )

    parser.add_argument(
        "command",
        choices=["api", "init-db"],
        help="Command to run",
    )

    args = parser.parse_args()

    # Configure logging
    configure_logging()

    # Run command
    if args.command == "api":
        run_api()
    elif args.command == "init-db":
        init_db()


if __name__ == "__main__":
    main()
