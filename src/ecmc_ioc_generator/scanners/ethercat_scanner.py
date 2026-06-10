"""Scanner for EtherCAT bus discovery."""

import subprocess
import sys

from .base_scanner import BaseScanner


class EthercatScanner(BaseScanner):
    """Handle hardware discovery from the EtherCAT bus or standard input."""

    def scan(self) -> list[str]:
        """
        Scan the bus or fall back to stdin.

        Ensure the script doesn't hang if no input is provided.
        """
        # 1. Try to run the actual 'ethercat' command
        try:
            output = subprocess.check_output(["ethercat", "slaves"], stderr=subprocess.STDOUT)
            if isinstance(output, bytes):
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
