"""
Session state management for cleaning operations.
"""

import pandas as pd
import uuid
from typing import Dict, List, Optional
from datetime import datetime
import os
import pickle
from pathlib import Path

from .models import (
    SessionState,
    Problem,
    OperationRecord,
    DatasetStats
)
from .config import SESSION_CONFIG
from .operations import execute_operation


class SessionData:
    """Internal session data storage"""

    def __init__(self, session_id: str, temp_file_path: str, dataset_name: str, df: pd.DataFrame, problems: List[Problem]):
        self.session_id = session_id
        self.temp_file_path = temp_file_path
        self.dataset_name = dataset_name
        self.df = df
        self.problems = problems
        self.current_problem_index = 0
        self.skipped_problems: List[str] = []
        self.operation_history: List[OperationRecord] = []
        self.backups: List[str] = []  # Paths to backup files
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

    def get_current_stats(self) -> DatasetStats:
        """Get current dataset statistics"""
        missing_count = self.df.isna().sum().sum()
        duplicate_count = self.df.duplicated().sum()

        # Count outliers (simple check on numeric columns)
        outlier_count = 0
        for column in self.df.select_dtypes(include=['number']).columns:
            values = self.df[column].dropna()
            if len(values) >= 4:
                Q1 = values.quantile(0.25)
                Q3 = values.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                outlier_count += ((self.df[column] < lower_bound) | (self.df[column] > upper_bound)).sum()

        return DatasetStats(
            row_count=len(self.df),
            column_count=len(self.df.columns),
            missing_value_count=int(missing_count),
            duplicate_row_count=int(duplicate_count),
            outlier_count=int(outlier_count)
        )

    def to_session_state(self) -> SessionState:
        """Convert to SessionState model"""
        return SessionState(
            session_id=self.session_id,
            temp_file_path=self.temp_file_path,
            dataset_name=self.dataset_name,
            problems=self.problems,
            current_problem_index=self.current_problem_index,
            skipped_problems=self.skipped_problems,
            operation_history=self.operation_history,
            current_stats=self.get_current_stats(),
            created_at=self.created_at,
            updated_at=self.updated_at
        )


