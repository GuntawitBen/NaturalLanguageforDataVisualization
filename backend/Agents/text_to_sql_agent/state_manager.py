"""
Session and state management for the Text-to-SQL agent.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from threading import Lock

from .models import SessionState, SchemaContext, Message, ColumnInfo
from .config import SESSION_CONFIG, TOKEN_CONFIG
from database.db_utils import get_dataset


class SessionManager:
    """Manages text-to-SQL sessions with thread-safe operations"""

    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}
        self._lock = Lock()

    def create_session(
        self,
        dataset_id: str,
        schema: SchemaContext
    ) -> SessionState:
        """
        Create a new session for a dataset

        Args:
            dataset_id: Dataset identifier
            schema: Schema context for the dataset

        Returns:
            New SessionState
        """
        session_id = str(uuid.uuid4())
        now = datetime.now()

        session = SessionState(
            session_id=session_id,
            dataset_id=dataset_id,
            schema=schema,
            messages=[],
            created_at=now,
            last_activity=now
        )

        with self._lock:
            self._sessions[session_id] = session

        print(f"[SESSION] Created session {session_id} for dataset {dataset_id}")
        return session

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        Get a session by ID

        Args:
            session_id: Session identifier

        Returns:
            SessionState or None if not found/expired
        """
        with self._lock:
            session = self._sessions.get(session_id)

            if session is None:
                return None

            # Check if session has expired
            timeout = timedelta(seconds=SESSION_CONFIG["session_timeout_seconds"])
            if datetime.now() - session.last_activity > timeout:
                print(f"[SESSION] Session {session_id} has expired")
                del self._sessions[session_id]
                return None

            return session

    def update_activity(self, session_id: str) -> bool:
        """
        Update the last activity timestamp for a session

        Args:
            session_id: Session identifier

        Returns:
            True if session exists and was updated
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.last_activity = datetime.now()
                return True
            return False

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sql_query: Optional[str] = None
    ) -> bool:
        """
        Add a message to a session's conversation history

        Args:
            session_id: Session identifier
            role: Message role ("user" or "assistant")
            content: Message content
            sql_query: SQL query (if any)

        Returns:
            True if message was added
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False

            message = Message(
                role=role,
                content=content,
                sql_query=sql_query
            )
            session.messages.append(message)

            # Trim messages if exceeding limit
            max_messages = SESSION_CONFIG["max_messages_per_session"]
            if len(session.messages) > max_messages:
                session.messages = session.messages[-max_messages:]

            session.last_activity = datetime.now()
            return True

    def get_messages(self, session_id: str) -> List[Message]:
        """
        Get conversation history for a session

        Args:
            session_id: Session identifier

        Returns:
            List of messages or empty list
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                return session.messages.copy()
            return []

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                print(f"[SESSION] Deleted session {session_id}")
                return True
            return False

    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions

        Returns:
            Number of sessions cleaned up
        """
        timeout = timedelta(seconds=SESSION_CONFIG["session_timeout_seconds"])
        now = datetime.now()
        expired_count = 0

        with self._lock:
            expired_ids = [
                sid for sid, session in self._sessions.items()
                if now - session.last_activity > timeout
            ]

            for sid in expired_ids:
                del self._sessions[sid]
                expired_count += 1

        if expired_count > 0:
            print(f"[SESSION] Cleaned up {expired_count} expired sessions")

        return expired_count

    def get_active_session_count(self) -> int:
        """Get count of active sessions"""
        with self._lock:
            return len(self._sessions)


def build_schema_context(dataset_id: str) -> Optional[SchemaContext]:
    """
    Build schema context from a dataset

    Args:
        dataset_id: Dataset identifier

    Returns:
        SchemaContext or None if dataset not found
    """
    # Get dataset metadata
    dataset = get_dataset(dataset_id)
    if not dataset:
        return None

    table_name = dataset['table_name']
    row_count = dataset['row_count']
    columns_info = dataset.get('columns_info', [])

    # Build column info with sample values for VARCHAR columns
    columns = []

    # Get sample values for string columns from database
    from database.db_init import get_db_connection
    conn = get_db_connection()

    for col_data in columns_info:
        col_name = col_data['name']
        col_type = col_data['type']

        sample_values = None

        # Get sample values for VARCHAR columns
        if col_type.upper() == 'VARCHAR':
            try:
                max_samples = TOKEN_CONFIG["max_sample_values"]
                result = conn.execute(f"""
                    SELECT DISTINCT "{col_name}"
                    FROM {table_name}
                    WHERE "{col_name}" IS NOT NULL
                    LIMIT {max_samples}
                """).fetchall()

                sample_values = [str(row[0]) for row in result if row[0]]
            except Exception as e:
                print(f"[WARNING] Failed to get sample values for {col_name}: {e}")

        columns.append(ColumnInfo(
            name=col_name,
            type=col_type,
            sample_values=sample_values
        ))

    return SchemaContext(
        table_name=table_name,
        columns=columns,
        row_count=row_count
    )


# Global session manager instance
session_manager = SessionManager()
