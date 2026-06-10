"""CLI for ECMC IOC Generator."""

from __future__ import annotations

import argparse
import sys

from .generators import ESSGenerator
from .scanners import EthercatScanner


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
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument("--ecmc-ver", default="8.0.2", help="ECMC version to use (default: 8.0.2)")

    args = parser.parse_args()

    print(f"Generating ECMC IOC for facility: {args.facility}")

    ioc_generator = ESSGenerator(
        scanner=EthercatScanner(),
        output_file=args.output,
        ecmc_ver=args.ecmc_ver,
        verbose=args.verbose,
    )

    try:
        ioc_generator.generate()
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        print("Usage: ecmc-ioc-gen OR cat slaves.txt | ecmc-ioc-gen", file=sys.stderr)
        sys.exit(1)