class SessionManager:
    """Manages cleaning sessions and operations"""

    def __init__(self):
        self.sessions: Dict[str, SessionData] = {}
        self._backup_dir = Path("./backups/cleaning_sessions")
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def create_session(self, temp_file_path: str, dataset_name: str, problems: List[Problem]) -> str:
        """
        Create a new cleaning session.

        Args:
            temp_file_path: Path to the temporary CSV file
            dataset_name: Name of the dataset
            problems: List of detected problems

        Returns:
            Session ID
        """
        # Load DataFrame
        df = pd.read_csv(temp_file_path)

        # Generate session ID
        session_id = str(uuid.uuid4())

        # Create session data
        session_data = SessionData(
            session_id=session_id,
            temp_file_path=temp_file_path,
            dataset_name=dataset_name,
            df=df,
            problems=problems
        )

        self.sessions[session_id] = session_data
        return session_id

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session data by ID"""
        return self.sessions.get(session_id)

    def save_backup(self, session_id: str) -> str:
        """
        Save current DataFrame as backup before operation.

        Args:
            session_id: Session ID

        Returns:
            Path to backup file
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Create backup path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{session_id}_{timestamp}.pkl"
        backup_path = self._backup_dir / backup_filename

        # Save DataFrame using pickle (faster than CSV for backups)
        with open(backup_path, 'wb') as f:
            pickle.dump(session.df, f)

        # Add to backup list
        session.backups.append(str(backup_path))

        # Cleanup old backups if exceeding limit
        max_backups = SESSION_CONFIG["max_backups"]
        if len(session.backups) > max_backups:
            old_backup = session.backups.pop(0)
            try:
                os.remove(old_backup)
            except:
                pass  # Ignore errors if file already deleted

        return str(backup_path)

    def apply_operation(
        self,
        session_id: str,
        operation_type: str,
        parameters: Dict,
        option_id: str,
        problem_id: str
    ) -> OperationRecord:
        """
        Apply a cleaning operation to the session's DataFrame.

        Args:
            session_id: Session ID
            operation_type: Type of operation (e.g., "drop_missing_rows")
            parameters: Operation parameters
            option_id: ID of the selected option
            problem_id: ID of the problem being addressed

        Returns:
            OperationRecord with operation details
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Get stats before operation
        stats_before = session.get_current_stats()

        # Save backup before operation
        backup_path = self.save_backup(session_id)

        # Execute operation
        df_cleaned, message = execute_operation(operation_type, session.df, parameters)

        # Update session DataFrame
        session.df = df_cleaned

        # Update temp file
        session.df.to_csv(session.temp_file_path, index=False)

        # Get stats after operation
        stats_after = session.get_current_stats()

        # Create operation record
        operation_record = OperationRecord(
            operation_id=str(uuid.uuid4()),
            problem_id=problem_id,
            option_id=option_id,
            operation_type=operation_type,
            parameters=parameters,
            timestamp=datetime.now().isoformat(),
            stats_before=stats_before,
            stats_after=stats_after,
            backup_path=backup_path
        )

        # Add to history
        session.operation_history.append(operation_record)
        session.updated_at = datetime.now().isoformat()

        return operation_record

    def undo_last_operation(self, session_id: str) -> bool:
        """
        Undo the last operation by restoring from backup.

        Args:
            session_id: Session ID

        Returns:
            True if undo successful, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        if len(session.operation_history) == 0:
            return False

        # Get last operation
        last_operation = session.operation_history[-1]

        # Restore from backup
        backup_path = last_operation.backup_path
        if not backup_path or not os.path.exists(backup_path):
            return False

        try:
            # Load backup
            with open(backup_path, 'rb') as f:
                df_restored = pickle.load(f)

            # Update session DataFrame
            session.df = df_restored

            # Update temp file
            session.df.to_csv(session.temp_file_path, index=False)

            # Remove last operation from history
            session.operation_history.pop()
            session.updated_at = datetime.now().isoformat()

            # Move back to previous problem if current problem was completed
            if session.current_problem_index > 0:
                session.current_problem_index -= 1

            return True
        except Exception as e:
            print(f"Error undoing operation: {e}")
            return False

    def skip_problem(self, session_id: str) -> bool:
        """
        Skip the current problem and move to next.

        Args:
            session_id: Session ID

        Returns:
            True if skipped successfully
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        if session.current_problem_index < len(session.problems):
            current_problem = session.problems[session.current_problem_index]
            session.skipped_problems.append(current_problem.problem_id)
            session.current_problem_index += 1
            session.updated_at = datetime.now().isoformat()
            return True

        return False

    def move_to_next_problem(self, session_id: str):
        """Move to the next problem after completing current one"""
        session = self.get_session(session_id)
        if session:
            session.current_problem_index += 1
            session.updated_at = datetime.now().isoformat()

    def delete_session(self, session_id: str):
        """Delete a session and cleanup backups"""
        session = self.get_session(session_id)
        if session:
            # Cleanup all backups
            for backup_path in session.backups:
                try:
                    os.remove(backup_path)
                except:
                    pass

            # Remove session
            del self.sessions[session_id]

    def cleanup_old_sessions(self, max_age_seconds: int = None):
        """
        Cleanup sessions older than specified age.

        Args:
            max_age_seconds: Maximum age in seconds (default from config)
        """
        if max_age_seconds is None:
            max_age_seconds = SESSION_CONFIG["session_timeout"]

        current_time = datetime.now()
        sessions_to_delete = []

        for session_id, session in self.sessions.items():
            created_at = datetime.fromisoformat(session.created_at)
            age = (current_time - created_at).total_seconds()

            if age > max_age_seconds:
                sessions_to_delete.append(session_id)

        for session_id in sessions_to_delete:
            self.delete_session(session_id)

    def cleanup_orphaned_backups(self, max_age_hours: int = 24):
        """
        Cleanup orphaned backup files that don't belong to any active session.
        Also removes backup files older than max_age_hours.

        Args:
            max_age_hours: Maximum age of backup files in hours (default 24)
        """
        try:
            # Get all active backup paths from sessions
            active_backups = set()
            for session in self.sessions.values():
                active_backups.update(session.backups)

            # Scan backup directory
            if not self._backup_dir.exists():
                return

            current_time = datetime.now()
            removed_count = 0

            for backup_file in self._backup_dir.glob("*.pkl"):
                try:
                    # Get file modification time
                    file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    age_hours = (current_time - file_mtime).total_seconds() / 3600

                    # Remove if orphaned OR too old
                    if str(backup_file) not in active_backups or age_hours > max_age_hours:
                        backup_file.unlink()
                        removed_count += 1
                except Exception as e:
                    print(f"[WARNING] Failed to remove backup file {backup_file}: {e}")
                    continue

            if removed_count > 0:
                print(f"[INFO] Cleaned up {removed_count} orphaned/old backup files")

        except Exception as e:
            print(f"[ERROR] Failed to cleanup orphaned backups: {e}")


# Global session manager instance
session_manager = SessionManager()
