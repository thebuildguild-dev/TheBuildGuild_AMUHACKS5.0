-- AMU Academic Recovery Engine Database Schema
-- This script runs automatically on first PostgreSQL container startup

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,  -- Firebase UID
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Create assessments table
CREATE TABLE IF NOT EXISTS assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    payload JSONB NOT NULL,  -- Raw assessment answers
    gap_vector JSONB,  -- Optional derived vector per subject/topic
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_assessments_user_id ON assessments(user_id);
CREATE INDEX IF NOT EXISTS idx_assessments_created_at ON assessments(created_at DESC);

-- Create recovery_plans table
CREATE TABLE IF NOT EXISTS recovery_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    plan JSONB NOT NULL,  -- Final plan (daily schedule, topic ranks, strategy)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_recovery_plans_user_id ON recovery_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_recovery_plans_assessment_id ON recovery_plans(assessment_id);
CREATE INDEX IF NOT EXISTS idx_recovery_plans_created_at ON recovery_plans(created_at DESC);

-- Create pyq_meta table (optional, for small metadata storage)
CREATE TABLE IF NOT EXISTS pyq_meta (
    id SERIAL PRIMARY KEY,
    qdrant_id TEXT UNIQUE,
    year INTEGER,
    subject TEXT,
    marks_estimate INTEGER,
    original_filename TEXT,
    excerpt TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pyq_meta_subject ON pyq_meta(subject);
CREATE INDEX IF NOT EXISTS idx_pyq_meta_year ON pyq_meta(year);
CREATE INDEX IF NOT EXISTS idx_pyq_meta_qdrant_id ON pyq_meta(qdrant_id);

-- Create trigger to auto-update updated_at on recovery_plans
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_recovery_plans_updated_at 
    BEFORE UPDATE ON recovery_plans 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (optional, for production with specific users)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'AMU Recovery Engine schema initialized successfully!';
    RAISE NOTICE 'Tables created: users, assessments, recovery_plans, pyq_meta';
END $$;
