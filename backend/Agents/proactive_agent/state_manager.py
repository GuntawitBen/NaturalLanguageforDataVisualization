"""
State manager for exploration sessions.
"""

from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
import uuid
import threading

from .models import (
    ExplorationSession,
    Signal,
    Observation,
    ExplorationChoice,
    ProactiveInsights,
)


class ExplorationSessionManager:
    """Manages exploration sessions in memory with thread safety."""

    def __init__(self, session_timeout_minutes: int = 60):
        self._sessions: Dict[str, ExplorationSession] = {}
        self._session_data: Dict[str, Dict[str, Any]] = {}  # Additional session data
        self._lock = threading.Lock()
        self._session_timeout = timedelta(minutes=session_timeout_minutes)

    def create_session(
        self,
        user_id: str,
        dataset_id: str,
        insights: ProactiveInsights,
        starting_observation_id: Optional[str] = None
    ) -> ExplorationSession:
        """
        Create a new exploration session.

        Args:
            user_id: User identifier
            dataset_id: Dataset being explored
            insights: Pre-computed insights for the dataset
            starting_observation_id: Optional observation to start from

        Returns:
            New ExplorationSession
        """
        with self._lock:
            session_id = str(uuid.uuid4())
            now = datetime.utcnow()

            # Find starting observation
            current_observation = None
            if starting_observation_id:
                for obs in insights.observations:
                    if obs.observation_id == starting_observation_id:
                        current_observation = obs
                        break

            if not current_observation and insights.observations:
                current_observation = insights.observations[0]

            # Get choices for current observation
            available_choices = []
            if current_observation:
                available_choices = [
                    c for c in insights.choices
                    if c.observation_id == current_observation.observation_id
                ]

            session = ExplorationSession(
                session_id=session_id,
                user_id=user_id,
                dataset_id=dataset_id,
                exploration_path=[],
                current_state={
                    "current_observation_id": current_observation.observation_id if current_observation else None,
                    "available_choice_ids": [c.choice_id for c in available_choices],
                    "step": 0,
                },
                created_at=now,
            )

            self._sessions[session_id] = session

            # Store additional data for the session
            self._session_data[session_id] = {
                "insights": insights,
                "current_observation": current_observation,
                "available_choices": available_choices,
                "last_accessed": now,
            }

            return session

    def get_session(self, session_id: str) -> Optional[ExplorationSession]:
        """Get a session by ID."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                self._session_data[session_id]["last_accessed"] = datetime.utcnow()
            return session

    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get additional session data."""
        with self._lock:
            return self._session_data.get(session_id)

    def get_current_observation(self, session_id: str) -> Optional[Observation]:
        """Get the current observation for a session."""
        data = self.get_session_data(session_id)
        return data.get("current_observation") if data else None

    def get_available_choices(self, session_id: str) -> List[ExplorationChoice]:
        """Get available choices for the current observation."""
        data = self.get_session_data(session_id)
        return data.get("available_choices", []) if data else []

    def get_insights(self, session_id: str) -> Optional[ProactiveInsights]:
        """Get the insights for a session."""
        data = self.get_session_data(session_id)
        return data.get("insights") if data else None

    def record_choice(
        self,
        session_id: str,
        choice_id: str,
        sql_executed: Optional[str],
        results: Optional[List[Dict[str, Any]]],
    ) -> bool:
        """
        Record a choice made by the user.

        Args:
            session_id: Session identifier
            choice_id: Choice that was selected
            sql_executed: SQL that was executed
            results: Query results

        Returns:
            True if successful, False if session not found
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False

            data = self._session_data.get(session_id)
            if not data:
                return False

            # Find the chosen choice
            chosen_choice = None
            for choice in data.get("available_choices", []):
                if choice.choice_id == choice_id:
                    chosen_choice = choice
                    break

            if not chosen_choice:
                return False

            # Record in exploration path
            session.exploration_path.append({
                "step": session.current_state.get("step", 0),
                "choice_id": choice_id,
                "choice_text": chosen_choice.text,
                "sql_executed": sql_executed,
                "result_count": len(results) if results else 0,
                "timestamp": datetime.utcnow().isoformat(),
            })

            # Update step
            session.current_state["step"] = session.current_state.get("step", 0) + 1
            data["last_accessed"] = datetime.utcnow()

            return True

    def update_follow_up(
        self,
        session_id: str,
        new_observation: Optional[Observation],
        new_choices: List[ExplorationChoice],
    ) -> bool:
        """
        Update session with follow-up observation and choices.

        Args:
            session_id: Session identifier
            new_observation: New observation based on results
            new_choices: New exploration choices

        Returns:
            True if successful
        """
        with self._lock:
            session = self._sessions.get(session_id)
            data = self._session_data.get(session_id)

            if not session or not data:
                return False

            data["current_observation"] = new_observation
            data["available_choices"] = new_choices

            if new_observation:
                session.current_state["current_observation_id"] = new_observation.observation_id

            session.current_state["available_choice_ids"] = [c.choice_id for c in new_choices]

            return True

    def cleanup_old_sessions(self) -> int:
        """
        Remove sessions older than the timeout.

        Returns:
            Number of sessions removed
        """
        with self._lock:
            now = datetime.utcnow()
            expired = []

            for session_id, data in self._session_data.items():
                last_accessed = data.get("last_accessed", now)
                if now - last_accessed > self._session_timeout:
                    expired.append(session_id)

            for session_id in expired:
                del self._sessions[session_id]
                del self._session_data[session_id]

            if expired:
                print(f"[INFO] Cleaned up {len(expired)} expired exploration sessions")

            return len(expired)


# Create singleton instance
session_manager = ExplorationSessionManager()
