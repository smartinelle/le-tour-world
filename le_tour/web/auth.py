"""Authentication middleware and utilities for NiceGUI.

This module provides:
- AuthManager: Core authentication state management
- require_auth: Decorator for protected routes
- Login/logout functionality via Supabase Auth
"""

import asyncio
import logging
from typing import Optional, Callable, Any
from functools import wraps

from nicegui import app, ui

from ..supabase_client import get_supabase, get_supabase_config, is_supabase_configured

logger = logging.getLogger(__name__)


class AuthManager:
    """Manages authentication state for NiceGUI sessions.

    Uses NiceGUI's app.storage.user for per-session state persistence.
    Integrates with Supabase Auth for Google OAuth.
    """

    @staticmethod
    def get_current_user() -> Optional[dict]:
        """Get current authenticated user from session.

        Returns:
            User dict with id, email, name, avatar_url, or None if not authenticated
        """
        return app.storage.user.get("user")

    @staticmethod
    def get_user_id() -> Optional[str]:
        """Get current user's ID.

        Returns:
            User UUID string or None
        """
        user = AuthManager.get_current_user()
        return user.get("id") if user else None

    @staticmethod
    def get_access_token() -> Optional[str]:
        """Get current access token for API calls."""
        return app.storage.user.get("access_token")

    @staticmethod
    def is_authenticated() -> bool:
        """Check if user is authenticated."""
        return AuthManager.get_current_user() is not None

    @staticmethod
    def get_login_url() -> str:
        """Get the Google OAuth login URL.

        Returns:
            URL to redirect user to for Google login
        """
        if not is_supabase_configured():
            raise ValueError("Supabase not configured")

        config = get_supabase_config()
        supabase = get_supabase()

        # Build callback URL
        callback_url = f"{config.app_url}/auth/callback"

        # Get OAuth URL from Supabase
        response = supabase.auth.sign_in_with_oauth(
            {"provider": "google", "options": {"redirect_to": callback_url}}
        )

        return response.url

    @staticmethod
    async def handle_oauth_callback(access_token: str, refresh_token: str) -> bool:
        """Handle OAuth callback and establish session.

        Args:
            access_token: JWT access token from OAuth flow
            refresh_token: Refresh token for maintaining session

        Returns:
            True if login successful, False otherwise
        """
        try:
            supabase = get_supabase()

            # Set the session in Supabase client
            supabase.auth.set_session(access_token, refresh_token)

            # Get user details
            user_response = supabase.auth.get_user(access_token)

            if user_response and user_response.user:
                user = user_response.user

                # Store user info in NiceGUI session
                app.storage.user["user"] = {
                    "id": user.id,
                    "email": user.email,
                    "name": user.user_metadata.get("full_name", user.email),
                    "avatar_url": user.user_metadata.get("avatar_url", ""),
                }
                app.storage.user["access_token"] = access_token
                app.storage.user["refresh_token"] = refresh_token

                logger.info(f"User authenticated: {user.email}")
                return True
            else:
                logger.warning("OAuth callback: no user in response")
                return False

        except Exception as e:
            logger.error(f"OAuth callback failed: {e}")
            return False

    @staticmethod
    async def logout() -> None:
        """Log out current user and clear session."""
        try:
            if is_supabase_configured():
                supabase = get_supabase()
                supabase.auth.sign_out()
        except Exception as e:
            logger.warning(f"Supabase sign out error (continuing): {e}")

        # Clear local session
        user = AuthManager.get_current_user()
        if user:
            logger.info(f"User logged out: {user.get('email', 'unknown')}")

        app.storage.user.clear()

    @staticmethod
    async def refresh_session() -> bool:
        """Refresh the current session using refresh token.

        Returns:
            True if refresh successful, False otherwise
        """
        refresh_token = app.storage.user.get("refresh_token")
        if not refresh_token:
            return False

        try:
            supabase = get_supabase()
            response = supabase.auth.refresh_session(refresh_token)

            if response and response.session:
                app.storage.user["access_token"] = response.session.access_token
                app.storage.user["refresh_token"] = response.session.refresh_token
                return True

        except Exception as e:
            logger.error(f"Session refresh failed: {e}")

        return False


def require_auth(func: Callable) -> Callable:
    """Decorator to require authentication for a page or handler.

    If user is not authenticated, redirects to /login.

    Usage:
        @ui.page("/dashboard")
        @require_auth
        def dashboard_page():
            ...
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not AuthManager.is_authenticated():
            # Store intended destination for post-login redirect
            app.storage.user["redirect_after_login"] = str(
                app.storage.browser.get("path", "/")
            )
            ui.navigate.to("/login")
            return None

        # Check if it's async
        if asyncio.iscoroutinefunction(func):
            return asyncio.create_task(func(*args, **kwargs))
        return func(*args, **kwargs)

    return wrapper


def get_post_login_redirect() -> str:
    """Get the URL to redirect to after successful login.

    Returns:
        URL path, defaults to "/" if none stored
    """
    redirect = app.storage.user.pop("redirect_after_login", None)
    return redirect if redirect else "/"
