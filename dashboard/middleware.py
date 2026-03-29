"""
WSGI middleware for auth and proxy headers.

Dash wraps server.wsgi_app with its own middleware that intercepts ALL
requests and serves the SPA index. Flask before_request and routes never
fire. Auth must be handled at the WSGI layer, outside Dash's middleware.

Unauthenticated users see a plain HTML login page. Authenticated
users pass through to Dash.
"""

import logging

logger = logging.getLogger(__name__)

_INPUT_STYLE = ("width:100%;padding:12px;background:#1a2332;border:1px solid #1e293b;"
                "color:#e2e8f0;border-radius:6px;box-sizing:border-box")
_GOOGLE_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18"'
    ' style="vertical-align:middle;margin-right:10px">'
    '<path fill="#fff" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92'
    'a5.06 5.06 0 0 1-2.2 3.32l3.55 2.76c2.07-1.91 3.29-4.73 3.29-8.09z"/>'
    '<path fill="#fff" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.55-2.76'
    'c-.98.66-2.23 1.06-3.73 1.06-2.87 0-5.3-1.94-6.16-4.54l-3.66 2.84'
    'A11.99 11.99 0 0 0 12 23z"/>'
    '<path fill="#fff" d="M5.84 14.1a7.2 7.2 0 0 1 0-4.2L2.18 7.06'
    'A11.99 11.99 0 0 0 0 12c0 1.94.46 3.77 1.28 5.4l3.66-2.84z"/>'
    '<path fill="#fff" d="M12 4.75c1.62 0 3.06.56 4.21 1.64l3.15-3.15'
    'C17.45 1.09 14.97 0 12 0 7.31 0 3.25 2.7 1.28 6.61l3.66 2.84'
    'c.87-2.6 3.3-4.54 6.16-4.54z"/></svg>')


def _login_page(message=""):
    """Single login page: invitation code (optional) + Google sign-in button."""
    msg_html = (f'<div style="color:#ff4757;font-size:13px;margin-top:12px">{message}</div>'
                if message else "")
    return f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AlgoStation</title>
