-- Database Schema for Natural Language Data Visualization
-- Using DuckDB for analytics and data storage

-- ============================================================================
-- USERS TABLE (Reference - Actual auth is in Firebase)
-- This table syncs with Firebase for quick queries
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    picture VARCHAR,
    auth_provider VARCHAR DEFAULT 'email', -- 'email' or 'google'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- ============================================================================
-- DATASETS TABLE (Metadata about uploaded files)
-- ============================================================================
CREATE TABLE IF NOT EXISTS datasets (
    dataset_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    dataset_name VARCHAR NOT NULL,
    original_filename VARCHAR NOT NULL,
    file_size_bytes BIGINT,
    table_name VARCHAR NOT NULL, -- Dynamic table name: user_data_{dataset_id}
    row_count INTEGER,
    column_count INTEGER,
    columns_info JSON, -- Array of {name, type, nullable, sample_values}
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    description TEXT,
    tags VARCHAR[] -- Array of tags for categorization
);

CREATE INDEX IF NOT EXISTS idx_datasets_user_id ON datasets(user_id);
CREATE INDEX IF NOT EXISTS idx_datasets_upload_date ON datasets(upload_date);
CREATE INDEX IF NOT EXISTS idx_datasets_is_deleted ON datasets(is_deleted);
CREATE INDEX IF NOT EXISTS idx_datasets_table_name ON datasets(table_name);

-- ============================================================================
-- CONVERSATIONS TABLE (Chat/Query history)
-- ============================================================================
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    dataset_id VARCHAR, -- NULL for general conversations
    title VARCHAR, -- Auto-generated or user-provided
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_archived BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_dataset_id ON conversations(dataset_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_is_archived ON conversations(is_archived);

-- ============================================================================
-- MESSAGES TABLE (Individual messages in conversations)
-- ============================================================================
CREATE TABLE IF NOT EXISTS messages (
    message_id VARCHAR PRIMARY KEY,
    conversation_id VARCHAR NOT NULL,
    role VARCHAR NOT NULL, -- 'user' or 'assistant'
    content TEXT NOT NULL,
    query_sql TEXT, -- Generated SQL query (if applicable)
    query_result JSON, -- Result of SQL query (if applicable)
    visualization_config JSON, -- Chart configuration (if applicable)
    error_message TEXT, -- Error if query failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tokens_used INTEGER -- For tracking API usage
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);

-- ============================================================================
-- QUERY_HISTORY TABLE (Track all SQL queries for analytics)
-- ============================================================================
CREATE TABLE IF NOT EXISTS query_history (
    query_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    dataset_id VARCHAR,
    conversation_id VARCHAR,
    natural_language_query TEXT NOT NULL,
    generated_sql TEXT NOT NULL,
    execution_time_ms DOUBLE,
    rows_returned INTEGER,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_query_history_user_id ON query_history(user_id);
CREATE INDEX IF NOT EXISTS idx_query_history_dataset_id ON query_history(dataset_id);
CREATE INDEX IF NOT EXISTS idx_query_history_created_at ON query_history(created_at);
CREATE INDEX IF NOT EXISTS idx_query_history_success ON query_history(success);

-- ============================================================================
-- SAVED_VISUALIZATIONS TABLE (User-saved charts and reports)
-- ============================================================================
CREATE TABLE IF NOT EXISTS saved_visualizations (
    visualization_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    dataset_id VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    description TEXT,
    chart_type VARCHAR, -- 'bar', 'line', 'pie', 'scatter', etc.
    query_sql TEXT NOT NULL,
    visualization_config JSON NOT NULL, -- Complete chart configuration
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_saved_viz_user_id ON saved_visualizations(user_id);
CREATE INDEX IF NOT EXISTS idx_saved_viz_dataset_id ON saved_visualizations(dataset_id);
CREATE INDEX IF NOT EXISTS idx_saved_viz_is_public ON saved_visualizations(is_public);

-- ============================================================================
-- NOTES:
-- Dynamic user_data_* tables are created on-the-fly when users upload CSV files
-- Table naming convention: user_data_{dataset_id}
-- These tables contain the actual CSV data and are created dynamically
-- Example: CREATE TABLE user_data_abc123 AS SELECT * FROM read_csv('file.csv')
-- ============================================================================
