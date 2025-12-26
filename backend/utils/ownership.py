"""
User Ownership Linking and Management
Handles user-resource ownership verification, access control, and transfers
"""
from typing import Dict, List, Optional, Tuple
from database.db_init import get_db_connection
from database.db_utils import get_dataset, get_user_datasets
import json

# ============================================================================
# OWNERSHIP VERIFICATION
# ============================================================================

def verify_dataset_ownership(dataset_id: str, user_id: str) -> Tuple[bool, Optional[str]]:
    """
    Verify that a user owns a specific dataset

    Args:
        dataset_id: Dataset ID to check
        user_id: User ID (email or Firebase UID)

    Returns:
        Tuple of (is_owner: bool, error_message: Optional[str])
    """
    conn = get_db_connection()

    try:
        result = conn.execute("""
            SELECT user_id, is_deleted
            FROM datasets
            WHERE dataset_id = ?
        """, [dataset_id]).fetchone()

        if not result:
            return False, "Dataset not found"

        owner_id, is_deleted = result

        if is_deleted:
            return False, "Dataset has been deleted"

        if owner_id != user_id:
            return False, "Access denied: You do not own this dataset"

        return True, None

    except Exception as e:
        return False, f"Error verifying ownership: {str(e)}"

def verify_conversation_ownership(conversation_id: str, user_id: str) -> Tuple[bool, Optional[str]]:
    """
    Verify that a user owns a specific conversation

    Args:
        conversation_id: Conversation ID to check
        user_id: User ID (email or Firebase UID)

    Returns:
        Tuple of (is_owner: bool, error_message: Optional[str])
    """
    conn = get_db_connection()

    try:
        result = conn.execute("""
            SELECT user_id, is_archived
            FROM conversations
            WHERE conversation_id = ?
        """, [conversation_id]).fetchone()

        if not result:
            return False, "Conversation not found"

        owner_id, is_archived = result

        if owner_id != user_id:
            return False, "Access denied: You do not own this conversation"

        return True, None

    except Exception as e:
        return False, f"Error verifying ownership: {str(e)}"

def verify_visualization_ownership(visualization_id: str, user_id: str) -> Tuple[bool, Optional[str]]:
    """
    Verify that a user owns a specific visualization

    Args:
        visualization_id: Visualization ID to check
        user_id: User ID (email or Firebase UID)

    Returns:
        Tuple of (is_owner: bool, error_message: Optional[str])
    """
    conn = get_db_connection()

    try:
        result = conn.execute("""
            SELECT user_id, is_public
            FROM saved_visualizations
            WHERE visualization_id = ?
        """, [visualization_id]).fetchone()

        if not result:
            return False, "Visualization not found"

        owner_id, is_public = result

        # Public visualizations can be viewed by anyone
        if is_public:
            return True, None

        if owner_id != user_id:
            return False, "Access denied: You do not own this visualization"

        return True, None

    except Exception as e:
        return False, f"Error verifying ownership: {str(e)}"

# ============================================================================
# USER RESOURCE QUERIES
# ============================================================================

def get_user_resource_count(user_id: str) -> Dict[str, int]:
    """
    Get count of all resources owned by a user

    Returns:
        Dictionary with counts for each resource type
    """
    conn = get_db_connection()

    try:
        counts = {}

        # Count active datasets
        counts['datasets'] = conn.execute("""
            SELECT COUNT(*) FROM datasets
            WHERE user_id = ? AND is_deleted = FALSE
        """, [user_id]).fetchone()[0]

        # Count deleted datasets
        counts['deleted_datasets'] = conn.execute("""
            SELECT COUNT(*) FROM datasets
            WHERE user_id = ? AND is_deleted = TRUE
        """, [user_id]).fetchone()[0]

        # Count conversations
        counts['conversations'] = conn.execute("""
            SELECT COUNT(*) FROM conversations
            WHERE user_id = ? AND is_archived = FALSE
        """, [user_id]).fetchone()[0]

        # Count archived conversations
        counts['archived_conversations'] = conn.execute("""
            SELECT COUNT(*) FROM conversations
            WHERE user_id = ? AND is_archived = TRUE
        """, [user_id]).fetchone()[0]

        # Count saved visualizations
        counts['visualizations'] = conn.execute("""
            SELECT COUNT(*) FROM saved_visualizations
            WHERE user_id = ?
        """, [user_id]).fetchone()[0]

        # Count queries
        counts['queries'] = conn.execute("""
            SELECT COUNT(*) FROM query_history
            WHERE user_id = ?
        """, [user_id]).fetchone()[0]

        # Total storage used (sum of all dataset file sizes)
        storage_result = conn.execute("""
            SELECT COALESCE(SUM(file_size_bytes), 0) FROM datasets
            WHERE user_id = ? AND is_deleted = FALSE
        """, [user_id]).fetchone()
        counts['total_storage_bytes'] = int(storage_result[0])

        return counts

    except Exception as e:
        print(f"Error getting user resource count: {e}")
        return {}

