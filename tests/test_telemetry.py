"""Tests for telemetry module."""

from unittest.mock import patch
import pytest


class TestTelemetryModule:
    def test_module_imports(self):
        import dashboard.telemetry as t
        assert hasattr(t, "log_usage")
        assert hasattr(t, "log_access_attempt")
        assert hasattr(t, "ACTIONS")
        assert hasattr(t, "ATTEMPT_TYPES")

    def test_action_constants_defined(self):
        from dashboard.telemetry import ACTIONS
        assert "login" in ACTIONS
        assert "analyze" in ACTIONS
        assert "analyze_error" in ACTIONS

    def test_attempt_type_constants_defined(self):
        from dashboard.telemetry import ATTEMPT_TYPES
        assert "no_code" in ATTEMPT_TYPES
        assert "invalid_code" in ATTEMPT_TYPES
        assert "auth_failed" in ATTEMPT_TYPES

    @patch("dashboard.telemetry._get_client", return_value=None)
    def test_log_usage_without_supabase_does_not_raise(self, mock_client):
        """Telemetry is fire-and-forget — errors are swallowed."""
        from dashboard.telemetry import log_usage
        log_usage("test@example.com", "login", detail="test", user_name="Test")

    @patch("dashboard.telemetry._get_client", return_value=None)
    def test_log_access_attempt_without_supabase_does_not_raise(self, mock_client):
        from dashboard.telemetry import log_access_attempt
        log_access_attempt("test@example.com", "no_code", name="Test")
