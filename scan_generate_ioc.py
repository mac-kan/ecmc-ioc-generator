#!/usr/bin/env python
import sys
import re
import subprocess

def main():
    """
    Scans the EtherCAT bus and generates an ecmc-compatible IOC startup script.

    The script attempts to execute the 'ethercat slaves' command to retrieve the 
    current state of the hardware bus. If the command is unavailable, it falls 
    back to reading from standard input, allowing for processed output to be 
    piped in manually.

    It identifies Beckhoff hardware modules (e.g., EK, EL, EP series) using 
    regular expressions and generates the corresponding 'addSlave.cmd' calls 
    required for an ecmc IOC.
    """
    # Try to run `ethercat slaves` directly.
    try:
        # check_output is compatible with Python 2.7+ and 3.x
        output = subprocess.check_output(['ethercat', 'slaves'])
        # Handle bytes vs string difference in Python 3
        if type(output) is not str:
            output = output.decode('utf-8', errors='ignore')
        lines = output.splitlines()
    except Exception:
        # Fall back to stdin if the command fails or isn't found
        lines = sys.stdin.read().splitlines()

    # Print the header
    print("require essioc")
    print("require ecmccfg\n")
    print('iocshLoad "${ecmccfg_DIR}/startup.cmd" "ECMC_VER=8.0.1, NAMING=ESSnaming"\n')

    # Regex to match Beckhoff prefixes (EK, EL, EP, EJ, CU, AX)
    hw_regex = re.compile(r'\b((E[KLPJ]|CU|AX)\d{4}(?:-\d{4})?)\b')

    for line in lines:
        if not line.strip():
            continue

        match = hw_regex.search(line)
        if match:
            hw_desc = match.group(1)

            # Grab the rest of the line as the description for the comment
            parts = line.split(hw_desc, 1)
            description = parts[1].strip() if len(parts) > 1 else ""

            # Replaced f-strings with universal string concatenation
            print("# Configure " + hw_desc + " " + description)
            print('iocshLoad "${ecmccfg_DIR}addSlave.cmd" HW_DESC=' + hw_desc)

if __name__ == "__main__":
    main()
