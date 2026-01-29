"""
Pydantic models for the Chart Recommendation agent.
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel


class ChartRecommendation(BaseModel):
    """A single chart recommendation"""
    chart_type: str  # e.g., "bar", "line", "pie", "scatter"
    title: str
    description: str
    explanation: Optional[str] = "View the details and trends in your data below."
    priority: Optional[str] = "medium"
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    color_by: Optional[str] = None
    reasoning: str


class VisualizationResponse(BaseModel):
    """Response from the Chart Recommendation agent"""
    recommendations: List[ChartRecommendation]
    summary: str
