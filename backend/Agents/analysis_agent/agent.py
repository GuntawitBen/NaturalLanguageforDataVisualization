"""
Analysis Agent orchestrator.
Dispatches statistical analysis requests to executor functions.
"""

import logging
from typing import Optional
import pandas as pd

from .models import AnalysisRequest, AnalysisResult
from .executor import factor_impact, correlation_between, group_comparison

logger = logging.getLogger(__name__)


class AnalysisAgent:
    """Orchestrator for statistical analysis operations"""

    def run_analysis(
        self,
        df: pd.DataFrame,
        analysis_request: dict,
        schema=None,
    ) -> AnalysisResult:
        """
        Run a statistical analysis on the dataset.

        Args:
            df: Dataset as pandas DataFrame
            analysis_request: Dict with analysis_type, target_column, columns, explanation
            schema: Optional schema context (unused currently, reserved for future use)

        Returns:
            AnalysisResult with chart-ready data
        """
        request = AnalysisRequest(**analysis_request)
        analysis_type = request.analysis_type

        logger.info(f"Running {analysis_type} analysis")

        if analysis_type == "factor_impact":
            if not request.target_column:
                return AnalysisResult(
                    data=[],
                    columns=[],
                    summary="No target column specified for factor impact analysis.",
                    chart_type="bar",
                    chart_config={"title": "Error"}
                )
            return factor_impact(df, request.target_column)

        elif analysis_type == "correlation":
            if not request.columns or len(request.columns) < 2:
                return AnalysisResult(
                    data=[],
                    columns=[],
                    summary="Two columns are required for correlation analysis.",
                    chart_type="scatter",
                    chart_config={"title": "Error"}
                )
            return correlation_between(df, request.columns[0], request.columns[1])

        elif analysis_type == "group_comparison":
            if not request.target_column or not request.columns:
                return AnalysisResult(
                    data=[],
                    columns=[],
                    summary="Target column and group column are required for group comparison.",
                    chart_type="bar",
                    chart_config={"title": "Error"}
                )
            return group_comparison(df, request.target_column, request.columns[0])

        else:
            return AnalysisResult(
                data=[],
                columns=[],
                summary=f"Unknown analysis type: {analysis_type}",
                chart_type="bar",
                chart_config={"title": "Error"}
            )


# Global agent instance
analysis_agent = AnalysisAgent()
