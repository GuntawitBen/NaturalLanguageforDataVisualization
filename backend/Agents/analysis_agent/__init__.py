"""
Analysis Agent package.
Performs statistical analysis on datasets using pandas.
"""

from .agent import analysis_agent, AnalysisAgent
from .models import AnalysisRequest, AnalysisResult

__all__ = [
    "analysis_agent",
    "AnalysisAgent",
    "AnalysisRequest",
    "AnalysisResult",
]
