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
