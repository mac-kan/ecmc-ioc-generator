#!/usr/bin/env python
import sys
import subprocess

def main():
    """
    Attempts to scan the EtherCAT bus using the 'ethercat' command.
    Falls back to reading from stdin if the command fails.
    """
    try:
        # Execute 'ethercat slaves' to get current bus state
        output = subprocess.check_output(['ethercat', 'slaves'])
        if type(output) is not str:
            output = output.decode('utf-8', errors='ignore')
        lines = output.splitlines()
    except Exception:
        # Use stdin for piped input (e.g., cat slaves.txt | python script.py)
        lines = sys.stdin.read().splitlines()

    for line in lines:
        if line.strip():
            print(line)

if __name__ == "__main__":
    main()
