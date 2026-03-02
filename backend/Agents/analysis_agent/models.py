"""
Pydantic models for the Analysis Agent.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel


class AnalysisRequest(BaseModel):
    """Request for a statistical analysis operation"""
    analysis_type: str  # "factor_impact", "correlation", "group_comparison"
    target_column: Optional[str] = None
    columns: Optional[List[str]] = None
    explanation: str


class AnalysisResult(BaseModel):
    """Result of a statistical analysis"""
    data: List[Dict[str, Any]]       # Chart-ready data rows
    columns: List[str]               # Column names
    summary: str                     # NL summary of findings
    chart_type: str                  # "bar", "scatter"
    chart_config: Dict[str, Any]     # x_axis, y_axis, title, etc.
