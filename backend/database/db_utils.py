"""
Database utility functions for managing datasets, conversations, and queries
"""
import uuid
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from database.db_init import get_db_connection

# ============================================================================
# USER MANAGEMENT
# ============================================================================

def sync_user_from_firebase(user_id: str, email: str, name: str, picture: str = None, auth_provider: str = 'email'):
    """Sync user from Firebase to DuckDB for quick queries"""
    conn = get_db_connection()

    try:
        # Check if user exists
        existing = conn.execute(
            "SELECT user_id FROM users WHERE email = ?",
            [email]
        ).fetchone()

        if existing:
            # Update existing user
            conn.execute("""
                UPDATE users
                SET name = ?, picture = ?, last_login = CURRENT_TIMESTAMP
                WHERE email = ?
            """, [name, picture, email])
        else:
            # Insert new user
            conn.execute("""
                INSERT INTO users (user_id, email, name, picture, auth_provider)
                VALUES (?, ?, ?, ?, ?)
            """, [user_id, email, name, picture, auth_provider])

        return True
    except Exception as e:
        print(f"Error syncing user: {e}")
        return False

# ============================================================================
# DATASET MANAGEMENT
# ============================================================================

def create_dataset(
    user_id: str,
    dataset_name: str,
    original_filename: str,
    file_path: str,
    description: str = None,
    tags: List[str] = None,
    extract_stats: bool = False
) -> Optional[str]:
    """
    Create a new dataset by importing CSV file

    Args:
        user_id: User ID (email)
        dataset_name: Name for the dataset
        original_filename: Original CSV filename
        file_path: Path to CSV file
        description: Optional description
        tags: Optional list of tags
        extract_stats: Whether to extract detailed column statistics (slower)

    Returns:
        dataset_id if successful, None otherwise
    """
    conn = get_db_connection()
    dataset_id = str(uuid.uuid4())
    table_name = f"user_data_{dataset_id.replace('-', '_')}"

    try:
        # 1. Read CSV file and create dynamic table
        conn.execute(f"""
            CREATE TABLE {table_name} AS
            SELECT * FROM read_csv_auto('{file_path}')
        """)

        # 2. Get table metadata from information_schema
        columns_info = conn.execute(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """).fetchall()

        # 3. Get row and column counts
        row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        column_count = len(columns_info)

        # 4. Get file size
        import os
        file_size_bytes = os.path.getsize(file_path)

        # 5. Format columns info as JSON
        columns_json = json.dumps([
            {
                "name": col[0],
                "type": col[1],
                "nullable": col[2] == 'YES'
            }
            for col in columns_info
        ])

        # 6. Extract detailed statistics if requested
        metadata_stats = None
        if extract_stats:
            from utils.metadata_extractor import extract_comprehensive_metadata
            metadata_stats = extract_comprehensive_metadata(table_name, include_stats=True)

        # 7. Insert dataset metadata
        conn.execute("""
            INSERT INTO datasets (
                dataset_id, user_id, dataset_name, original_filename,
                file_size_bytes, table_name, row_count, column_count,
                columns_info, description, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            dataset_id, user_id, dataset_name, original_filename,
            file_size_bytes, table_name, row_count, column_count,
            columns_json, description, tags or []
        ])

        print(f"[OK] Dataset created: {dataset_id} ({table_name})")
        print(f"     Rows: {row_count:,} | Columns: {column_count} | Size: {file_size_bytes:,} bytes")

        # 8. Save metadata snapshot if stats were extracted
        if metadata_stats:
            from utils.metadata_extractor import save_metadata_snapshot
            save_metadata_snapshot(dataset_id, metadata_stats)

        return dataset_id

    except Exception as e:
        print(f"[ERROR] Error creating dataset: {e}")
        # Cleanup: drop table if created
        try:
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        except:
            pass
        return None

def get_dataset(dataset_id: str) -> Optional[Dict]:
    """Get dataset metadata"""
    conn = get_db_connection()

    try:
        result = conn.execute("""
            SELECT * FROM datasets WHERE dataset_id = ? AND is_deleted = FALSE
        """, [dataset_id]).fetchone()

        if not result:
            return None

        columns = [desc[0] for desc in conn.description]
        dataset = dict(zip(columns, result))

        # Parse JSON columns
        if dataset.get('columns_info'):
            dataset['columns_info'] = json.loads(dataset['columns_info'])

        return dataset

    except Exception as e:
        print(f"Error getting dataset: {e}")
        return None

def get_user_datasets(user_id: str, include_deleted: bool = False) -> List[Dict]:
    """Get all datasets for a user"""
    conn = get_db_connection()

    try:
        query = "SELECT * FROM datasets WHERE user_id = ?"
        params = [user_id]

        if not include_deleted:
            query += " AND is_deleted = FALSE"

        query += " ORDER BY upload_date DESC"

        results = conn.execute(query, params).fetchall()
        columns = [desc[0] for desc in conn.description]

        datasets = []
        for row in results:
            dataset = dict(zip(columns, row))
            if dataset.get('columns_info'):
                dataset['columns_info'] = json.loads(dataset['columns_info'])
            datasets.append(dataset)

        return datasets

    except Exception as e:
        print(f"Error getting user datasets: {e}")
        return []

