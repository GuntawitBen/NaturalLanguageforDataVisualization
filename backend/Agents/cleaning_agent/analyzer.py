"""
Main CleaningAgent orchestrator class.
"""

import pandas as pd
from typing import Optional, List, Dict, Any

from .models import (
    Problem,
    ProblemWithOptions,
    SessionState,
    OperationResult,
    StartSessionResponse,
    DatasetStats
)
from .detection import detect_all_problems
from .config import CLEANING_OPERATIONS
from .state_manager import session_manager
from .openai_client import CleaningOpenAIClient


class CleaningAgent:
    """Main orchestrator for interactive data cleaning"""

    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize CleaningAgent

        Args:
            openai_api_key: Optional OpenAI API key
        """
        try:
            self.openai_client = CleaningOpenAIClient(api_key=openai_api_key)
        except ValueError as e:
            print(f"[WARNING] OpenAI client initialization failed: {e}")
            print("[INFO] Will use fallback pros/cons from config.")
            self.openai_client = None

    def start_session(
        self,
        temp_file_path: str,
        dataset_name: str
    ) -> StartSessionResponse:
        """
        Start a new cleaning session.

        Args:
            temp_file_path: Path to the temporary CSV file
            dataset_name: Name of the dataset

        Returns:
            StartSessionResponse with session info and first problem
        """
        # Load DataFrame to detect problems
        df = pd.read_csv(temp_file_path)

        # Detect all problems
        problems = detect_all_problems(df)

        # Create session
        session_id = session_manager.create_session(temp_file_path, dataset_name, problems)
        session = session_manager.get_session(session_id)

        # Get session state
        session_state = session.to_session_state()

        # Generate summary message
        if len(problems) == 0:
            summary = f"Great news! No data quality issues detected in '{dataset_name}'. Your dataset is ready for visualization."
            first_problem = None
        else:
            critical_count = sum(1 for p in problems if p.severity == "critical")
            warning_count = sum(1 for p in problems if p.severity == "warning")
            info_count = sum(1 for p in problems if p.severity == "info")

            summary_parts = [f"Detected {len(problems)} data quality issue(s) in '{dataset_name}'"]
            if critical_count > 0:
                summary_parts.append(f"{critical_count} critical")
            if warning_count > 0:
                summary_parts.append(f"{warning_count} warning")
            if info_count > 0:
                summary_parts.append(f"{info_count} info")

            summary = ": ".join([summary_parts[0], ", ".join(summary_parts[1:])]) + "."

            # Get first problem with options
            first_problem = self.get_next_problem(session_id)

        return StartSessionResponse(
            session_id=session_id,
            session_state=session_state,
            first_problem=first_problem,
            summary=summary
        )

    def get_next_problem(self, session_id: str) -> Optional[ProblemWithOptions]:
        """
        Get the next problem with cleaning options.

        Args:
            session_id: Session ID

        Returns:
            ProblemWithOptions or None if no more problems
        """
        session = session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Check if we have more problems
        if session.current_problem_index >= len(session.problems):
            return None

        # Get current problem
        current_problem = session.problems[session.current_problem_index]

        # Generate cleaning options
        options = self._generate_options_for_problem(current_problem, session.df)

        # Create ProblemWithOptions
        problem_with_options = ProblemWithOptions(
            problem=current_problem,
            options=options,
            current_index=session.current_problem_index,
            total_problems=len(session.problems)
        )

        return problem_with_options

    def apply_operation(
        self,
        session_id: str,
        option_id: str
    ) -> OperationResult:
        """
        Apply a cleaning operation.

        Args:
            session_id: Session ID
            option_id: Option ID to apply

        Returns:
            OperationResult with stats and next problem
        """
        session = session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Get current problem
        current_problem = session.problems[session.current_problem_index]

        # Find the selected option
        current_problem_with_options = self.get_next_problem(session_id)
        selected_option = next(
            (opt for opt in current_problem_with_options.options if opt.option_id == option_id),
            None
        )

        if not selected_option:
            raise ValueError(f"Option not found: {option_id}")

        # Get stats before operation
        stats_before = session.get_current_stats()

        # Apply operation
        operation_record = session_manager.apply_operation(
            session_id=session_id,
            operation_type=selected_option.operation_type,
            parameters=selected_option.parameters,
            option_id=option_id,
            problem_id=current_problem.problem_id
        )

        # Move to next problem
        session_manager.move_to_next_problem(session_id)

        # Get next problem
        next_problem = self.get_next_problem(session_id)

        # Determine if session is complete
        session_complete = next_problem is None

        return OperationResult(
            success=True,
            message=f"Applied: {selected_option.option_name}",
            stats_before=stats_before,
            stats_after=operation_record.stats_after,
            next_problem=next_problem,
            session_complete=session_complete
        )

    def skip_problem(self, session_id: str) -> ProblemWithOptions:
        """
        Skip the current problem and move to next.

        Args:
            session_id: Session ID

        Returns:
            Next ProblemWithOptions or None
        """
        session_manager.skip_problem(session_id)
        return self.get_next_problem(session_id)

    def undo_last(self, session_id: str) -> OperationResult:
        """
        Undo the last operation.

        Args:
            session_id: Session ID

        Returns:
            OperationResult with restored stats
        """
        session = session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Get stats before undo
        stats_before = session.get_current_stats()

        # Undo operation
        success = session_manager.undo_last_operation(session_id)

        if not success:
            return OperationResult(
                success=False,
                message="No operations to undo",
                stats_before=stats_before,
                stats_after=stats_before,
                next_problem=None,
                session_complete=False
            )

        # Get stats after undo
        stats_after = session.get_current_stats()

        # Get current problem
        next_problem = self.get_next_problem(session_id)

        return OperationResult(
            success=True,
            message="Last operation undone successfully",
            stats_before=stats_before,
            stats_after=stats_after,
            next_problem=next_problem,
            session_complete=False
        )

    def get_session_state(self, session_id: str) -> SessionState:
        """
        Get current session state.

        Args:
            session_id: Session ID

        Returns:
            SessionState
        """
        session = session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        return session.to_session_state()

    def _generate_options_for_problem(
        self,
        problem: Problem,
        df: pd.DataFrame
    ) -> List:
        """
        Generate cleaning options for a problem.

        Args:
            problem: Problem object
            df: Current DataFrame

        Returns:
            List of CleaningOption objects
        """
        # Get operation templates for this problem type
        problem_type_key = problem.problem_type.value
        operation_templates = CLEANING_OPERATIONS.get(problem_type_key, {})

        if not operation_templates:
            return []

        # Convert templates to list format for GPT-4
        template_list = []
        for op_key, op_config in operation_templates.items():
            # Check if this option should be included based on missing percentage
            if "min_missing_percentage" in op_config:
                # Get missing percentage from problem metadata
                missing_percentage = problem.metadata.get("null_percentage", 0)
                if missing_percentage < op_config["min_missing_percentage"]:
                    # Skip this option if missing percentage is too low
                    continue

            template = {
                "name": op_config["name"],
                "operation_type": op_config["function"],
                "parameters": op_config["parameters"].copy(),
                "description": op_config["description"]
            }

            # Fill in affected columns for missing values and outliers
            if problem.affected_columns:
                if "columns" in template["parameters"]:
                    template["parameters"]["columns"] = problem.affected_columns

            # For duplicate columns, fill in columns to remove
            if problem_type_key == "duplicates_columns":
                columns_to_remove = problem.metadata.get("columns_to_remove", [])
                if "columns" in template["parameters"]:
                    template["parameters"]["columns"] = columns_to_remove

            template_list.append(template)

        # Get column statistics for context
        column_stats = {}
        for col in problem.affected_columns:
            if col in df.columns:
                col_stats = {
                    "dtype": str(df[col].dtype),
                    "non_null_count": int(df[col].notna().sum()),
                    "null_count": int(df[col].isna().sum())
                }

                # Add numeric stats if applicable
                if pd.api.types.is_numeric_dtype(df[col]):
                    col_stats.update({
                        "min": float(df[col].min()) if df[col].notna().any() else None,
                        "max": float(df[col].max()) if df[col].notna().any() else None,
                        "mean": float(df[col].mean()) if df[col].notna().any() else None,
                        "median": float(df[col].median()) if df[col].notna().any() else None
                    })

                column_stats[col] = col_stats

        # Generate options with GPT-4 analysis (or fallback)
        if self.openai_client:
            options = self.openai_client.generate_options_analysis(
                problem=problem,
                option_templates=template_list,
                column_stats=column_stats
            )
        else:
            # Use fallback
            options = self.openai_client._create_fallback_options(template_list, problem) if self.openai_client else []

        return options


# Global agent instance
cleaning_agent = CleaningAgent()
