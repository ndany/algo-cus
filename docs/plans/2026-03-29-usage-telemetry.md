# Usage Telemetry Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Track user activity (logins, analysis runs, errors) and unauthorized access attempts in Supabase tables. Add admin reporting (dashboard page + CLI script). Establish versioned SQL migrations.

**Architecture:** Two new Supabase tables — `usage_log` for authenticated actions, `access_attempts` for rejected logins. A `telemetry.py` module wraps inserts with fire-and-forget semantics (never block the user). A `reporting.py` module provides shared query functions used by both the dashboard reports page (admin-only) and a CLI script. All SQL is version-controlled in `sql/migrations/`.

**Tech Stack:** Supabase (existing), Python, Dash (existing)

**Action vocabulary:**

`usage_log.action`: `login`, `login` (detail=`first_login`), `analyze`, `analyze_error`

`access_attempts.attempt_type`: `no_code`, `invalid_code`, `auth_failed`

---

### Task 1: Set up SQL migrations directory

**Files:**
- Create: `sql/migrations/001_auth_tables.sql`
- Create: `sql/migrations/002_telemetry.sql`
- Create: `sql/migrations/003_user_roles.sql`
- Create: `sql/README.md`
- Modify: `docs/DEPLOYMENT.md` (replace inline SQL with migration reference)

**Step 1: Create migration 001 from existing schema**

```sql
-- sql/migrations/001_auth_tables.sql
-- Initial auth tables for Supabase
-- Run once when setting up a new environment

CREATE TABLE IF NOT EXISTS invitation_codes (
    code TEXT PRIMARY KEY,
    used BOOLEAN DEFAULT FALSE,
    used_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS authorized_users (
    user_id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Step 2: Create migration 002 for telemetry**

```sql
-- sql/migrations/002_telemetry.sql
-- Usage telemetry and access attempt tracking

