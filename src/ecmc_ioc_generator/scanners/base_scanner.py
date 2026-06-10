"""Base scanner for ECMC IOC Generator."""
from abc import ABC, abstractmethod


class BaseScanner(ABC):
    """Base class for all scanners."""

    @abstractmethod
    def scan(self) -> list[str]:
        """Scan method to be implemented by all scanners."""
