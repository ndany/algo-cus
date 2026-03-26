"""
Supabase authentication module.

Handles Google OAuth flow and invitation code validation.
Requires environment variables:
    SUPABASE_URL      — Your Supabase project URL
    SUPABASE_KEY      — Your Supabase anon/public key
"""

import os
import logging
from functools import wraps

from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Supabase client (initialized lazily)
_client: Client | None = None


def get_supabase() -> Client:
    """Get or create the Supabase client."""
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY environment variables are required. "
                "Get these from your Supabase project settings."
            )
        _client = create_client(url, key)
    return _client


def get_google_login_url(redirect_to: str) -> str:
    """Generate the Google OAuth login URL via Supabase.

    Args:
        redirect_to: URL to redirect to after successful auth.

    Returns:
        The OAuth URL to redirect the user to.
    """
    sb = get_supabase()
    response = sb.auth.sign_in_with_oauth({
        "provider": "google",
        "options": {"redirect_to": redirect_to},
    })
    return response.url


def get_user_from_token(access_token: str) -> dict | None:
    """Validate an access token and return the user info.

    Returns:
        Dict with user info (id, email, name) or None if invalid.
    """
    try:
        sb = get_supabase()
        response = sb.auth.get_user(access_token)
        if response and response.user:
            user = response.user
            return {
                "id": user.id,
                "email": user.email,
                "name": user.user_metadata.get("full_name", user.email),
                "avatar": user.user_metadata.get("avatar_url", ""),
            }
    except Exception as e:
        logger.warning(f"Token validation failed: {e}")
    return None


def validate_invitation_code(code: str) -> bool:
    """Check if an invitation code is valid and unused.

    Expects a Supabase table 'invitation_codes' with columns:
        code (text, unique), used (boolean), used_by (text, nullable)
    """
    try:
        sb = get_supabase()
        result = (
            sb.table("invitation_codes")
            .select("code, used")
            .eq("code", code)
            .eq("used", False)
            .execute()
        )
        return len(result.data) > 0
    except Exception as e:
        logger.error(f"Invitation code check failed: {e}")
        return False


def consume_invitation_code(code: str, user_email: str) -> bool:
    """Mark an invitation code as used.

    Returns True if successful.
    """
    try:
        sb = get_supabase()
        sb.table("invitation_codes").update({
            "used": True,
            "used_by": user_email,
        }).eq("code", code).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to consume invitation code: {e}")
        return False


def register_authorized_user(user_id: str, email: str, name: str) -> bool:
    """Add a user to the authorized_users table after invitation code validation.

    Expects a Supabase table 'authorized_users' with columns:
        user_id (text, primary key), email (text), name (text)
    """
    try:
        sb = get_supabase()
        sb.table("authorized_users").upsert({
            "user_id": user_id,
            "email": email,
            "name": name,
        }).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to register user: {e}")
        return False


def is_user_authorized(user_id: str) -> bool:
    """Check if a user has already been authorized (used a valid invitation code)."""
    try:
        sb = get_supabase()
        result = (
            sb.table("authorized_users")
            .select("user_id")
            .eq("user_id", user_id)
            .execute()
        )
        return len(result.data) > 0
    except Exception as e:
        logger.error(f"Authorization check failed: {e}")
        return False