def get_user_activity_summary(user_id: str, days: int = 30) -> Dict:
    """
    Get user activity summary for the last N days

    Args:
        user_id: User ID
        days: Number of days to look back (default: 30)

    Returns:
        Dictionary with activity metrics
    """
    conn = get_db_connection()

    try:
        summary = {}

        # Recent uploads
        summary['recent_uploads'] = conn.execute(f"""
            SELECT COUNT(*) FROM datasets
            WHERE user_id = ?
            AND upload_date >= CURRENT_TIMESTAMP - INTERVAL '{days}' DAY
        """, [user_id]).fetchone()[0]

        # Recent queries
        summary['recent_queries'] = conn.execute(f"""
            SELECT COUNT(*) FROM query_history
            WHERE user_id = ?
            AND created_at >= CURRENT_TIMESTAMP - INTERVAL '{days}' DAY
        """, [user_id]).fetchone()[0]

        # Successful query rate
        query_stats = conn.execute(f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful
            FROM query_history
            WHERE user_id = ?
            AND created_at >= CURRENT_TIMESTAMP - INTERVAL '{days}' DAY
        """, [user_id]).fetchone()

        total_queries, successful_queries = query_stats
        summary['query_success_rate'] = (successful_queries / total_queries * 100) if total_queries > 0 else 0

        # Most accessed datasets
        summary['most_accessed_datasets'] = conn.execute(f"""
            SELECT dataset_name, last_accessed
            FROM datasets
            WHERE user_id = ? AND is_deleted = FALSE
            ORDER BY last_accessed DESC
            LIMIT 5
        """, [user_id]).fetchall()

        # Recent conversations
        summary['recent_conversations'] = conn.execute(f"""
            SELECT COUNT(*) FROM conversations
            WHERE user_id = ?
            AND created_at >= CURRENT_TIMESTAMP - INTERVAL '{days}' DAY
        """, [user_id]).fetchone()[0]

        return summary

    except Exception as e:
        print(f"Error getting user activity summary: {e}")
        return {}

def list_user_resources(user_id: str, resource_type: str = 'all') -> Dict[str, List]:
    """
    List all resources owned by a user

    Args:
        user_id: User ID
        resource_type: 'all', 'datasets', 'conversations', 'visualizations', or 'queries'

    Returns:
        Dictionary with lists of resources
    """
    conn = get_db_connection()
    resources = {}

    try:
        if resource_type in ['all', 'datasets']:
            datasets = conn.execute("""
                SELECT dataset_id, dataset_name, upload_date, row_count, file_size_bytes
                FROM datasets
                WHERE user_id = ? AND is_deleted = FALSE
                ORDER BY upload_date DESC
            """, [user_id]).fetchall()

            resources['datasets'] = [
                {
                    'dataset_id': d[0],
                    'dataset_name': d[1],
                    'upload_date': d[2].isoformat() if d[2] else None,
                    'row_count': d[3],
                    'file_size_bytes': d[4]
                }
                for d in datasets
            ]

        if resource_type in ['all', 'conversations']:
            conversations = conn.execute("""
                SELECT conversation_id, title, created_at, updated_at, dataset_id
                FROM conversations
                WHERE user_id = ? AND is_archived = FALSE
                ORDER BY updated_at DESC
            """, [user_id]).fetchall()

            resources['conversations'] = [
                {
                    'conversation_id': c[0],
                    'title': c[1],
                    'created_at': c[2].isoformat() if c[2] else None,
                    'updated_at': c[3].isoformat() if c[3] else None,
                    'dataset_id': c[4]
                }
                for c in conversations
            ]

        if resource_type in ['all', 'visualizations']:
            visualizations = conn.execute("""
                SELECT visualization_id, title, chart_type, created_at, dataset_id
                FROM saved_visualizations
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, [user_id]).fetchall()

            resources['visualizations'] = [
                {
                    'visualization_id': v[0],
                    'title': v[1],
                    'chart_type': v[2],
                    'created_at': v[3].isoformat() if v[3] else None,
                    'dataset_id': v[4]
                }
                for v in visualizations
            ]

        if resource_type in ['all', 'queries']:
            queries = conn.execute("""
                SELECT query_id, natural_language_query, success, created_at, dataset_id
                FROM query_history
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 50
            """, [user_id]).fetchall()

            resources['queries'] = [
                {
                    'query_id': q[0],
                    'query': q[1],
                    'success': q[2],
                    'created_at': q[3].isoformat() if q[3] else None,
                    'dataset_id': q[4]
                }
                for q in queries
            ]

        return resources

    except Exception as e:
        print(f"Error listing user resources: {e}")
        return {}

