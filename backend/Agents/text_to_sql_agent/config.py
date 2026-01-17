"""
Configuration for the Text-to-SQL agent.
"""

# OpenAI API Configuration
OPENAI_CONFIG = {
    "model": "gpt-4o",
    "temperature": 0.3,  # Lower for more consistent SQL generation
    "max_tokens": 500,   # SQL queries are typically short
    "timeout": 15,       # seconds
}

# SQL Generation Configuration
SQL_CONFIG = {
    "max_retries": 1,           # Retry once on SQL error
    "default_row_limit": 1000,  # Default LIMIT for queries
    "max_row_limit": 10000,     # Maximum allowed LIMIT
}

# Token Optimization Configuration
TOKEN_CONFIG = {
    "max_sample_values": 3,         # Sample values for VARCHAR columns
    "max_conversation_history": 3,  # Q&A exchanges to keep in context
    "max_column_name_length": 50,   # Truncate long column names
}

# Session Configuration
SESSION_CONFIG = {
    "session_timeout_seconds": 3600,  # 1 hour
    "max_messages_per_session": 10,   # Keep last N messages
    "cleanup_interval_seconds": 300,  # Run cleanup every 5 minutes
}

# Rate Limiting Configuration
RATE_LIMIT_CONFIG = {
    "max_retries": 3,
    "base_delay": 2,      # seconds
    "max_delay": 8,       # seconds
    "exponential_base": 2,
}

# Supported SQL Operations (for documentation/validation)
SUPPORTED_OPERATIONS = {
    "aggregations": ["SUM", "AVG", "COUNT", "MIN", "MAX", "GROUP BY"],
    "filtering": ["WHERE", "AND", "OR", "IN", "BETWEEN", "LIKE", "NOT"],
    "sorting": ["ORDER BY", "ASC", "DESC"],
    "limiting": ["LIMIT", "OFFSET"],
    "date_operations": ["EXTRACT", "DATE_TRUNC", "DATE_DIFF"],
}
