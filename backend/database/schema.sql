-- Database Schema for Natural Language Data Visualization
-- Using MySQL for analytics and data storage

-- ============================================================================
-- USERS TABLE (Reference - Actual auth is in Firebase)
-- This table syncs with Firebase for quick queries
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    picture VARCHAR(1024),
    auth_provider VARCHAR(50) DEFAULT 'email',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_users_email (email),
    INDEX idx_users_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- DATASETS TABLE (Metadata about uploaded files)
-- ============================================================================
CREATE TABLE IF NOT EXISTS datasets (
    dataset_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    dataset_name VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT,
    table_name VARCHAR(255) NOT NULL,
    row_count INTEGER,
    column_count INTEGER,
    columns_info JSON,
    upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    description TEXT,
    tags JSON,
    INDEX idx_datasets_user_id (user_id),
    INDEX idx_datasets_upload_date (upload_date),
    INDEX idx_datasets_is_deleted (is_deleted),
    INDEX idx_datasets_table_name (table_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- CONVERSATIONS TABLE (Chat/Query history)
-- ============================================================================
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    dataset_id VARCHAR(36),
    title VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_archived BOOLEAN DEFAULT FALSE,
    INDEX idx_conversations_user_id (user_id),
    INDEX idx_conversations_dataset_id (dataset_id),
    INDEX idx_conversations_created_at (created_at),
    INDEX idx_conversations_is_archived (is_archived)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- MESSAGES TABLE (Individual messages in conversations)
-- ============================================================================
CREATE TABLE IF NOT EXISTS messages (
    message_id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    query_sql TEXT,
    query_result JSON,
    visualization_config JSON,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    tokens_used INTEGER,
    INDEX idx_messages_conversation_id (conversation_id),
    INDEX idx_messages_created_at (created_at),
    INDEX idx_messages_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- QUERY_HISTORY TABLE (Track all SQL queries for analytics)
-- ============================================================================
CREATE TABLE IF NOT EXISTS query_history (
    query_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    dataset_id VARCHAR(36),
    conversation_id VARCHAR(36),
    natural_language_query TEXT NOT NULL,
    generated_sql TEXT NOT NULL,
    execution_time_ms DOUBLE,
    rows_returned INTEGER,
    success BOOLEAN,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_query_history_user_id (user_id),
    INDEX idx_query_history_dataset_id (dataset_id),
    INDEX idx_query_history_created_at (created_at),
    INDEX idx_query_history_success (success)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- SAVED_VISUALIZATIONS TABLE (User-saved charts and reports)
-- ============================================================================
CREATE TABLE IF NOT EXISTS saved_visualizations (
    visualization_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    dataset_id VARCHAR(36) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    chart_type VARCHAR(50),
    query_sql TEXT NOT NULL,
    visualization_config JSON NOT NULL,
    is_public BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_saved_viz_user_id (user_id),
    INDEX idx_saved_viz_dataset_id (dataset_id),
    INDEX idx_saved_viz_is_public (is_public)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- NOTES:
-- Dynamic user_data_* tables are created on-the-fly when users upload CSV files
-- Table naming convention: user_data_{dataset_id}
-- These tables contain the actual CSV data and are created dynamically
-- using pandas to_sql() method
-- ============================================================================