# ============================================================================
# OWNERSHIP TRANSFER
# ============================================================================

def transfer_dataset_ownership(dataset_id: str, from_user_id: str, to_user_id: str) -> Tuple[bool, Optional[str]]:
    """
    Transfer dataset ownership from one user to another

    Args:
        dataset_id: Dataset to transfer
        from_user_id: Current owner
        to_user_id: New owner

    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    conn = get_db_connection()

    # Verify current ownership
    is_owner, error = verify_dataset_ownership(dataset_id, from_user_id)
    if not is_owner:
        return False, error

    # Verify target user exists
    target_user = conn.execute("""
        SELECT user_id FROM users WHERE user_id = ? OR email = ?
    """, [to_user_id, to_user_id]).fetchone()

    if not target_user:
        return False, f"Target user not found: {to_user_id}"

    try:
        # Transfer dataset
        conn.execute("""
            UPDATE datasets
            SET user_id = ?
            WHERE dataset_id = ?
        """, [to_user_id, dataset_id])

        # Transfer associated conversations
        conn.execute("""
            UPDATE conversations
            SET user_id = ?
            WHERE dataset_id = ? AND user_id = ?
        """, [to_user_id, dataset_id, from_user_id])

        # Transfer associated visualizations
        conn.execute("""
            UPDATE saved_visualizations
            SET user_id = ?
            WHERE dataset_id = ? AND user_id = ?
        """, [to_user_id, dataset_id, from_user_id])

        # Note: query_history is kept with original user for audit purposes

        return True, None

    except Exception as e:
        return False, f"Error transferring ownership: {str(e)}"

# ============================================================================
# BULK OPERATIONS
# ============================================================================

def delete_all_user_data(user_id: str, hard_delete: bool = False) -> Dict[str, int]:
    """
    Delete or soft-delete all data for a user (GDPR compliance)

    Args:
        user_id: User ID
        hard_delete: If True, permanently delete. If False, soft delete.

    Returns:
        Dictionary with counts of deleted items
    """
    conn = get_db_connection()
    deleted = {}

    try:
        if hard_delete:
            # Get all dataset table names before deletion
            datasets = conn.execute("""
                SELECT table_name FROM datasets WHERE user_id = ?
            """, [user_id]).fetchall()

            # Drop all user data tables
            for (table_name,) in datasets:
                try:
                    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                except Exception as e:
                    print(f"Error dropping table {table_name}: {e}")

            # Delete metadata
            deleted['datasets'] = conn.execute("""
                DELETE FROM datasets WHERE user_id = ?
            """, [user_id]).fetchone()

            deleted['conversations'] = conn.execute("""
                DELETE FROM conversations WHERE user_id = ?
            """, [user_id]).fetchone()

            # Delete messages from user's conversations
            deleted['messages'] = conn.execute("""
                DELETE FROM messages
                WHERE conversation_id IN (
                    SELECT conversation_id FROM conversations WHERE user_id = ?
                )
            """, [user_id]).fetchone()

            deleted['visualizations'] = conn.execute("""
                DELETE FROM saved_visualizations WHERE user_id = ?
            """, [user_id]).fetchone()

            deleted['queries'] = conn.execute("""
                DELETE FROM query_history WHERE user_id = ?
            """, [user_id]).fetchone()

        else:
            # Soft delete
            deleted['datasets'] = conn.execute("""
                UPDATE datasets SET is_deleted = TRUE WHERE user_id = ?
            """, [user_id]).fetchone()

            deleted['conversations'] = conn.execute("""
                UPDATE conversations SET is_archived = TRUE WHERE user_id = ?
            """, [user_id]).fetchone()

        return deleted

    except Exception as e:
        print(f"Error deleting user data: {e}")
        return {}

def get_orphaned_tables() -> List[str]:
    """
    Find data tables that don't have corresponding metadata entries
    Useful for cleanup

    Returns:
        List of orphaned table names
    """
    conn = get_db_connection()

    try:
        # Get all tables that match user_data_* pattern
        all_tables = conn.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_name LIKE 'user_data_%'
        """).fetchall()

        # Get all table names from datasets metadata
        registered_tables = conn.execute("""
            SELECT table_name FROM datasets
        """).fetchall()

        registered_set = {t[0] for t in registered_tables}
        orphaned = [t[0] for t in all_tables if t[0] not in registered_set]

        return orphaned

    except Exception as e:
        print(f"Error finding orphaned tables: {e}")
        return []

