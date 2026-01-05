"""
EDA Agent Package
Provides exploratory data analysis with OpenAI GPT-4
"""
from .analyzer import EDAAnalyzer
from .models import (
    EDARequest,
    EDAReport,
    DataIssue,
    ColumnStatistics,
    DatasetSummary,
    EDAErrorResponse
)
from .config import Severity, IssueType

__all__ = [
    'EDAAnalyzer',
    'EDARequest',
    'EDAReport',
    'DataIssue',
    'ColumnStatistics',
    'DatasetSummary',
    'EDAErrorResponse',
    'Severity',
    'IssueType'
]

__version__ = '1.0.0'
