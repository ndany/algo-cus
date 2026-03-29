-- sql/migrations/003_user_roles.sql
-- Add role column to authorized_users (default: 'user')

ALTER TABLE authorized_users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user';

-- Set admin role for initial admin user
-- UPDATE authorized_users SET role = 'admin' WHERE email = 'your-admin@email.com';
