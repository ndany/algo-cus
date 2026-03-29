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
-- Active users: who is using the platform and how much (last 7 days)
SELECT * FROM get_active_users(7);

-- Top tickers: what are users analyzing and how often
SELECT * FROM get_top_tickers(20);

-- Expressed interest: unregistered users who tried to access
-- High attempt count = high interest — potential users to invite
SELECT * FROM get_expressed_interest();

-- Login frequency: how often each user logs in — engagement/retention signal
SELECT * FROM get_login_frequency();
```
