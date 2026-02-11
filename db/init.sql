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

-- Create documents table for tracking uploaded PDFs
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sha256_hash TEXT NOT NULL UNIQUE,  -- Deduplication key
    original_filename TEXT NOT NULL,
    total_pages INTEGER NOT NULL,
    upload_source TEXT NOT NULL,  -- 'url' or 'file'
    source_url TEXT,  -- URL if uploaded via URL
    status TEXT DEFAULT 'processing',  -- 'processing', 'completed', 'failed'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_sha256 ON documents(sha256_hash);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);

-- Create user_documents table for linking users to their uploaded documents
CREATE TABLE IF NOT EXISTS user_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_sha256 TEXT NOT NULL REFERENCES documents(sha256_hash) ON DELETE CASCADE,
    linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, document_sha256)  -- Prevent duplicate links
);

CREATE INDEX IF NOT EXISTS idx_user_documents_user_id ON user_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_user_documents_document_sha256 ON user_documents(document_sha256);
CREATE INDEX IF NOT EXISTS idx_user_documents_linked_at ON user_documents(linked_at DESC);

-- Create document_chunks table for tracking PDF splits
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_sha256 TEXT NOT NULL REFERENCES documents(sha256_hash) ON DELETE CASCADE,
    chunk_number INTEGER NOT NULL,  -- 1, 2, 3...
    page_range_start INTEGER NOT NULL,
    page_range_end INTEGER NOT NULL,
    qdrant_point_id TEXT,  -- UUID in Qdrant vector DB
    text_content TEXT,  -- Extracted text
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_sha256, chunk_number)
);

CREATE INDEX IF NOT EXISTS idx_document_chunks_document_sha256 ON document_chunks(document_sha256);
CREATE INDEX IF NOT EXISTS idx_document_chunks_qdrant_point_id ON document_chunks(qdrant_point_id);

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
    RAISE NOTICE 'Tables created: users, assessments, recovery_plans, documents, user_documents, document_chunks';
END $$;