CREATE TABLE IF NOT EXISTS usage_log (
    id BIGSERIAL PRIMARY KEY,
    user_email TEXT NOT NULL,
    user_name TEXT,
    action TEXT NOT NULL,
    detail TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_log_email ON usage_log(user_email);
CREATE INDEX IF NOT EXISTS idx_usage_log_action ON usage_log(action);

CREATE TABLE IF NOT EXISTS access_attempts (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    name TEXT,
    attempt_type TEXT NOT NULL,
    code_provided TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_access_attempts_email ON access_attempts(email);
```

**Step 3: Create migration 003 for user roles**

```sql
-- sql/migrations/003_user_roles.sql
-- Add role column to authorized_users (default: 'user')

ALTER TABLE authorized_users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user';

-- Set admin role for initial admin user
-- UPDATE authorized_users SET role = 'admin' WHERE email = 'your-admin@email.com';
```

**Step 4: Create sql/README.md**

```markdown
# SQL Migrations

Numbered migration files for Supabase schema changes.

## Running migrations

**New environment:** Run all files in order in Supabase Dashboard > SQL Editor.

**Existing environment:** Run only the new migration files you haven't applied yet.

All statements use `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` so re-running is safe.

## Files

| Migration | Description |
|-----------|-------------|
| 001_auth_tables.sql | invitation_codes + authorized_users |
| 002_telemetry.sql | usage_log + access_attempts |
| 003_user_roles.sql | Add role column to authorized_users |
```

**Step 5: Update DEPLOYMENT.md**

Replace the inline CREATE TABLE blocks in the Supabase Setup section with:

```markdown
3. Run database migrations:
   - Open Supabase Dashboard > SQL Editor
   - Run each file in `sql/migrations/` in order (001, 002, 003, ...)
   - See `sql/README.md` for details
```

Keep the sample invitation codes INSERT inline since that's environment-specific.

**Step 6: Commit**

```bash
git add sql/ docs/DEPLOYMENT.md
git commit -m "Add versioned SQL migrations, extract existing schema from docs"
```

---

### Task 2: Apply new migrations (manual)

**Step 1: Run migrations 002 and 003 in Supabase Dashboard > SQL Editor**

Copy contents of `sql/migrations/002_telemetry.sql` and `sql/migrations/003_user_roles.sql` and execute.

**Step 2: Set admin role**

```sql
UPDATE authorized_users SET role = 'admin' WHERE email = 'nathan.dany@gmail.com';
```

**Step 3: Verify**

```sql
SELECT * FROM usage_log LIMIT 1;
SELECT * FROM access_attempts LIMIT 1;
SELECT user_id, email, role FROM authorized_users;
```

Expected: Empty telemetry tables, your record shows `role = 'admin'`.

---

### Task 3: Create telemetry module

**Files:**
- Create: `dashboard/telemetry.py`
- Test: `tests/test_telemetry.py`

**Step 1: Write the failing tests**

```python
# tests/test_telemetry.py
"""Tests for telemetry module."""

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

    def test_log_usage_without_supabase_does_not_raise(self):
        """Telemetry is fire-and-forget — errors are swallowed."""
        from dashboard.telemetry import log_usage
        log_usage("test@example.com", "login", detail="test", user_name="Test")

    def test_log_access_attempt_without_supabase_does_not_raise(self):
        from dashboard.telemetry import log_access_attempt
        log_access_attempt("test@example.com", "no_code", name="Test")
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_telemetry.py -v`
Expected: FAIL with "No module named 'dashboard.telemetry'"

**Step 3: Write implementation**

```python
# dashboard/telemetry.py
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
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_telemetry.py -v`
Expected: PASS (all 5)

**Step 5: Commit**

```bash
git add dashboard/telemetry.py tests/test_telemetry.py
git commit -m "Add telemetry module with fire-and-forget usage and access logging"
```

---

### Task 4: Instrument the auth middleware

**Files:**
- Modify: `dashboard/app.py` (import block + WSGI middleware `_handle_auth`)

**Step 1: Add import in the `if not SKIP_AUTH:` block**

```python
    from dashboard.telemetry import log_usage, log_access_attempt
```

**Step 2: Instrument four locations in `_handle_auth`**

1. **Auth failed** (token exchange error) — where `exchange_code_for_session` returns None:
   ```python
   log_access_attempt("", "auth_failed", name="unknown")
   ```

2. **Returning user login** — after `session["authenticated"] = True` in the `is_user_authorized` branch:
   ```python
   log_usage(user["email"], "login", user_name=user.get("name", ""))
   ```

3. **Rejected access** (new user + no/invalid code) — before returning the error page:
   ```python
   log_access_attempt(
       user["email"], "invalid_code" if invite_code else "no_code",
       name=user.get("name", ""), code_provided=invite_code)
   ```

4. **New user registration** — after `register_authorized_user`:
   ```python
   log_usage(user["email"], "login", detail="first_login",
             user_name=user.get("name", ""))
   ```

**Step 3: Run full test suite**

Run: `python -m pytest tests/ -m "not integration" -q`
Expected: All pass

**Step 4: Commit**

```bash
git add dashboard/app.py
git commit -m "Instrument auth middleware with telemetry logging"
```

---

### Task 5: Instrument the analyze callback

**Files:**
- Modify: `dashboard/app.py` (`on_analyze` callback)

**Step 1: Add telemetry to on_analyze**

After `result = run_analysis(ticker)` succeeds (inside the `try` block):

```python
        # Log usage telemetry
        from flask import session as flask_session
        auth_user = flask_session.get("user", {})
        if auth_user:
            from dashboard.telemetry import log_usage
            log_usage(auth_user.get("email", ""), "analyze",
                      detail=ticker, user_name=auth_user.get("name", ""))
```

In the `except` block, after `logger.exception(...)`:

```python
        # Log analysis failure
        from flask import session as flask_session
        auth_user = flask_session.get("user", {})
        if auth_user:
            from dashboard.telemetry import log_usage
            log_usage(auth_user.get("email", ""), "analyze_error",
                      detail=ticker, user_name=auth_user.get("name", ""))
```

**Step 2: Run full test suite**

Run: `python -m pytest tests/ -m "not integration" -q`
Expected: All pass

**Step 3: Commit**

```bash
git add dashboard/app.py
git commit -m "Log ticker analysis and error events to telemetry"
```

---

### Task 6: Create reporting module

**Files:**
- Create: `dashboard/reporting.py`
- Test: `tests/test_reporting.py`

**Step 1: Write the failing tests**

```python
# tests/test_reporting.py
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
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_reporting.py -v`
Expected: FAIL with "No module named 'dashboard.reporting'"

**Step 3: Write implementation**

```python
# dashboard/reporting.py
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
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_reporting.py -v`
Expected: PASS (all 2)

**Step 5: Commit**

```bash
git add dashboard/reporting.py tests/test_reporting.py
git commit -m "Add reporting module with shared query functions"
```

---

### Task 7: Add Supabase RPC functions for aggregated reports

**Files:**
- Create: `sql/migrations/004_reporting_functions.sql`
- Update: `sql/README.md`

**Step 1: Create reporting RPC functions**

```sql
-- sql/migrations/004_reporting_functions.sql
-- Server-side reporting functions for aggregated queries

-- Active users: who is using the platform and how much (last N days)
-- Returns: user_email, user_name, actions (count), last_seen
CREATE OR REPLACE FUNCTION get_active_users(days_back INT DEFAULT 7)
RETURNS TABLE(user_email TEXT, user_name TEXT, actions BIGINT, last_seen TIMESTAMPTZ)
LANGUAGE sql STABLE AS $$
    SELECT user_email, user_name, COUNT(*) as actions,
           MAX(created_at) as last_seen
    FROM usage_log
    WHERE created_at > NOW() - make_interval(days => days_back)
    GROUP BY user_email, user_name
    ORDER BY actions DESC;
$$;

-- Top tickers: what are users analyzing and how often
-- Returns: ticker, times (total analyses), unique_users (distinct users)
CREATE OR REPLACE FUNCTION get_top_tickers(result_limit INT DEFAULT 20)
RETURNS TABLE(ticker TEXT, times BIGINT, unique_users BIGINT)
LANGUAGE sql STABLE AS $$
    SELECT detail as ticker, COUNT(*) as times,
           COUNT(DISTINCT user_email) as unique_users
    FROM usage_log
    WHERE action = 'analyze' AND detail IS NOT NULL
    GROUP BY detail
    ORDER BY times DESC
    LIMIT result_limit;
$$;

-- Expressed interest: unregistered users who tried to access (no_code + invalid_code)
-- High attempt count = high interest — potential users to invite
-- Returns: email, name, attempt_type, attempts (count), first_attempt, last_attempt
CREATE OR REPLACE FUNCTION get_expressed_interest()
RETURNS TABLE(email TEXT, name TEXT, attempt_type TEXT, attempts BIGINT,
              first_attempt TIMESTAMPTZ, last_attempt TIMESTAMPTZ)
LANGUAGE sql STABLE AS $$
    SELECT email, name, attempt_type,
           COUNT(*) as attempts,
           MIN(created_at) as first_attempt,
           MAX(created_at) as last_attempt
    FROM access_attempts
    WHERE attempt_type IN ('no_code', 'invalid_code')
    GROUP BY email, name, attempt_type
    ORDER BY last_attempt DESC;
$$;

-- Login frequency: how often each user logs in — engagement/retention signal
-- Returns: user_email, user_name, logins (count), first_login, last_login
CREATE OR REPLACE FUNCTION get_login_frequency()
RETURNS TABLE(user_email TEXT, user_name TEXT, logins BIGINT,
              first_login TIMESTAMPTZ, last_login TIMESTAMPTZ)
LANGUAGE sql STABLE AS $$
    SELECT user_email, user_name,
           COUNT(*) as logins,
           MIN(created_at) as first_login,
           MAX(created_at) as last_login
    FROM usage_log
    WHERE action = 'login'
    GROUP BY user_email, user_name
    ORDER BY logins DESC;
$$;
```

**Step 2: Update sql/README.md** — add row for 004

**Step 3: Commit**

```bash
git add sql/
git commit -m "Add Supabase RPC functions for aggregated reporting"
```

---

### Task 8: Dashboard reporting page (admin-only)

**Files:**
- Modify: `dashboard/app.py` (navbar, layout, new callbacks)
- Modify: `dashboard/assets/style.css` (sign-out button restyle, reports link)
- Modify: `dashboard/auth.py` (return role with user info)
- Test: `tests/test_dashboard.py` (add reporting tests)

**Step 1: Update auth.py to include role**

Add a `get_user_role` function or update `is_user_authorized` to return role. The simplest approach: when building the session user dict in `_handle_auth`, query the role from `authorized_users`.

In `dashboard/auth.py`, add:

```python
def get_user_with_role(user_id: str) -> dict | None:
    """Get user record including role from authorized_users."""
    try:
        sb = get_supabase()
        result = (
            sb.table("authorized_users")
            .select("user_id, email, name, role")
            .eq("user_id", user_id)
            .execute()
        )
        if result.data:
            return result.data[0]
    except Exception as e:
        logger.error(f"get_user_with_role failed: {e}")
    return None
```

Update `_handle_auth` in `app.py`: after confirming user is authorized, call `get_user_with_role` and include `role` in `session["user"]`.

**Step 2: Restyle sign-out button and add reports link**

Add to `dashboard/assets/style.css`:

```css
.btn-signout {
    background: transparent !important;
    border: 1px solid #475569 !important;
    color: #475569 !important;
    font-size: 12px !important;
    padding: 4px 12px !important;
    border-radius: 4px !important;
    transition: all 0.2s;
}
.btn-signout:hover {
    border-color: #94a3b8 !important;
    color: #94a3b8 !important;
}
.reports-link {
    color: #475569 !important;
    text-decoration: none !important;
    font-size: 13px !important;
    margin-right: 16px !important;
    transition: color 0.2s;
}
.reports-link:hover {
    color: #94a3b8 !important;
}
```

**Step 3: Update make_navbar**

Change signature to `make_navbar(show_signout=False, user_role=None)`.

Replace sign-out button: use `className="btn-signout"` instead of `outline=True, color="secondary"`.

Add Reports link before sign-out (admin only):

```python
if user_role == "admin":
    children.append(
        html.A("Reports", href="#", id="reports-link",
               className="reports-link"),
    )
```

**Step 4: Update _make_app_shell to pass user role**

Read role from Flask session and pass to `make_navbar`:

```python
def _make_app_shell():
    from flask import session
    user = session.get("user", {})
    user_role = user.get("role", "user") if not SKIP_AUTH else "admin"
    return html.Div([
        make_navbar(show_signout=not SKIP_AUTH, user_role=user_role),
        ...
    ])
```

**Step 5: Add view-mode store and reports callback**

Add `dcc.Store(id="view-mode", data="terminal")` to the layout.

Add a callback that toggles between terminal and reports view:

```python
@callback(
    Output("main-content", "children"),
    Input("view-mode", "data"),
    State("analysis-store", "data"),
    State("selected-strategy", "data"),
)
def render_view(view_mode, store_data, selected_strategy):
    if view_mode == "reports":
        return build_reports_view()
    # Default terminal view — delegate to existing render_main logic
    return render_main_content(store_data, selected_strategy)
```

**Step 6: Build reports view**

Create `build_reports_view()` function with four tabs using `dbc.Tabs`/`dbc.Tab`:
- Active Users
- Top Tickers
- Expressed Interest
- Login Frequency

Each tab has a `dbc.Button("Refresh")` and a `dash_table.DataTable` or styled HTML table. Include a "Back to Terminal" link.

**Step 7: Write tests**

```python
class TestReporting:
    def test_navbar_shows_reports_for_admin(self):
        from dashboard.app import make_navbar
        nav = make_navbar(show_signout=True, user_role="admin")
        assert "reports-link" in str(nav)

    def test_navbar_hides_reports_for_user(self):
        from dashboard.app import make_navbar
        nav = make_navbar(show_signout=True, user_role="user")
        assert "reports-link" not in str(nav)

    def test_navbar_signout_uses_slate_style(self):
        from dashboard.app import make_navbar
        nav = make_navbar(show_signout=True, user_role="user")
        assert "btn-signout" in str(nav)
```

**Step 8: Run full test suite**

Run: `python -m pytest tests/ -m "not integration" -q`
Expected: All pass

**Step 9: Commit**

```bash
git add dashboard/app.py dashboard/auth.py dashboard/assets/style.css tests/test_dashboard.py
git commit -m "Add admin reports page with tabbed views, restyle navbar"
```

---

### Task 9: CLI reporting script

**Files:**
- Create: `scripts/report.py`

**Step 1: Write the script**

```python
#!/usr/bin/env python
"""CLI reporting tool — run from desktop to query usage telemetry.

Usage:
    python scripts/report.py                  # All reports
    python scripts/report.py active-users     # Active users (7 days)
    python scripts/report.py tickers          # Most analyzed tickers
    python scripts/report.py interest         # Expressed interest
    python scripts/report.py logins           # Login frequency
"""

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from dashboard.reporting import (
    get_active_users, get_top_tickers,
    get_expressed_interest, get_login_frequency,
)


def print_table(title, data, columns=None):
    """Print a list of dicts as a formatted table."""
    if not data:
        print(f"\n{title}: No data\n")
        return
    if columns is None:
        columns = list(data[0].keys())
    widths = {c: max(len(c), max(len(str(row.get(c, ""))) for row in data))
              for c in columns}
    header = "  ".join(c.ljust(widths[c]) for c in columns)
    print(f"\n{title}")
    print("=" * len(header))
    print(header)
    print("-" * len(header))
    for row in data:
        print("  ".join(str(row.get(c, "")).ljust(widths[c]) for c in columns))
    print()


def main():
    report = sys.argv[1] if len(sys.argv) > 1 else "all"

    reports = {
        "active-users": ("Active Users (last 7 days)", get_active_users),
        "tickers": ("Top Tickers", get_top_tickers),
        "interest": ("Expressed Interest (unregistered attempts)", get_expressed_interest),
        "logins": ("Login Frequency", get_login_frequency),
    }

    if report == "all":
        for name, (title, fn) in reports.items():
            print_table(title, fn())
    elif report in reports:
        title, fn = reports[report]
        print_table(title, fn())
    else:
        print(f"Unknown report: {report}")
        print(f"Available: {', '.join(reports.keys())}, all")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 2: Make executable**

```bash
chmod +x scripts/report.py
```

**Step 3: Commit**

```bash
git add scripts/report.py
git commit -m "Add CLI reporting script for desktop usage queries"
```

---

### Task 10: Add telemetry documentation

**Files:**
- Create: `docs/TELEMETRY.md`

**Step 1: Write the reference doc**

````markdown
# Telemetry

## Tables

**`usage_log`** — authenticated user actions

| action | detail | When |
|--------|--------|------|
| `login` | `""` | Returning user signs in |
| `login` | `first_login` | New user registers with code |
| `analyze` | ticker (e.g. `AMZN`) | User runs analysis |
| `analyze_error` | ticker | Analysis failed |

**`access_attempts`** — rejected access (expressed interest)

| attempt_type | When |
|--------------|------|
| `no_code` | Google auth succeeded, no invitation code provided |
| `invalid_code` | Google auth succeeded, invalid/claimed code |
| `auth_failed` | Google sign-in itself failed |

## Reporting

**Dashboard:** Admin users see a "Reports" link in the navbar with tabbed views.

**CLI:** Run from desktop (requires `.env` with Supabase credentials):

```bash
python scripts/report.py              # All reports
python scripts/report.py active-users # Active users (7 days)
python scripts/report.py tickers      # Most analyzed tickers
python scripts/report.py interest     # Expressed interest
python scripts/report.py logins       # Login frequency
```

## Raw SQL queries

Run in Supabase Dashboard > SQL Editor using the RPC functions:

```sql
SELECT * FROM get_active_users(7);
SELECT * FROM get_top_tickers(20);
SELECT * FROM get_expressed_interest();
SELECT * FROM get_login_frequency();
```
````

**Step 2: Commit**

```bash
git add docs/TELEMETRY.md
git commit -m "Add telemetry documentation with table schema and query reference"
```

---

### Task 11: Final verification

**Step 1: Run full test suite**

Run: `python -m pytest tests/ -m "not integration" -q`
Expected: All pass, 88%+ coverage

**Step 2: Verify no uncommitted changes**

Run: `git status`
Expected: Clean working tree

**Step 3: Push**

```bash
git push
```
