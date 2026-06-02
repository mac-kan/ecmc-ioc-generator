#!/usr/bin/env python
#
# Copyright (c) 2026, Markus Kristensson, European Spallation Source ERIC
# All rights reserved.
#
# This software is licensed under the BSD 3-Clause License.
# See the LICENSE file in the project root for full license text.
#
"""EtherCAT bus scanner and ecmc IOC generator."""

from __future__ import print_function

import argparse
import contextlib
import re
import subprocess
import sys

__author__ = "Markus Kristensson"
__email__ = "markus.kristensson@ess.eu"


class EthercatScanner(object):
    """Handle hardware discovery from the EtherCAT bus or standard input."""

    def scan(self):
        """
        Scan the bus or fall back to stdin.

        Ensure the script doesn't hang if no input is provided.
        """
        # 1. Try to run the actual 'ethercat' command
        try:
            output = subprocess.check_output(["ethercat", "slaves"], stderr=subprocess.STDOUT)
            if type(output) is not str:
                output = output.decode("utf-8", errors="ignore")
            return output.splitlines()
        except (subprocess.CalledProcessError, OSError):
            # Command failed or was not found
            pass

        # 2. Fall back to stdin only if data is actually being piped in
        if not sys.stdin.isatty():
            return sys.stdin.read().splitlines()

        # No command and no piped input - raise error
        msg = "Error: 'ethercat' command not found and no input piped via stdin."
        raise RuntimeError(msg)


