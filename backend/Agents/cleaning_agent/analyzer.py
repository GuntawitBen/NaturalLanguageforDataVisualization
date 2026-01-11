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


class CleaningAgent:
    """Main orchestrator for interactive data cleaning"""

    def __init__(self, enable_gpt_recommendations: bool = True):
        """
        Initialize CleaningAgent

        Args:
            enable_gpt_recommendations: Whether to enable GPT recommendations (default True)

        Note: Uses static pros/cons from config, but GPT for recommendations.
        """
        self.enable_gpt_recommendations = enable_gpt_recommendations

        # Initialize OpenAI client for recommendations
        if self.enable_gpt_recommendations:
            try:
                from .openai_client import CleaningOpenAIClient
                self.openai_client = CleaningOpenAIClient()
                print("[INFO] OpenAI client initialized for recommendations")
            except Exception as e:
                print(f"[WARNING] Failed to initialize OpenAI client: {e}")
                print("[INFO] GPT recommendations will be disabled")
                self.openai_client = None
                self.enable_gpt_recommendations = False
        else:
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
        # Store dataset name for later use in recommendations
        self._current_dataset_name = dataset_name

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

        # Generate cleaning options with GPT recommendation
        options, recommendation = self._generate_options_for_problem(current_problem, session.df)

        # Create ProblemWithOptions with recommendation
        problem_with_options = ProblemWithOptions(
            problem=current_problem,
            options=options,
            current_index=session.current_problem_index,
            total_problems=len(session.problems),
            recommendation=recommendation
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
    ) -> Tuple[List, Optional]:
        """
        Generate cleaning options for a problem with GPT recommendation.

        Args:
            problem: Problem object
            df: Current DataFrame

        Returns:
            Tuple of (List of CleaningOption objects, Optional GPTRecommendation)
        """
        # Get operation templates for this problem type
        problem_type_key = problem.problem_type.value
        operation_templates = CLEANING_OPERATIONS.get(problem_type_key, {})

        if not operation_templates:
            return [], None

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

        # Generate options using static pros/cons from config
        options = self._create_static_options(template_list, problem)

        # Generate GPT recommendation if enabled
        recommendation = None
        if self.enable_gpt_recommendations and self.openai_client and len(options) > 1:
            try:
                from .models import GPTRecommendation, DatasetStats

                # Get dataset stats
                dataset_stats = DatasetStats(
                    row_count=len(df),
                    column_count=len(df.columns),
                    missing_value_count=int(df.isna().sum().sum()),
                    duplicate_row_count=int(df.duplicated().sum()),
                    outlier_count=0
                )

                # Get dataset name from session
                dataset_name = getattr(self, '_current_dataset_name', 'dataset')

                # Call OpenAI for recommendation
                recommended_id, reason = self.openai_client.generate_recommendation(
                    problem=problem,
                    options=options,
                    dataset_stats=dataset_stats,
                    dataset_name=dataset_name
                )

                if recommended_id and reason:
                    recommendation = GPTRecommendation(
                        recommended_option_id=recommended_id,
                        reason=reason
                    )
                    print(f"[GPT] Recommended: {recommended_id} - {reason}")
                else:
                    print(f"[INFO] No GPT recommendation generated")

            except Exception as e:
                # Fail silently - no recommendation shown
                print(f"[WARNING] Failed to generate GPT recommendation: {e}")
                recommendation = None

        return options, recommendation

    def _create_static_options(
        self,
        option_templates: List[Dict],
        problem: Problem
    ) -> List:
        """
        Create cleaning options using static pros/cons from config.

        Args:
            option_templates: List of operation templates
            problem: Problem object

        Returns:
            List of CleaningOption objects with static pros/cons
        """
        from .models import CleaningOption, ProblemType
        from .config import DEFAULT_PROS_CONS

        # Map operation function names to DEFAULT_PROS_CONS keys
        OPERATION_TO_PROSCONS_KEY = {
            "drop_columns": "drop_columns",
            "drop_missing_rows": "drop_rows",
            "fill_with_mean": "fill_mean",
            "fill_with_median": "fill_median",
            "fill_with_mode": "fill_mode",
            "remove_outliers": "remove_outliers",
            "cap_outliers": "cap_outliers",
            "drop_duplicate_rows": "drop_duplicates_first",
            "drop_duplicate_columns": "drop_duplicate_columns",
        }

        options = []

        for i, template in enumerate(option_templates):
            operation_type = template["operation_type"]

            # Handle context-dependent no_operation mapping
            if operation_type == "no_operation":
                if problem.problem_type == ProblemType.MISSING_VALUES:
                    proscons_key = "keep_missing"
                elif problem.problem_type == ProblemType.OUTLIERS:
                    proscons_key = "keep_outliers"
                else:
                    proscons_key = "keep_missing"  # Default fallback
            else:
                # Get the appropriate key for DEFAULT_PROS_CONS
                proscons_key = OPERATION_TO_PROSCONS_KEY.get(operation_type, operation_type)

            # Get static pros/cons from config
            defaults = DEFAULT_PROS_CONS.get(proscons_key, {})
            pros = defaults.get("pros", "Advantages not available for this operation.")
            cons = defaults.get("cons", "Disadvantages not available for this operation.")

            # Create option with static pros/cons
            # Use deterministic option_id based on problem_id and index
            option = CleaningOption(
                option_id=f"{problem.problem_id}-opt-{i+1}",
                option_name=template["name"],
                operation_type=operation_type,
                parameters=template["parameters"],
                pros=pros,
                cons=cons,
                impact_metrics={}  # No dynamic metrics needed
            )
            options.append(option)

        return options


# Global agent instance
try:
    cleaning_agent = CleaningAgent()
except Exception as e:
    print(f"[WARNING] Failed to initialize CleaningAgent with GPT recommendations: {e}")
    print("[INFO] Initializing CleaningAgent without GPT recommendations")
    cleaning_agent = CleaningAgent(enable_gpt_recommendations=False)
