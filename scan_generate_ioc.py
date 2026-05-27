#!/usr/bin/env python
from __future__ import print_function
import sys
import re
import subprocess
import argparse

class EcmcIocGenerator(object):
    """
    Scans the EtherCAT bus and generates an ecmc-compatible IOC startup script.
    """
    def __init__(self, facility='ESS', verbose=False):
        self.facility = facility
        self.verbose = verbose
        self.lines = []
        # Regex to match Beckhoff prefixes (EK, EL, EP, EJ, CU, AX)
        self.hw_regex = re.compile(r'\b((E[KLPJ]|CU|AX)\d{4}(?:-\d{4})?)\b')

    def scan_bus(self):
        """Attempts to scan the bus or falls back to stdin."""
        try:
            output = subprocess.check_output(['ethercat', 'slaves'])
            if type(output) is not str:
                output = output.decode('utf-8', errors='ignore')
            self.lines = output.splitlines()
        except Exception:
            self.lines = sys.stdin.read().splitlines()

    def print_header(self):
        """Prints the facility-specific header."""
        if self.facility == 'ESS':
            print("require essioc")
            print("require ecmccfg\n")
            print('iocshLoad "${ecmccfg_DIR}/startup.cmd" "ECMC_VER=8.0.1, NAMING=ESSnaming"\n')
        elif self.facility == 'PSI':
            print("require ecmccfg\n")
            print('iocshLoad "${ecmccfg_DIR}/startup.cmd" "ECMC_VER=8.0.1"\n')

    def process_slaves(self):
        """Matches hardware and prints addSlave commands."""
        for line in self.lines:
            if not line.strip():
                continue

            match = self.hw_regex.search(line)
            if match:
                hw_desc = match.group(1)
                
                if self.verbose:
                    parts = line.split(hw_desc, 1)
                    description = parts[1].strip() if len(parts) > 1 else ""
                    print("# Configure " + hw_desc + " " + description)

                print('iocshLoad "${ecmccfg_DIR}addSlave.cmd" HW_DESC=' + hw_desc)

    def generate(self):
        """Orchestrates the scanning and generation process."""
        self.scan_bus()
        self.print_header()
        self.process_slaves()

def main():
    parser = argparse.ArgumentParser(description='Generate ecmc IOC from EtherCAT bus scan.')
    parser.add_argument('--facility', choices=['ESS', 'PSI'], default='ESS',
                        help='Target facility (default: ESS)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Include descriptive comments in the output')
    args = parser.parse_args()

    generator = EcmcIocGenerator(facility=args.facility, verbose=args.verbose)
    generator.generate()

if __name__ == "__main__":
    main()
