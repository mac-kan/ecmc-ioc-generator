#!/usr/bin/env python
"""EtherCAT bus scanner and ecmc IOC generator."""
from __future__ import print_function
import sys
import re
import subprocess
import argparse
import contextlib

__author__ = "Markus Kristensson"
__email__ = "markus.kristensson@ess.eu"


class EcmcIocGenerator(object):
    """Scan the EtherCAT bus and generate an ecmc-compatible IOC startup script."""
    def __init__(self, facility='ESS', verbose=False, output_file=None):
        self.facility = facility
        self.verbose = verbose
        self.output_file = output_file
        self.lines = []
        # Regex to match Beckhoff prefixes (EK, EL, EP, EJ, CU, AX)
        self.hw_regex = re.compile(r'\b((E[KLPJ]|CU|AX)\d{4}(?:-\d{4})?)\b')
        # Regex to match the absolute slave index at the start of the line
        self.index_regex = re.compile(r'^(\d+)')

        # Mapping of hardware descriptions to potential axis configuration requirements
        self.motion_hw = {
            'EL7031': 'Stepper motor terminal',
            'EL7037': 'Stepper motor terminal',
            'EL7041': 'Stepper motor terminal',
            'EL7047': 'Stepper motor terminal',
            'EL7201': 'Servomotor terminal',
            'EL7211': 'Servomotor terminal',
            'EL7221': 'Servomotor terminal',
            'AX5101': 'Digital Servo Drive',
            'AX5103': 'Digital Servo Drive',
            'AX5203': 'Digital Servo Drive',
        }
        # Standard prefix for ecmccfg commands
        self.prefix = 'iocshLoad "${ecmccfg_DIR}/'
        self.axis_count = 0
        self.slave_index = -1  # Tracks the EtherCAT slave index

    @contextlib.contextmanager
    def _get_output_stream(self):
        """Yield a stream object for writing output (file or stdout)."""
        if self.output_file:
            try:
                with open(self.output_file, 'w') as f:
                    yield f
            except IOError as e:
                print("Error: Could not open output file '" + self.output_file + "': " + str(e), file=sys.stderr)
                sys.exit(1)
        else:
            yield sys.stdout

    def scan_bus(self):
        """
        Scan the bus or fall back to stdin.

        Ensure the script doesn't hang if no input is provided.
        """
        try:
            output = subprocess.check_output(['ethercat', 'slaves'], stderr=subprocess.STDOUT)
            if type(output) is not str:
                output = output.decode('utf-8', errors='ignore')
            self.lines = output.splitlines()
            return
        except (subprocess.CalledProcessError, OSError):
            # Command failed or was not found
            pass

        # Fall back to stdin only if data is actually being piped in
        if not sys.stdin.isatty():
            self.lines = sys.stdin.read().splitlines()
        else:
            # No command and no piped input - print error and exit
            print("Error: 'ethercat' command not found and no input piped via stdin.", file=sys.stderr)
            print("Usage: ecmc-ioc-gen OR cat slaves.txt | ecmc-ioc-gen", file=sys.stderr)
            sys.exit(1)

    def print_header(self, stream):
        """Print the facility-specific header."""
        if self.facility == 'ESS':
            print("require essioc", file=stream)
            print("require ecmccfg\n", file=stream)
            print(self.prefix + 'startup.cmd" "ECMC_VER=8.0.2, NAMING=ESSnaming"\n', file=stream)
        elif self.facility == 'PSI':
            print("require ecmccfg\n", file=stream)

    def process_slaves(self, stream):
        """Match hardware and print addSlave commands."""
        for line in self.lines:
            stripped_line = line.strip()
            if not stripped_line:
                continue

            # Update the absolute slave index from the start of the line
            index_match = self.index_regex.search(stripped_line)
            if index_match:
                self.slave_index = int(index_match.group(1))

            match = self.hw_regex.search(stripped_line)
            if match:
                hw_desc = match.group(1)

                # Add a blank line before bus couplers (EK) to group segments,
                # except for the very first slave.
                if hw_desc.startswith('EK') and self.slave_index > 0:
                    print("", file=stream)

                if self.verbose:
                    parts = stripped_line.split(hw_desc, 1)
                    description = parts[1].strip() if len(parts) > 1 else ""
                    print("# Configure " + hw_desc + " " + description, file=stream)

                print(self.prefix + 'addSlave.cmd" HW_DESC=' + hw_desc, file=stream)

                # Check if this hardware is a known motion terminal
                base_hw = hw_desc.split('-')[0]
                if base_hw in self.motion_hw:
                    self.axis_count += 1

                    if self.verbose:
                        print("# Axis " + str(self.axis_count) + ": " + self.motion_hw[base_hw], file=stream)

                    if self.facility == 'ESS':
                        print('# ' + self.prefix + 'configureAxis.cmd" "AXIS_NO=' + str(self.axis_count) + ', CONFIG=./cfg/axis_' + str(self.axis_count) + '.ax"', file=stream)
                    elif self.facility == 'PSI':
                        print('# ' + self.prefix + 'applyComponent.cmd" "COMP=Motor-Generic-2Phase-Stepper, CH_ID=1, MACROS=\'I_MAX_MA=1000\'"', file=stream)
                        print('# ' + self.prefix + 'loadYamlAxis.cmd" "FILE=cfg/axis_' + str(self.axis_count) + '.yaml, DEV=${DEV}, DRV_SLAVE=' + str(self.slave_index) + ', ENC_SLAVE=' + str(self.slave_index) + ', ENC_CHANNEL=01"', file=stream)
            elif index_match:
                # Hardware not recognized, but we must account for it to preserve indexing
                print("# Skip unknown hardware at index " + str(self.slave_index) + ": " + stripped_line, file=stream)
                print(self.prefix + 'addSlave.cmd" HW_DESC=SKIP', file=stream)
    def print_footer(self, stream):
        """Print the facility-specific footer."""
        if self.facility == 'ESS':
            print('\n' + self.prefix + 'applyConfig.cmd"', file=stream)
            print(self.prefix + 'setAppMode.cmd"\n', file=stream)
            print('iocInit\n', file=stream)
        elif self.facility == 'PSI':
            # PSI often handles initialization differently or within finalize.cmd
            # Provide a trailing newline for cleanliness
            print('', file=stream)

    def generate(self):
        """Orchestrate the scanning and generation process."""
        self.scan_bus()
        with self._get_output_stream() as stream:
            self.print_header(stream)
            self.process_slaves(stream)
            self.print_footer(stream)

def main():
    """Parse command-line arguments and generate an ECMC IOC."""
    parser = argparse.ArgumentParser(description='Generate ecmc IOC from EtherCAT bus scan.')
    parser.add_argument('--facility', type=str.upper, choices=['ESS', 'PSI'], default='ESS',
                        help='Target facility (default: ESS)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Include descriptive comments in the output')
    parser.add_argument('--output', '-o', help='Output file path (default: stdout)')
    args = parser.parse_args()

    generator = EcmcIocGenerator(
        facility=args.facility,
        verbose=args.verbose,
        output_file=args.output
    )
    generator.generate()

if __name__ == "__main__":
    main()
