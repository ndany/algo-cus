"""Tests for reporting module."""

import pytest


class TestReportingModule:
    def test_module_imports(self):
        import dashboard.reporting as r
        assert hasattr(r, "get_active_users")
        assert hasattr(r, "get_top_tickers")
        assert hasattr(r, "get_expressed_interest")
        assert hasattr(r, "get_login_frequency")

    def test_functions_return_lists(self):
        """Reporting functions return lists (empty or with data)."""
        from dashboard.reporting import (
            get_active_users, get_top_tickers,
            get_expressed_interest, get_login_frequency,
        )
        assert isinstance(get_active_users(), list)
        assert isinstance(get_top_tickers(), list)
        assert isinstance(get_expressed_interest(), list)
        assert isinstance(get_login_frequency(), list)