<link rel="stylesheet" href="/assets/style.css">
<style>body{{background:#0a0e17;margin:0;font-family:'Inter',sans-serif}}</style>
</head><body>
<div class="login-container"><div class="login-card">
<div class="login-title">ALGOSTATION</div>
<div style="color:#94a3b8;font-size:14px;margin-bottom:24px">Trading Analysis Terminal</div>
<form method="POST" action="/auth/login">
<div style="color:#94a3b8;font-size:13px;margin-bottom:8px">
Invitation code <span style="color:#475569">(only required for first-time access)</span></div>
<input name="code" placeholder="XXXX-XXXX-XXXX" maxlength="20"
 style="{_INPUT_STYLE};font-family:'JetBrains Mono',monospace;
 text-transform:uppercase;margin-bottom:16px">
<button type="submit" class="btn-google" style="width:100%;padding:12px;
 border:none;border-radius:6px;cursor:pointer;font-size:14px;font-weight:500;
 display:flex;align-items:center;justify-content:center">
{_GOOGLE_SVG}Sign in with Google</button>
</form>{msg_html}
</div></div>
</body></html>"""


class AuthAndProxyMiddleware:
    """WSGI middleware for auth and proxy headers."""

    def __init__(self, wsgi_app, flask_app, skip_auth, auth_funcs=None):
        self.wsgi_app = wsgi_app
        self.flask_app = flask_app
        self.skip_auth = skip_auth
        self.auth = auth_funcs or {}

    def __call__(self, environ, start_response):
        if environ.get("HTTP_X_FORWARDED_PROTO") == "https":
            environ["wsgi.url_scheme"] = "https"

        if self.skip_auth:
            return self.wsgi_app(environ, start_response)

        path = environ.get("PATH_INFO", "/")

        if path.startswith("/auth/"):
            return self._handle_auth(environ, start_response, path)

        if path.startswith(("/_dash", "/assets/")):
            return self.wsgi_app(environ, start_response)

        with self.flask_app.request_context(environ):
            from flask import session
            if session.get("authenticated"):
                return self.wsgi_app(environ, start_response)

        return self._serve_html(start_response, _login_page())

    def _serve_html(self, start_response, html):
        encoded = html.encode()
        start_response("200 OK", [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(encoded))),
        ])
        return [encoded]

    def _save_session_and_respond(self, environ, start_response, resp):
        from flask import session
        self.flask_app.session_interface.save_session(self.flask_app, session, resp)
        return resp(environ, start_response)

    def _handle_auth(self, environ, start_response, path):
        from werkzeug.wrappers import Request
        req = Request(environ)

        if path == "/auth/login":
            scheme = environ.get("wsgi.url_scheme", "http")
            host = environ.get("HTTP_HOST", "localhost")
            callback_url = f"{scheme}://{host}/auth/callback"
            authorize_url, code_verifier = self.auth["get_google_authorize_url"](callback_url)

            with self.flask_app.request_context(environ):
                from flask import session, redirect as flask_redirect
                session["code_verifier"] = code_verifier
                invite_code = req.form.get("code", "").strip().upper()
                if invite_code:
                    session["invite_code"] = invite_code
                resp = flask_redirect(authorize_url)
                return self._save_session_and_respond(environ, start_response, resp)

        if path == "/auth/callback":
            with self.flask_app.request_context(environ):
                from flask import session, redirect as flask_redirect

                auth_code = req.args.get("code")
                code_verifier = session.pop("code_verifier", None)

                if not auth_code or not code_verifier:
                    logger.warning(f"OAuth callback missing: code={bool(auth_code)}, verifier={bool(code_verifier)}")
                    return self._serve_html(start_response,
                        _login_page("Sign-in failed. Please try again."))

                user = self.auth["exchange_code_for_session"](auth_code, code_verifier)
                if not user:
                    logger.warning("OAuth code exchange failed")
                    self.auth["log_access_attempt"]("", "auth_failed", name="unknown")
                    return self._serve_html(start_response,
                        _login_page("Sign-in failed. Please try again."))

                invite_code = session.pop("invite_code", "")

                if self.auth["is_user_authorized"](user["id"]):
                    db_user = self.auth["get_user_with_role"](user["id"])
                    if db_user:
                        user["role"] = db_user.get("role", "user")
                    session["authenticated"] = True
                    session["user"] = user
                    self.auth["log_usage"](user["email"], "login", user_name=user.get("name", ""))
                    resp = flask_redirect("/")
                    return self._save_session_and_respond(environ, start_response, resp)

                if not invite_code or not self.auth["validate_invitation_code"](invite_code, user_identity=user["email"]):
                    self.auth["log_access_attempt"](
                        user["email"], "invalid_code" if invite_code else "no_code",
                        name=user.get("name", ""), code_provided=invite_code)
                    return self._serve_html(start_response,
                        _login_page("You're not yet registered. "
                                    "Please enter a valid invitation code to get started."))

                self.auth["consume_invitation_code"](invite_code, user["email"])
                self.auth["register_authorized_user"](user["id"], user["email"],
                                         user.get("name", user["email"]))
                user["role"] = "user"
                self.auth["log_usage"](user["email"], "login", detail="first_login",
                          user_name=user.get("name", ""))
                session["authenticated"] = True
                session["user"] = user
                resp = flask_redirect("/")
                return self._save_session_and_respond(environ, start_response, resp)

        if path == "/auth/signout":
            with self.flask_app.request_context(environ):
                from flask import session, redirect as flask_redirect
                session.clear()
                resp = flask_redirect("/")
                return self._save_session_and_respond(environ, start_response, resp)

        return self.wsgi_app(environ, start_response)
