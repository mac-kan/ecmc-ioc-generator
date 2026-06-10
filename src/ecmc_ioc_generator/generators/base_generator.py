"""Base class for ECMC IOC generators."""

import contextlib
import sys
from abc import ABC, abstractmethod

from ecmc_ioc_generator.scanners import BaseScanner


class BaseGenerator(ABC):
    """Base class for ECMC IOC generators."""

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
        self.lines = []

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
    def _process_slaves(self, stream) -> None:
        """Process the scanned lines and generate IOC configuration."""

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
