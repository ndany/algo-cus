"""
Fire-and-forget usage telemetry.

Logs user actions and access attempts to Supabase tables.
All functions swallow errors — telemetry must never block the user.
"""

import logging

logger = logging.getLogger(__name__)

# Valid action values for usage_log
ACTIONS = {"login", "analyze", "analyze_error"}

# Valid attempt_type values for access_attempts
ATTEMPT_TYPES = {"no_code", "invalid_code", "auth_failed"}


def _get_client():
    """Get Supabase client, or None if unavailable."""
    try:
        from dashboard.auth import get_supabase
        return get_supabase()
    except Exception:
        return None


def log_usage(user_email: str, action: str, *, detail: str = "", user_name: str = ""):
    """Log an authenticated user action (login, analyze, etc.)."""
    try:
        sb = _get_client()
        if sb:
            sb.table("usage_log").insert({
                "user_email": user_email,
                "user_name": user_name,
                "action": action,
                "detail": detail,
            }).execute()
    except Exception as e:
        logger.warning(f"Telemetry log_usage failed: {e}")


def log_access_attempt(email: str, attempt_type: str, *, name: str = "", code_provided: str = ""):
    """Log a rejected access attempt (no code, invalid code, auth failure)."""
    try:
        sb = _get_client()
        if sb:
            sb.table("access_attempts").insert({
                "email": email,
                "name": name,
                "attempt_type": attempt_type,
                "code_provided": code_provided or None,
            }).execute()
    except Exception as e:
        logger.warning(f"Telemetry log_access_attempt failed: {e}")
