"""
Strategy registry — auto-discovery and filtering by data requirements.

Strategies register themselves via the @register decorator or by
calling registry.register(cls) directly. The registry supports filtering
by available data columns so strategies requiring unavailable data
(e.g., fundamentals) are excluded gracefully.
"""

from enum import Enum

from strategies.base import Strategy


class DataRequirement(Enum):
    """What data a strategy needs beyond basic OHLCV."""
    OHLCV_ONLY = "ohlcv_only"
    FUNDAMENTALS = "fundamentals"
    MACRO = "macro"


class StrategyRegistry:
    """Central registry for strategy classes."""

    def __init__(self):
        self._strategies: list[type[Strategy]] = []

    def register(self, cls: type[Strategy]) -> type[Strategy]:
        """Register a strategy class. Usable as a decorator or direct call."""
        if cls not in self._strategies:
            self._strategies.append(cls)
        return cls

    def get_all(self) -> list[type[Strategy]]:
        """Return all registered strategy classes."""
        return list(self._strategies)

    def get_compatible(self, available_columns: set[str] | None = None) -> list[type[Strategy]]:
        """Return strategies compatible with the available data columns.

        If available_columns is None, returns all strategies (no filtering).
        """
        if available_columns is None:
            return self.get_all()

        compatible = []
        for cls in self._strategies:
            instance = cls.__new__(cls)
            Strategy.__init__(instance)
            required = set(instance.required_columns)

            if required.issubset(available_columns):
                compatible.append(cls)

        return compatible

    def create_all(self, **kwargs) -> list[Strategy]:
        """Instantiate all registered strategies with default params."""
        return [cls() for cls in self._strategies]

    def create_compatible(self, available_columns: set[str] | None = None) -> list[Strategy]:
        """Instantiate strategies compatible with available data."""
        return [cls() for cls in self.get_compatible(available_columns)]

    def clear(self):
        """Remove all registered strategies (for testing)."""
        self._strategies.clear()


# Module-level singleton
registry = StrategyRegistry()
register = registry.register
