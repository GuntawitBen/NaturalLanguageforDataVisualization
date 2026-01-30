"""
Main Proactive Agent orchestrator.

Coordinates signal detection, LLM interpretation, and exploration flow.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import pandas as pd

from .models import (
    Signal,
    Observation,
    ExplorationChoice,
    ProactiveInsights,
    ExploreRequest,
    ExploreResponse,
    ChooseRequest,
    ChooseResponse,
)
from .signal_detector import detect_all_signals
from .openai_client import ProactiveOpenAIClient
from .state_manager import session_manager
from .config import MAX_INSIGHTS, MAX_CHOICES_PER_OBSERVATION, SQL_TEMPLATES

from database.db_utils import get_dataset, query_dataset


class ProactiveAgent:
    """Main orchestrator for proactive data insights"""

    def __init__(self):
        self.openai_client = None  # Lazy init to avoid startup errors

    def _get_openai_client(self) -> ProactiveOpenAIClient:
        """Get or create OpenAI client (lazy initialization)"""
        if self.openai_client is None:
            self.openai_client = ProactiveOpenAIClient()
        return self.openai_client

    def get_insights(self, dataset_id: str) -> ProactiveInsights:
        """
        Compute insights for a dataset on-demand.

        This is the main entry point - called when user opens Insights tab.

        Args:
            dataset_id: Dataset identifier

        Returns:
            ProactiveInsights with signals, observations, and choices

        Raises:
            ValueError: If dataset not found
        """
        # Get dataset metadata
        dataset = get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset not found: {dataset_id}")

        table_name = dataset.get("table_name", "data")
        file_path = dataset.get("file_path")

        if not file_path:
            raise ValueError(f"Dataset has no file path: {dataset_id}")

        # Load data into DataFrame
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            raise ValueError(f"Failed to load dataset: {str(e)}")

        print(f"[PROACTIVE] Analyzing dataset {dataset_id}: {len(df)} rows, {len(df.columns)} columns")

        # Phase 1: Statistical signal detection
        signals = detect_all_signals(df, table_name)
        print(f"[PROACTIVE] Detected {len(signals)} signals")

        # Limit signals
        signals = signals[:MAX_INSIGHTS]

        # Phase 2: LLM interpretation - generate observations and choices
        observations = []
        choices = []

        openai_client = self._get_openai_client()

        for signal in signals:
            # Generate observation
            obs_text, importance, key_insight = openai_client.generate_observation(
                signal=signal,
                table_name=table_name,
                row_count=len(df),
                column_names=df.columns.tolist()
            )

            if not obs_text:
                # Fallback to basic observation
                obs_text = self._generate_fallback_observation(signal)
                importance = "medium"

            observation = Observation(
                observation_id=str(uuid.uuid4()),
                signal_id=signal.signal_id,
                text=obs_text,
                importance=importance or "medium"
            )
            observations.append(observation)

            # Generate exploration choices
            choice_data = openai_client.generate_exploration_choices(
                observation=observation,
                signal=signal,
                available_columns=df.columns.tolist()
            )

            if not choice_data:
                # Fallback to basic choices
                choice_data = self._generate_fallback_choices(signal)

            for cd in choice_data[:MAX_CHOICES_PER_OBSERVATION]:
                choice = ExplorationChoice(
                    choice_id=str(uuid.uuid4()),
                    observation_id=observation.observation_id,
                    text=cd.get("text", "Explore this further"),
                    suggested_chart=cd.get("suggested_chart", "table"),
                    sql_template=self._build_sql_template(signal, cd)
                )
                choices.append(choice)

        print(f"[PROACTIVE] Generated {len(observations)} observations, {len(choices)} choices")

        return ProactiveInsights(
            dataset_id=dataset_id,
            signals=signals,
            observations=observations,
            choices=choices,
            computed_at=datetime.utcnow()
        )

    def start_exploration(
        self,
        dataset_id: str,
        user_id: str,
        observation_id: Optional[str] = None
    ) -> ExploreResponse:
        """
        Start an exploration session.

        Args:
            dataset_id: Dataset to explore
            user_id: User identifier
            observation_id: Optional starting observation

        Returns:
            ExploreResponse with session info and available choices
        """
        # Compute insights if not cached
        insights = self.get_insights(dataset_id)

        # Create session
        session = session_manager.create_session(
            user_id=user_id,
            dataset_id=dataset_id,
            insights=insights,
            starting_observation_id=observation_id
        )

        current_obs = session_manager.get_current_observation(session.session_id)
        available_choices = session_manager.get_available_choices(session.session_id)

        return ExploreResponse(
            session_id=session.session_id,
            current_observation=current_obs,
            available_choices=available_choices,
            context={
                "dataset_id": dataset_id,
                "total_observations": len(insights.observations),
                "step": 0,
            }
        )

    def make_choice(
        self,
        session_id: str,
        choice_id: str
    ) -> ChooseResponse:
        """
        Process a user's exploration choice.

        Args:
            session_id: Session identifier
            choice_id: Selected choice

        Returns:
            ChooseResponse with SQL results and follow-up options
        """
        session = session_manager.get_session(session_id)
        if not session:
            return ChooseResponse(
                success=False,
                message="Session not found or expired"
            )

        insights = session_manager.get_insights(session_id)
        if not insights:
            return ChooseResponse(
                success=False,
                message="Session data not found"
            )

        # Find the selected choice
        selected_choice = None
        for choice in session_manager.get_available_choices(session_id):
            if choice.choice_id == choice_id:
                selected_choice = choice
                break

        if not selected_choice:
            return ChooseResponse(
                success=False,
                message="Choice not found"
            )

        # Find the observation and signal for this choice
        observation = None
        signal = None
        for obs in insights.observations:
            if obs.observation_id == selected_choice.observation_id:
                observation = obs
                for sig in insights.signals:
                    if sig.signal_id == obs.signal_id:
                        signal = sig
                        break
                break

        if not observation or not signal:
            return ChooseResponse(
                success=False,
                message="Could not find context for this choice"
            )

        # Execute SQL
        sql_query = selected_choice.sql_template
        results = []
        result_count = 0

        if sql_query:
            query_result = query_dataset(session.dataset_id, sql_query)

            if query_result.get("success"):
                # Format results
                columns = query_result.get("columns", [])
                data = query_result.get("data", [])
                result_count = query_result.get("row_count", 0)

                for row in data[:100]:  # Limit to 100 rows
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i] if i < len(row) else None
                        # Handle special types
                        if value is not None:
                            if hasattr(value, 'isoformat'):
                                value = value.isoformat()
                            elif isinstance(value, (bytes, bytearray)):
                                value = value.decode('utf-8', errors='replace')
                            try:
                                # Try to make JSON serializable
                                import json
                                json.dumps(value)
                            except (TypeError, ValueError):
                                value = str(value)
                        row_dict[col] = value
                    results.append(row_dict)

        # Record the choice
        session_manager.record_choice(
            session_id=session_id,
            choice_id=choice_id,
            sql_executed=sql_query,
            results=results
        )

        # Generate follow-up options using LLM
        follow_up_observation = None
        follow_up_choices = []

        if results:
            openai_client = self._get_openai_client()
            interpretation, follow_up_text, follow_up_data = openai_client.generate_follow_up(
                choice_text=selected_choice.text,
                result_count=result_count,
                result_columns=list(results[0].keys()) if results else [],
                sample_data=results[:5],
                signal=signal,
                observation=observation
            )

            if follow_up_text:
                follow_up_observation = Observation(
                    observation_id=str(uuid.uuid4()),
                    signal_id=signal.signal_id,
                    text=follow_up_text,
                    importance="medium"
                )

            for fd in follow_up_data[:MAX_CHOICES_PER_OBSERVATION]:
                follow_up_choices.append(ExplorationChoice(
                    choice_id=str(uuid.uuid4()),
                    observation_id=follow_up_observation.observation_id if follow_up_observation else observation.observation_id,
                    text=fd.get("text", "Continue exploring"),
                    suggested_chart=fd.get("suggested_chart", "table"),
                    sql_template=self._build_sql_template(signal, fd)
                ))

        # Update session with follow-ups
        session_manager.update_follow_up(
            session_id=session_id,
            new_observation=follow_up_observation,
            new_choices=follow_up_choices
        )

        return ChooseResponse(
            success=True,
            sql_executed=sql_query,
            results=results,
            result_count=result_count,
            follow_up_observation=follow_up_observation,
            follow_up_choices=follow_up_choices,
            message=f"Found {result_count} rows"
        )

    def get_session_state(self, session_id: str) -> Optional[ExploreResponse]:
        """
        Get the current state of an exploration session.

        Args:
            session_id: Session identifier

        Returns:
            ExploreResponse with current state, or None if not found
        """
        session = session_manager.get_session(session_id)
        if not session:
            return None

        current_obs = session_manager.get_current_observation(session_id)
        available_choices = session_manager.get_available_choices(session_id)

        return ExploreResponse(
            session_id=session_id,
            current_observation=current_obs,
            available_choices=available_choices,
            context={
                "dataset_id": session.dataset_id,
                "step": session.current_state.get("step", 0),
                "exploration_path": session.exploration_path,
            }
        )

    def _generate_fallback_observation(self, signal: Signal) -> str:
        """Generate a basic observation when LLM fails."""
        signal_type = signal.signal_type.value
        columns = ", ".join(signal.columns)

        fallbacks = {
            "trend": f"A trend pattern was detected in {columns} with strength {signal.strength:.2f}",
            "outlier": f"Outliers were detected in {columns}",
            "dominance": f"One category dominates in {columns}",
            "seasonality": f"A seasonal pattern was detected in {columns}",
            "imbalance": f"The distribution is uneven in {columns}",
        }

        return fallbacks.get(signal_type, f"A pattern was detected in {columns}")

    def _generate_fallback_choices(self, signal: Signal) -> List[Dict[str, Any]]:
        """Generate basic exploration choices when LLM fails."""
        signal_type = signal.signal_type.value

        fallback_choices = {
            "trend": [
                {"text": "View the trend over time", "intent": "explore_trend", "suggested_chart": "line_with_trendline"},
                {"text": "See a breakdown by category", "intent": "drill_down", "suggested_chart": "multi_line"},
            ],
            "outlier": [
                {"text": "Investigate the outliers", "intent": "investigate", "suggested_chart": "scatter_highlight"},
                {"text": "See the distribution", "intent": "see_distribution", "suggested_chart": "histogram"},
            ],
            "dominance": [
                {"text": "See the breakdown", "intent": "see_breakdown", "suggested_chart": "pie"},
                {"text": "View changes over time", "intent": "compare_over_time", "suggested_chart": "stacked_bar"},
            ],
            "seasonality": [
                {"text": "View the full pattern", "intent": "view_pattern", "suggested_chart": "line_full"},
                {"text": "Compare different periods", "intent": "compare_periods", "suggested_chart": "multi_line"},
            ],
            "imbalance": [
                {"text": "Compare the distribution", "intent": "compare_distribution", "suggested_chart": "histogram"},
                {"text": "See the breakdown", "intent": "see_breakdown", "suggested_chart": "bar"},
            ],
        }

        return fallback_choices.get(signal_type, [
            {"text": "Explore further", "intent": "explore", "suggested_chart": "table"}
        ])

    def _build_sql_template(self, signal: Signal, choice_data: Dict[str, Any]) -> Optional[str]:
        """Build SQL template for an exploration choice."""
        intent = choice_data.get("intent", "")
        metadata = signal.metadata
        table_name = metadata.get("table_name", "data")

        signal_type = signal.signal_type.value

        try:
            if signal_type == "trend":
                date_col = metadata.get("date_column", "")
                value_col = metadata.get("value_column", "")

                if intent == "explore_trend":
                    return SQL_TEMPLATES["trend_over_time"].format(
                        date_column=date_col,
                        value_column=value_col,
                        table_name=table_name
                    ).strip()
                elif intent == "drill_down":
                    groupby = choice_data.get("suggested_groupby")
                    if groupby:
                        return SQL_TEMPLATES["trend_by_category"].format(
                            date_column=date_col,
                            category_column=groupby,
                            value_column=value_col,
                            table_name=table_name
                        ).strip()

            elif signal_type == "outlier":
                column = metadata.get("column", "")
                lower = metadata.get("lower_bound", 0)
                upper = metadata.get("upper_bound", 0)

                if intent == "investigate":
                    return SQL_TEMPLATES["outlier_details"].format(
                        table_name=table_name,
                        column=column,
                        lower_bound=lower,
                        upper_bound=upper
                    ).strip()
                elif intent == "see_distribution":
                    return SQL_TEMPLATES["distribution"].format(
                        table_name=table_name,
                        column=column
                    ).strip()

            elif signal_type == "dominance":
                column = metadata.get("column", "")

                if intent in ("see_breakdown", "drill_into_dominant"):
                    return SQL_TEMPLATES["category_breakdown"].format(
                        category_column=column,
                        table_name=table_name
                    ).strip()

            elif signal_type == "imbalance":
                column = metadata.get("column", "")

                if intent in ("compare_distribution", "see_breakdown"):
                    return SQL_TEMPLATES["category_breakdown"].format(
                        category_column=column,
                        table_name=table_name
                    ).strip()

        except Exception as e:
            print(f"[WARNING] Failed to build SQL template: {e}")

        # Fallback: simple select
        return f"SELECT * FROM {table_name} LIMIT 100"


# Global agent instance
proactive_agent = ProactiveAgent()
