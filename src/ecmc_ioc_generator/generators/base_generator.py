"""Base class for ECMC IOC generators."""

import contextlib
import re
import sys
from abc import ABC, abstractmethod

from ecmc_ioc_generator.scanners import BaseScanner


class BaseGenerator(ABC):
    """Base class for ECMC IOC generators."""

    # Regex to match Beckhoff prefixes (EK, EL, EP, EJ, CU, AX)
    HW_REGEX = re.compile(r"\b((E[KLPJ]|CU|AX)\d{4}(?:-\d{4})?)\b")
    # Regex to match the absolute slave index at the start of the line
    INDEX_REGEX = re.compile(r"^(\d+)")
    # Regex to match motion-capable terminals (EL7xxx, ELM7xxx, AX5xxx)
    MOTION_REGEX = re.compile(r"\b(EL7\d{3}|ELM7\d{3}|AX5\d{3})")

    def __init__(
        self,
        scanner: BaseScanner,
        output_file: str | None = None,
        ecmc_ver: str = "8.0.2",
        *,
        verbose: bool = False,
    ) -> None:
        self.scanner = scanner
        self.verbose = verbose
        self.output_file = output_file
        self.ecmc_ver = ecmc_ver
        self.lines: list[str] = []
        self.prefix = ""  # To be set by subclasses
        self.axis_count = 0
        self.slave_index = -1  # Tracks the EtherCAT slave index

    @abstractmethod
    def _print_header(self, stream) -> None:
        """Print common header lines for the IOC."""

    @abstractmethod
    def _print_axis_config(self, stream) -> None:
        """Print axis configuration templates for motion terminals."""

    @abstractmethod
    def _print_footer(self, stream) -> None:
        """Print any necessary footer lines for the IOC."""

    @abstractmethod
    def _add_slave_fn(self, hw_desc: str) -> str:
        """Return the addSlave iocshLoad command string for the given slave."""

    def _process_slaves(self, stream):
        """Match hardware and print addSlave commands."""
        for line in self.lines:
            stripped_line = line.strip()
            print(f"# Processing line: '{stripped_line}'", file=stream)  # Debug print
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

                slave_str = self._add_slave_fn(hw_desc)
                print(slave_str, file=stream)

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
        print(f"# Scanned {len(self.lines)} lines from EtherCAT bus or stdin.", file=sys.stderr)
        with self._get_output_stream() as stream:
            self._print_header(stream)
            self._process_slaves(stream)
            self._print_footer(stream)