def delete_dataset(dataset_id: str, hard_delete: bool = False) -> bool:
    """
    Delete a dataset (soft delete by default)
    Set hard_delete=True to permanently remove
    """
    conn = get_db_connection()

    try:
        if hard_delete:
            # Get table name
            dataset = get_dataset(dataset_id)
            if dataset:
                table_name = dataset['table_name']
                # Drop the data table
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")

            # Delete metadata
            conn.execute("DELETE FROM datasets WHERE dataset_id = ?", [dataset_id])
        else:
            # Soft delete
            conn.execute("""
                UPDATE datasets SET is_deleted = TRUE WHERE dataset_id = ?
            """, [dataset_id])

        return True

    except Exception as e:
        print(f"Error deleting dataset: {e}")
        return False

def query_dataset(dataset_id: str, sql_query: str) -> Dict[str, Any]:
    """
    Execute a SQL query on a dataset
    Returns: {success: bool, data: list, columns: list, error: str}
    """
    conn = get_db_connection()

    try:
        # Get dataset to verify it exists and get table name
        dataset = get_dataset(dataset_id)
        if not dataset:
            return {"success": False, "error": "Dataset not found"}

        table_name = dataset['table_name']

        # Replace placeholder table name in query
        sql_query = sql_query.replace('{{table}}', table_name)

        # Execute query with timing
        start_time = datetime.now()
        result = conn.execute(sql_query).fetchall()
        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        # Get column names
        columns = [desc[0] for desc in conn.description] if conn.description else []

        # Update last_accessed
        conn.execute("""
            UPDATE datasets SET last_accessed = CURRENT_TIMESTAMP
            WHERE dataset_id = ?
        """, [dataset_id])

        return {
            "success": True,
            "data": result,
            "columns": columns,
            "row_count": len(result),
            "execution_time_ms": execution_time
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================================================
# CONVERSATION MANAGEMENT
# ============================================================================

def create_conversation(user_id: str, dataset_id: str = None, title: str = None) -> str:
    """Create a new conversation"""
    conn = get_db_connection()
    conversation_id = str(uuid.uuid4())

    try:
        conn.execute("""
            INSERT INTO conversations (conversation_id, user_id, dataset_id, title)
            VALUES (?, ?, ?, ?)
        """, [conversation_id, user_id, dataset_id, title])

        return conversation_id

    except Exception as e:
        print(f"Error creating conversation: {e}")
        return None

def add_message(
    conversation_id: str,
    role: str,
    content: str,
    query_sql: str = None,
    query_result: Any = None,
    visualization_config: Any = None,
    error_message: str = None,
    tokens_used: int = None
) -> str:
    """Add a message to a conversation"""
    conn = get_db_connection()
    message_id = str(uuid.uuid4())

    try:
        # Convert complex types to JSON
        query_result_json = json.dumps(query_result) if query_result else None
        viz_config_json = json.dumps(visualization_config) if visualization_config else None

        conn.execute("""
            INSERT INTO messages (
                message_id, conversation_id, role, content,
                query_sql, query_result, visualization_config,
                error_message, tokens_used
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            message_id, conversation_id, role, content,
            query_sql, query_result_json, viz_config_json,
            error_message, tokens_used
        ])

        # Update conversation updated_at
        conn.execute("""
            UPDATE conversations SET updated_at = CURRENT_TIMESTAMP
            WHERE conversation_id = ?
        """, [conversation_id])

        return message_id

    except Exception as e:
        print(f"Error adding message: {e}")
        return None

def get_conversation_messages(conversation_id: str) -> List[Dict]:
    """Get all messages in a conversation"""
    conn = get_db_connection()

    try:
        results = conn.execute("""
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
        """, [conversation_id]).fetchall()

        columns = [desc[0] for desc in conn.description]

        messages = []
        for row in results:
            message = dict(zip(columns, row))

            # Parse JSON fields
            if message.get('query_result'):
                message['query_result'] = json.loads(message['query_result'])
            if message.get('visualization_config'):
                message['visualization_config'] = json.loads(message['visualization_config'])

            messages.append(message)

        return messages

    except Exception as e:
        print(f"Error getting messages: {e}")
        return []

def get_user_conversations(user_id: str, include_archived: bool = False, limit: int = 50) -> List[Dict]:
    """Get all conversations for a user with message counts"""
    conn = get_db_connection()

    try:
        query = """
            SELECT c.*,
                   d.dataset_name,
                   COUNT(m.message_id) as message_count,
                   (SELECT content FROM messages WHERE conversation_id = c.conversation_id AND role = 'user' ORDER BY created_at ASC LIMIT 1) as first_question
            FROM conversations c
            LEFT JOIN datasets d ON c.dataset_id = d.dataset_id
            LEFT JOIN messages m ON c.conversation_id = m.conversation_id
            WHERE c.user_id = ?
        """
        params = [user_id]

        if not include_archived:
            query += " AND c.is_archived = FALSE"

        query += " GROUP BY c.conversation_id, c.user_id, c.dataset_id, c.title, c.created_at, c.updated_at, c.is_archived, d.dataset_name"
        query += " ORDER BY c.updated_at DESC"
        query += f" LIMIT {limit}"

        results = conn.execute(query, params).fetchall()
        columns = [desc[0] for desc in conn.description]

        return [dict(zip(columns, row)) for row in results]

    except Exception as e:
        print(f"Error getting conversations: {e}")
        return []


def get_conversation(conversation_id: str) -> Optional[Dict]:
    """Get a single conversation by ID"""
    conn = get_db_connection()

    try:
        result = conn.execute("""
            SELECT c.*, d.dataset_name, d.table_name
            FROM conversations c
            LEFT JOIN datasets d ON c.dataset_id = d.dataset_id
            WHERE c.conversation_id = ?
        """, [conversation_id]).fetchone()

        if not result:
            return None

        columns = [desc[0] for desc in conn.description]
        return dict(zip(columns, result))

    except Exception as e:
        print(f"Error getting conversation: {e}")
        return None


def update_conversation_title(conversation_id: str, title: str) -> bool:
    """Update a conversation's title"""
    conn = get_db_connection()

    try:
        conn.execute("""
            UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE conversation_id = ?
        """, [title, conversation_id])
        return True
    except Exception as e:
        print(f"Error updating conversation title: {e}")
        return False


def touch_conversation(conversation_id: str) -> bool:
    """Update the conversation's updated_at timestamp to now"""
    conn = get_db_connection()

    try:
        conn.execute("""
            UPDATE conversations SET updated_at = CURRENT_TIMESTAMP
            WHERE conversation_id = ?
        """, [conversation_id])
        return True
    except Exception as e:
        print(f"Error touching conversation: {e}")
        return False


def delete_conversation(conversation_id: str, hard_delete: bool = False) -> bool:
    """
    Delete a conversation and its messages.

    Args:
        conversation_id: Conversation identifier
        hard_delete: If True, permanently delete. If False, archive (soft delete).

    Returns:
        True if successful
    """
    conn = get_db_connection()

    try:
        if hard_delete:
            # Delete messages first (foreign key constraint)
            conn.execute("""
                DELETE FROM messages WHERE conversation_id = ?
            """, [conversation_id])
            # Delete conversation
            conn.execute("""
                DELETE FROM conversations WHERE conversation_id = ?
            """, [conversation_id])
        else:
            # Soft delete (archive)
            conn.execute("""
                UPDATE conversations SET is_archived = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE conversation_id = ?
            """, [conversation_id])

        return True
    except Exception as e:
        print(f"Error deleting conversation: {e}")
        return False


# ============================================================================
# QUERY HISTORY
# ============================================================================

def log_query(
    user_id: str,
    natural_language_query: str,
    generated_sql: str,
    dataset_id: str = None,
    conversation_id: str = None,
    execution_time_ms: float = None,
    rows_returned: int = None,
    success: bool = True,
    error_message: str = None
) -> str:
    """Log a query execution for analytics"""
    conn = get_db_connection()
    query_id = str(uuid.uuid4())

    try:
        conn.execute("""
            INSERT INTO query_history (
                query_id, user_id, dataset_id, conversation_id,
                natural_language_query, generated_sql,
                execution_time_ms, rows_returned, success, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            query_id, user_id, dataset_id, conversation_id,
            natural_language_query, generated_sql,
            execution_time_ms, rows_returned, success, error_message
        ])

        return query_id

    except Exception as e:
        print(f"Error logging query: {e}")
        return None

# ============================================================================
# SAVED VISUALIZATIONS
# ============================================================================

def save_visualization(
    user_id: str,
    dataset_id: str,
    title: str,
    query_sql: str,
    chart_type: str,
    visualization_config: Dict,
    description: str = None,
    is_public: bool = False
) -> str:
    """Save a visualization"""
    conn = get_db_connection()
    viz_id = str(uuid.uuid4())

    try:
        viz_config_json = json.dumps(visualization_config)

        conn.execute("""
            INSERT INTO saved_visualizations (
                visualization_id, user_id, dataset_id, title, description,
                chart_type, query_sql, visualization_config, is_public
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            viz_id, user_id, dataset_id, title, description,
            chart_type, query_sql, viz_config_json, is_public
        ])

        return viz_id

    except Exception as e:
        print(f"Error saving visualization: {e}")
        return None

def get_user_visualizations(user_id: str) -> List[Dict]:
    """Get all saved visualizations for a user"""
    conn = get_db_connection()

    try:
        results = conn.execute("""
            SELECT * FROM saved_visualizations
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, [user_id]).fetchall()

        columns = [desc[0] for desc in conn.description]

        visualizations = []
        for row in results:
            viz = dict(zip(columns, row))
            if viz.get('visualization_config'):
                viz['visualization_config'] = json.loads(viz['visualization_config'])
            visualizations.append(viz)

        return visualizations

    except Exception as e:
        print(f"Error getting visualizations: {e}")
        return []
