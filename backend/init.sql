-- Simple initialization script to create basic users table and admin user
-- This script will be run when the PostgreSQL container starts

-- Create users table with all required columns
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    department VARCHAR(100),
    role VARCHAR(100),
    avatar_url VARCHAR(255),
    jira_account_id VARCHAR(255),
    jira_display_name VARCHAR(255),
    sso_provider VARCHAR(50),
    sso_provider_id VARCHAR(255),
    sso_provider_name VARCHAR(255),
    sso_last_login TIMESTAMP WITH TIME ZONE,
    sso_attributes JSON,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    last_login TIMESTAMP WITH TIME ZONE,
    reset_token VARCHAR(255),
    reset_token_expires TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create admin user with bcrypt hash for 'admin123'
-- Hash generated for password 'admin123' using bcrypt with cost 12
INSERT INTO users (email, username, full_name, hashed_password, is_active, is_superuser, department, role)
VALUES (
    'admin@sprint-reports.com',
    'admin', 
    'System Administrator',
    '$2b$12$LQv3c1yqBWVHxkd0LQ4bLu.Ky9ekHqNpx.8LoXgJZNs3CpQVVKYCO',
    true,
    true,
    'IT',
    'Administrator'
) ON CONFLICT (email) DO NOTHING;

-- Create simple test user
INSERT INTO users (email, username, full_name, hashed_password, is_active, is_superuser)
VALUES (
    'simple@admin.com',
    'simpleadmin',
    'Simple Administrator', 
    '$2b$12$LQv3c1yqBWVHxkd0LQ4bLu.Ky9ekHqNpx.8LoXgJZNs3CpQVVKYCO',
    true,
    true
) ON CONFLICT (email) DO NOTHING;

-- Create basic sprints table for testing
CREATE TABLE IF NOT EXISTS sprints (
    id SERIAL PRIMARY KEY,
    jira_sprint_id INTEGER UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    state VARCHAR(50) NOT NULL DEFAULT 'future',
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    complete_date TIMESTAMP WITH TIME ZONE,
    goal TEXT,
    board_id INTEGER,
    origin_board_id INTEGER,
    jira_last_updated TIMESTAMP WITH TIME ZONE,
    sync_status VARCHAR(20) DEFAULT 'pending',
    sync_conflicts JSON,
    jira_board_name VARCHAR(200),
    jira_project_key VARCHAR(50),
    jira_version VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert some sample sprints for testing
INSERT INTO sprints (jira_sprint_id, name, state, start_date, end_date, goal, board_id) VALUES
(1001, 'Sprint 2024-01', 'closed', '2024-01-01'::timestamp, '2024-01-14'::timestamp, 'Q1 Foundation Features', 123),
(1002, 'Sprint 2024-02', 'closed', '2024-01-15'::timestamp, '2024-01-28'::timestamp, 'User Authentication & Security', 123),
(1003, 'Sprint 2024-03', 'active', '2024-01-29'::timestamp, '2024-02-11'::timestamp, 'Analytics Dashboard', 123),
(1004, 'Sprint 2024-04', 'future', '2024-02-12'::timestamp, '2024-02-25'::timestamp, 'Reporting System', 123),
(1005, 'Sprint 2024-05', 'future', '2024-02-26'::timestamp, '2024-03-11'::timestamp, 'Integration Platform', 123)
ON CONFLICT (jira_sprint_id) DO NOTHING;