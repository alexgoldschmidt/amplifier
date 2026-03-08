"""CLI entrypoint for the ADO Event Monitor."""

import argparse
import asyncio
import contextlib
import logging
import sys
from pathlib import Path

from .monitor import run_monitor


def main() -> None:
    """Main CLI entrypoint.

    Authentication is via Azure CLI. Run `az login` before starting the monitor.
    """
    parser = argparse.ArgumentParser(
        description="ADO Event Monitor - Autonomous event detection for Azure DevOps"
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=Path("subscriptions.yaml"),
        help="Path to subscriptions.yaml config file",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to SQLite database (default: ado_monitor.db)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Validate config file exists
    if not args.config.exists():
        print(f"Error: Config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    # Run the monitor
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(run_monitor(args.config, args.db))


if __name__ == "__main__":
    main()
