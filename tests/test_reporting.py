"""Tests for reporting module."""

import pytest


class TestReportingModule:
    def test_module_imports(self):
        import dashboard.reporting as r
        assert hasattr(r, "get_active_users")
        assert hasattr(r, "get_top_tickers")
        assert hasattr(r, "get_expressed_interest")
        assert hasattr(r, "get_login_frequency")

    def test_functions_return_empty_without_supabase(self):
        """Reporting functions return empty lists without valid credentials."""
        from dashboard.reporting import (
            get_active_users, get_top_tickers,
            get_expressed_interest, get_login_frequency,
        )
        assert get_active_users() == []
        assert get_top_tickers() == []
        assert get_expressed_interest() == []
        assert get_login_frequency() == []
