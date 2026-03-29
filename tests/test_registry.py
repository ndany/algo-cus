"""Tests for strategy registry (#30)."""

import pytest

from strategies.base import Strategy
from strategies.registry import StrategyRegistry, DataRequirement, register, registry
from strategies.moving_average_crossover import MovingAverageCrossover
from strategies.rsi_strategy import RSIStrategy
from strategies.bollinger_bands import BollingerBandsStrategy


class TestStrategyRegistry:
    def test_global_registry_has_three_strategies(self):
        """All 3 existing strategies auto-register via @register decorator."""
        classes = registry.get_all()
        assert len(classes) == 3
        names = {cls.__name__ for cls in classes}
        assert names == {"MovingAverageCrossover", "RSIStrategy", "BollingerBandsStrategy"}

    def test_create_all_returns_instances(self):
        instances = registry.create_all()
        assert len(instances) == 3
        for inst in instances:
            assert isinstance(inst, Strategy)

    def test_register_decorator_is_idempotent(self):
        """Re-registering the same class doesn't duplicate it."""
        before = len(registry.get_all())
        register(MovingAverageCrossover)
        assert len(registry.get_all()) == before

    def test_get_compatible_without_filter_returns_all(self):
        """No filter = all strategies."""
        assert len(registry.get_compatible()) == 3

    def test_get_compatible_with_ohlcv_returns_all(self):
        """OHLCV-only strategies need no extra columns."""
        ohlcv = {"Date", "Open", "High", "Low", "Close", "Volume"}
        compatible = registry.get_compatible(ohlcv)
        assert len(compatible) == 3

    def test_create_compatible_returns_instances(self):
        ohlcv = {"Date", "Open", "High", "Low", "Close", "Volume"}
        instances = registry.create_compatible(ohlcv)
        assert len(instances) == 3
        for inst in instances:
            assert isinstance(inst, Strategy)


class TestIsolatedRegistry:
    """Tests using a fresh registry to avoid side effects."""

    def test_empty_registry(self):
        r = StrategyRegistry()
        assert r.get_all() == []
        assert r.create_all() == []

    def test_register_and_retrieve(self):
        r = StrategyRegistry()
        r.register(MovingAverageCrossover)
        assert r.get_all() == [MovingAverageCrossover]

    def test_clear(self):
        r = StrategyRegistry()
        r.register(MovingAverageCrossover)
        r.clear()
        assert r.get_all() == []

    def test_filtering_excludes_incompatible_strategies(self):
        """A strategy requiring fundamentals is excluded when only OHLCV available."""

        class FundamentalStrategy(Strategy):
            @property
            def data_requirement(self):
                return "FUNDAMENTALS"

            @property
            def required_columns(self):
                return ["PERatio", "EBITDA"]

            def generate_signals(self, data):
                return data

        r = StrategyRegistry()
        r.register(MovingAverageCrossover)
        r.register(FundamentalStrategy)

        ohlcv = {"Date", "Open", "High", "Low", "Close", "Volume"}
        compatible = r.get_compatible(ohlcv)
        assert len(compatible) == 1
        assert compatible[0] == MovingAverageCrossover

    def test_filtering_includes_when_columns_available(self):
        """A strategy requiring fundamentals is included when columns are available."""

        class FundamentalStrategy(Strategy):
            @property
            def required_columns(self):
                return ["PERatio"]

            def generate_signals(self, data):
                return data

        r = StrategyRegistry()
        r.register(MovingAverageCrossover)
        r.register(FundamentalStrategy)

        all_cols = {"Date", "Open", "High", "Low", "Close", "Volume", "PERatio"}
        compatible = r.get_compatible(all_cols)
        assert len(compatible) == 2


class TestDataRequirementEnum:
    def test_enum_values(self):
        assert DataRequirement.OHLCV_ONLY.value == "ohlcv_only"
        assert DataRequirement.FUNDAMENTALS.value == "fundamentals"
        assert DataRequirement.MACRO.value == "macro"


class TestBaseClassProperties:
    def test_default_data_requirement(self):
        s = MovingAverageCrossover()
        assert s.data_requirement == "OHLCV_ONLY"

    def test_default_required_columns(self):
        s = RSIStrategy()
        assert s.required_columns == []

    def test_existing_strategies_backward_compatible(self):
        """Existing strategies work unchanged — no modifications needed."""
        for cls in [MovingAverageCrossover, RSIStrategy, BollingerBandsStrategy]:
            s = cls()
            assert s.data_requirement == "OHLCV_ONLY"
            assert s.required_columns == []


class TestAnalysisIntegration:
    def test_get_strategies_uses_registry(self):
        """dashboard.analysis.get_strategies() now returns registry instances."""
        from dashboard.analysis import get_strategies
        strategies = get_strategies()
        assert len(strategies) == 3
        for s in strategies:
            assert isinstance(s, Strategy)
