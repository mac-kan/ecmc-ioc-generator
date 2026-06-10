"""CLI for ECMC IOC Generator."""

from __future__ import annotations

import argparse


def cli():
    """Parse command-line arguments and generate an ECMC IOC."""
    parser = argparse.ArgumentParser(description="Generate ecmc IOC from EtherCAT bus scan.")
    parser.add_argument(
        "--facility",
        type=str.upper,
        choices=["ESS", "PSI"],
        default="ESS",
        help="Target facility for IOC generation (default: ESS)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output with comments describing each step.",
    )
    args = parser.parse_args()

    print(f"Generating ECMC IOC for facility: {args.facility}")