def cleanup_orphaned_tables() -> int:
    """
    Remove orphaned data tables

    Returns:
        Number of tables cleaned up
    """
    conn = get_db_connection()
    orphaned = get_orphaned_tables()

    cleaned = 0
    for table_name in orphaned:
        try:
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            cleaned += 1
            print(f"[OK] Dropped orphaned table: {table_name}")
        except Exception as e:
            print(f"[ERROR] Failed to drop table {table_name}: {e}")

    return cleaned

# ============================================================================
# USER ANALYTICS
# ============================================================================

def get_user_storage_breakdown(user_id: str) -> List[Dict]:
    """
    Get storage usage breakdown by dataset

    Returns:
        List of datasets with storage info, sorted by size
    """
    conn = get_db_connection()

    try:
        results = conn.execute("""
            SELECT
                dataset_id,
                dataset_name,
                file_size_bytes,
                row_count,
                column_count,
                upload_date
            FROM datasets
            WHERE user_id = ? AND is_deleted = FALSE
            ORDER BY file_size_bytes DESC
        """, [user_id]).fetchall()

        return [
            {
                'dataset_id': r[0],
                'dataset_name': r[1],
                'file_size_bytes': r[2],
                'row_count': r[3],
                'column_count': r[4],
                'upload_date': r[5].isoformat() if r[5] else None
            }
            for r in results
        ]

    except Exception as e:
        print(f"Error getting storage breakdown: {e}")
        return []

def get_dataset_usage_stats(dataset_id: str) -> Dict:
    """
    Get usage statistics for a specific dataset

    Returns:
        Dictionary with usage metrics
    """
    conn = get_db_connection()

    try:
        stats = {}

        # Query count
        stats['query_count'] = conn.execute("""
            SELECT COUNT(*) FROM query_history WHERE dataset_id = ?
        """, [dataset_id]).fetchone()[0]

        # Conversation count
        stats['conversation_count'] = conn.execute("""
            SELECT COUNT(*) FROM conversations WHERE dataset_id = ?
        """, [dataset_id]).fetchone()[0]

        # Visualization count
        stats['visualization_count'] = conn.execute("""
            SELECT COUNT(*) FROM saved_visualizations WHERE dataset_id = ?
        """, [dataset_id]).fetchone()[0]

        # Last accessed
        dataset = get_dataset(dataset_id)
        if dataset:
            stats['last_accessed'] = dataset['last_accessed'].isoformat() if dataset['last_accessed'] else None

        # Most common queries
        stats['top_queries'] = conn.execute("""
            SELECT natural_language_query, COUNT(*) as count
            FROM query_history
            WHERE dataset_id = ?
            GROUP BY natural_language_query
            ORDER BY count DESC
            LIMIT 5
        """, [dataset_id]).fetchall()

        return stats

    except Exception as e:
        print(f"Error getting dataset usage stats: {e}")
        return {}
