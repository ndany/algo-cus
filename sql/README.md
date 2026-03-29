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
| 004_reporting_functions.sql | Server-side RPC functions for aggregated reports |
