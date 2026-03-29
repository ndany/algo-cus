"""
Reporting queries for usage telemetry.

Shared by the dashboard reports page and the CLI report script.
All functions return lists of dicts. Empty list on error.
"""

import logging

logger = logging.getLogger(__name__)


def _get_client():
    """Get Supabase client, or None if unavailable."""
    try:
        from dashboard.auth import get_supabase
        return get_supabase()
    except Exception:
        return None


def get_active_users(days=7):
    """Active users in the last N days — who is using the platform and how much.
    Returns: user_email, user_name, actions (count), last_seen (timestamp)."""
    try:
        sb = _get_client()
        if not sb:
            return []
        result = sb.rpc("get_active_users", {"days_back": days}).execute()
        return result.data or []
    except Exception as e:
        logger.warning(f"Report get_active_users failed: {e}")
        return []


def get_top_tickers(limit=20):
    """Most popular tickers — what are users analyzing and how often.
    Returns: ticker, times (total analyses), unique_users (distinct users)."""
    try:
        sb = _get_client()
        if not sb:
            return []
        result = sb.rpc("get_top_tickers", {"result_limit": limit}).execute()
        return result.data or []
    except Exception as e:
        logger.warning(f"Report get_top_tickers failed: {e}")
        return []


def get_expressed_interest():
    """Unregistered users who tried to access — shows demand/interest.
    Includes both no_code and invalid_code attempts grouped together.
    High attempt count = high interest — these are potential users to invite.
    Returns: email, name, attempt_type, attempts (count), first_attempt, last_attempt."""
    try:
        sb = _get_client()
        if not sb:
            return []
        result = sb.rpc("get_expressed_interest").execute()
        return result.data or []
    except Exception as e:
        logger.warning(f"Report get_expressed_interest failed: {e}")
        return []


def get_login_frequency():
    """How often each user logs in — engagement/retention signal.
    Returns: user_email, user_name, logins (count), first_login, last_login."""
    try:
        sb = _get_client()
        if not sb:
            return []
        result = sb.rpc("get_login_frequency").execute()
        return result.data or []
    except Exception as e:
        logger.warning(f"Report get_login_frequency failed: {e}")
        return []