class EcmcIocGenerator(object):
    """Scan the EtherCAT bus and generate an ecmc-compatible IOC startup script."""

    # Regex to match Beckhoff prefixes (EK, EL, EP, EJ, CU, AX)
    HW_REGEX = re.compile(r"\b((E[KLPJ]|CU|AX)\d{4}(?:-\d{4})?)\b")
    # Regex to match the absolute slave index at the start of the line
    INDEX_REGEX = re.compile(r"^(\d+)")
    # Regex to match motion-capable terminals (EL7xxx, ELM7xxx, AX5xxx)
    MOTION_REGEX = re.compile(r"\b(EL7\d{3}|ELM7\d{3}|AX5\d{3})")

    def __init__(self, scanner, facility="ESS", verbose=False, output_file=None, ecmc_ver="8.0.2"):
        self.scanner = scanner
        self.facility = facility
        self.verbose = verbose
        self.output_file = output_file
        self.ecmc_ver = ecmc_ver
        self.lines = []

        # Standard prefix for ecmccfg commands
        if self.facility == "ESS":
            self.prefix = 'iocshLoad "${ecmccfg_DIR}/'
        else:
            self.prefix = "${SCRIPTEXEC} ${ecmccfg_DIR}"
        self.axis_count = 0
        self.slave_index = -1  # Tracks the EtherCAT slave index

    @contextlib.contextmanager
    def _get_output_stream(self):
        """Yield a stream object for writing output (file or stdout)."""
        if self.output_file:
            try:
                with open(self.output_file, "w") as f:
                    yield f
            except IOError as e:
                msg = "Error: Could not open output file '" + self.output_file + "': "
                print(msg + str(e), file=sys.stderr)
                sys.exit(1)
        else:
            yield sys.stdout

    def generate(self):
        """Orchestrate the scanning and generation process."""
        self.lines = self.scanner.scan()
        with self._get_output_stream() as stream:
            self._print_header(stream)
            self._process_slaves(stream)
            self._print_footer(stream)

    def _print_header(self, stream):
        """Print the facility-specific header."""
        if self.facility == "ESS":
            print("require essioc", file=stream)
            print("require ecmccfg\n", file=stream)
            print(
                self.prefix + 'startup.cmd" "ECMC_VER=' + self.ecmc_ver + ', NAMING=ESSnaming"\n',
                file=stream,
            )
        elif self.facility == "PSI":
            print("require ecmccfg\n", file=stream)

    def _print_axis_config(self, stream):
        """Print axis configuration templates for motion terminals."""
        self.axis_count += 1

        if self.facility == "ESS":
            # ESS pattern: explicit SDOs via ecmcConfigOrDie
            print(
                '# ecmcConfigOrDie "Cfg.EcAddSdo(${ECMC_EC_SLAVE_NUM},0x8010,0x1,<TODO>,2)"',
                file=stream,
            )
            print(
                '# ecmcConfigOrDie "Cfg.EcAddSdo(${ECMC_EC_SLAVE_NUM},0x8010,0x2,<TODO>,2)"',
                file=stream,
            )
            print(
                '# ecmcConfigOrDie "Cfg.EcAddSdo(${ECMC_EC_SLAVE_NUM},0x8012,0x3A,<TODO>,1)"',
                file=stream,
            )
        elif self.facility == "PSI":
            # Templates for PSI: applyComponent, loadYamlAxis and loadYamlEnc
            print(
                "# "
                + self.prefix
                + 'applyComponent.cmd "COMP=<TODO_COMPONENT>, '
                + "MACROS='I_MAX_MA=<TODO>, I_STDBY_MA=<TODO>, "
                + "U_NOM_MV=<TODO>, R_COIL_MOHM=<TODO>'\"",
                file=stream,
            )
            print(
                "# "
                + self.prefix
                + 'loadYamlAxis.cmd, "FILE=./cfg/axis_'
                + str(self.axis_count)
                + ".yaml, DEV=${IOC}, AX_NAME=M"
                + str(self.axis_count)
                + ", AXIS_ID="
                + str(self.axis_count)
                + ", DRV_SID=${ECMC_EC_SLAVE_NUM}, ENC_SID=<TODO_ENC_SID>, ENC_CH=<TODO>, "
                + 'BO_SID=<TODO_BO_SID>, BO_CH=<TODO>"',
                file=stream,
            )
            print(
                "# "
                + self.prefix
                + 'loadYamlEnc.cmd, "FILE=./cfg/enc_open_loop.yaml, '
                + 'DEV=${IOC}, DRV_SID=${ECMC_EC_SLAVE_NUM}"',
                file=stream,
            )

        print(file=stream)

    def _process_slaves(self, stream):
        """Match hardware and print addSlave commands."""
        for line in self.lines:
            stripped_line = line.strip()
            if not stripped_line:
                continue

            # Update the absolute slave index from the start of the line
            index_match = self.INDEX_REGEX.search(stripped_line)
            if index_match:
                self.slave_index = int(index_match.group(1))

            match = self.HW_REGEX.search(stripped_line)
            if match:
                hw_desc = match.group(1)

                # Add a blank line before bus couplers (EK) to group segments,
                # except for the very first slave.
                if hw_desc.startswith("EK") and self.slave_index > 0:
                    print(file=stream)

                # Grab the rest of the line as the description
                parts = stripped_line.split(hw_desc, 1)
                description = parts[1].strip() if len(parts) > 1 else ""

                if self.verbose:
                    print("# Configure " + hw_desc + " " + description, file=stream)

                if self.facility == "ESS":
                    print(self.prefix + 'addSlave.cmd" HW_DESC=' + hw_desc, file=stream)
                else:
                    # PSI style: comma and different quoting
                    print(self.prefix + 'addSlave.cmd, "HW_DESC=' + hw_desc + '"', file=stream)

                # Check if this hardware is a known motion terminal
                if self.MOTION_REGEX.search(hw_desc):
                    self._print_axis_config(stream)
            elif index_match:
                # Hardware not recognized, but we must account for it to preserve indexing
                print(
                    "# Skip unknown hardware at index "
                    + str(self.slave_index)
                    + ": "
                    + stripped_line,
                    file=stream,
                )
                print(self.prefix + 'addSlave.cmd" HW_DESC=SKIP', file=stream)

    def _print_footer(self, stream):
        """Print the facility-specific footer."""
        if self.facility == "ESS":
            print("\n" + self.prefix + 'applyConfig.cmd"', file=stream)
            print(self.prefix + 'setAppMode.cmd"', file=stream)
            print("iocInit", file=stream)
        elif self.facility == "PSI":
            # PSI often handles initialization differently or within finalize.cmd
            # Provide a trailing newline for cleanliness
            pass

        # Single blank line at EOF
        print(file=stream)


def main():
    """Parse command-line arguments and generate an ECMC IOC."""
    parser = argparse.ArgumentParser(description="Generate ecmc IOC from EtherCAT bus scan.")
    parser.add_argument(
        "--facility",
        type=str.upper,
        choices=["ESS", "PSI"],
        default="ESS",
        help="Target facility (default: ESS)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Include descriptive comments in the output"
    )
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument("--ecmc-ver", default="8.0.2", help="ECMC version to use (default: 8.0.2)")
    args = parser.parse_args()

    ethercat_scanner = EthercatScanner()
    ioc_generator = EcmcIocGenerator(
        scanner=ethercat_scanner,
        facility=args.facility,
        verbose=args.verbose,
        output_file=args.output,
        ecmc_ver=args.ecmc_ver,
    )

    try:
        ioc_generator.generate()
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        print("Usage: ecmc-ioc-gen OR cat slaves.txt | ecmc-ioc-gen", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
