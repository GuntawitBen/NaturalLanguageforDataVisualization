"""
Database package for Natural Language Data Visualization
"""
from .db_init import (
    get_db_connection,
    get_db_engine,
    init_database,
    close_connection,
    reset_database,
    get_db_status,
    set_db_status,
    test_db_connection,
    require_db_connection,
    DatabaseConnectionError,
)
from .db_utils import (
    # User management
    sync_user_from_firebase,

    # Dataset management
    create_dataset,
    get_dataset,
    get_user_datasets,
    delete_dataset,
    query_dataset,

    # Conversation management
    create_conversation,
    add_message,
    get_conversation_messages,
    get_user_conversations,

    # Query history
    log_query,

    # Visualizations
    save_visualization,
    get_user_visualizations,
)

__all__ = [
    # Database initialization
    'get_db_connection',
    'get_db_engine',
    'init_database',
    'close_connection',
    'reset_database',
    'get_db_status',
    'set_db_status',
    'test_db_connection',
    'require_db_connection',
    'DatabaseConnectionError',

    # User management
    'sync_user_from_firebase',

    # Dataset management
    'create_dataset',
    'get_dataset',
    'get_user_datasets',
    'delete_dataset',
    'query_dataset',

    # Conversation management
    'create_conversation',
    'add_message',
    'get_conversation_messages',
    'get_user_conversations',

    # Query history
    'log_query',

    # Visualizations
    'save_visualization',
    'get_user_visualizations',
]
