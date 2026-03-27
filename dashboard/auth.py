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
from supabase.lib.client_options import SyncClientOptions

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
        # Use implicit flow so Supabase returns #access_token in the URL
        # fragment instead of ?code (PKCE). PKCE requires a code_verifier
        # persisted across requests, which doesn't work in stateless Dash callbacks.
        options = SyncClientOptions(flow_type="implicit")
        _client = create_client(url, key, options=options)
    return _client


def get_google_login_url(redirect_to: str) -> str:
    """Generate the Google OAuth login URL via Supabase.

    Constructs the URL directly with response_type=token to force
    implicit flow. The SDK's sign_in_with_oauth may default to PKCE
    regardless of flow_type, and PKCE requires a code_verifier that
    can't be reliably persisted across Dash's stateless callbacks.

    Args:
        redirect_to: URL to redirect to after successful auth.

    Returns:
        The OAuth URL to redirect the user to.
    """
    from urllib.parse import quote
    url = os.environ.get("SUPABASE_URL")
    return (
        f"{url}/auth/v1/authorize"
        f"?provider=google"
        f"&redirect_to={quote(redirect_to)}"
        f"&response_type=token"
    )


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


def validate_invitation_code(code: str, user_identity: str | None = None) -> bool:
    """Check if an invitation code is available for this user.

    A code is valid if:
      - It exists and has never been used (new user), OR
      - It was previously used by the same user_identity (re-login)

    Expects a Supabase table 'invitation_codes' with columns:
        code (text, unique), used (boolean), used_by (text, nullable)
    """
    try:
        sb = get_supabase()
        result = (
            sb.table("invitation_codes")
            .select("code, used, used_by")
            .eq("code", code)
            .execute()
        )
        if not result.data:
            return False
        row = result.data[0]
        # Unused code — available to anyone
        if not row["used"]:
            return True
        # Already used — only the original owner can re-use it
        if user_identity and row.get("used_by") == user_identity:
            return True
        return False
    except Exception as e:
        logger.error(f"Invitation code check failed: {e}")
        return False


def consume_invitation_code(code: str, user_email: str) -> bool:
    """Mark an invitation code as used on first use. No-op on subsequent uses.

    Returns True if successful.
    """
    try:
        sb = get_supabase()
        sb.table("invitation_codes").update({
            "used": True,
            "used_by": user_email,
        }).eq("code", code).eq("used", False).execute()
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
