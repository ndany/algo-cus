"""Tests for reporting module."""

import pytest


class TestReportingModule:
    def test_module_imports(self):
        import dashboard.reporting as r
        assert hasattr(r, "get_active_users")
        assert hasattr(r, "get_top_tickers")
        assert hasattr(r, "get_expressed_interest")
        assert hasattr(r, "get_login_frequency")

    def test_functions_return_none_without_supabase(self):
        """Reporting functions return None when no DB connection available."""
        from unittest.mock import patch
        from dashboard.reporting import (
            get_active_users, get_top_tickers,
            get_expressed_interest, get_login_frequency,
        )
        with patch("dashboard.reporting._get_client", return_value=None):
            assert get_active_users() is None
            assert get_top_tickers() is None
            assert get_expressed_interest() is None
            assert get_login_frequency() is None
