"""
Main orchestrator for the Chart Recommendation agent.
"""

from typing import List, Dict, Any, Optional
from .models import VisualizationResponse
from .openai_client import ChartRecOpenAIClient


class ChartRecAgent:
    """Main orchestrator for chart recommendations"""

    def __init__(self):
        self.openai_client = ChartRecOpenAIClient()

    def get_recommendations(
        self,
        user_question: str,
        sql_query: str,
        columns_info: List[Dict[str, str]],
        sample_data: List[Dict[str, Any]]
    ) -> VisualizationResponse:
        """
        Analyze query results and recommend charts

        Args:
            user_question: The original question from the user
            sql_query: The SQL query that was executed
            columns_info: List of dictionaries with column name and type
            sample_data: List of row dictionaries (sample results)

        Returns:
            VisualizationResponse with chart recommendations
        """
        print(f"[CHART-REC] Analyzing results for query: {sql_query[:50]}...")
        
        # In a real-world scenario, we might do some pre-analysis 
        # (e.g., check if data is time-series, categorical, etc.)
        # for now, we rely on GPT's analysis capability.
        
        return self.openai_client.recommend_charts(
            user_question=user_question,
            sql_query=sql_query,
            columns_info=columns_info,
            sample_data=sample_data
        )


# Global instance
chart_rec_agent = ChartRecAgent()
