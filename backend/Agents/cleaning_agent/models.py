"""
Pydantic models for the cleaning agent.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum


class ProblemType(str, Enum):
    """Types of data quality problems"""
    MISSING_VALUES = "missing_values"
    OUTLIERS = "outliers"
    DUPLICATES_ROWS = "duplicates_rows"
    DUPLICATES_COLUMNS = "duplicates_columns"


class Problem(BaseModel):
    """Represents a data quality problem"""
    problem_id: str
    problem_type: ProblemType
    severity: str  # "critical", "warning", "info"
    title: str
    description: str
    affected_columns: List[str]
    visualization_impact: str  # AI-generated explanation
    metadata: Dict[str, Any]  # Additional problem-specific data


class CleaningOption(BaseModel):
    """Represents a cleaning option for a problem"""
    option_id: str
    option_name: str  # "Drop rows with missing values"
    operation_type: str  # "drop_rows", "fill_mean", etc.
    parameters: Dict[str, Any]
    pros: str  # AI-generated advantages
    cons: str  # AI-generated disadvantages
    impact_metrics: Dict[str, Any]  # {"rows_affected": 150, "data_loss_percentage": 15.0}


class ProblemWithOptions(BaseModel):
    """A problem with its associated cleaning options"""
    problem: Problem
    options: List[CleaningOption]  # 2-3 options
    current_index: int
    total_problems: int


class DatasetStats(BaseModel):
    """Statistics about the dataset"""
    row_count: int
    column_count: int
    missing_value_count: int
    duplicate_row_count: int
    outlier_count: int


class OperationRecord(BaseModel):
    """Record of an applied operation"""
    operation_id: str
    problem_id: str
    option_id: str
    operation_type: str
    parameters: Dict[str, Any]
    timestamp: str
    stats_before: DatasetStats
    stats_after: DatasetStats
    backup_path: Optional[str]


class SessionState(BaseModel):
    """State of a cleaning session"""
    session_id: str
    temp_file_path: str
    dataset_name: str
    problems: List[Problem]
    current_problem_index: int
    skipped_problems: List[str]
    operation_history: List[OperationRecord]
    current_stats: DatasetStats
    created_at: str
    updated_at: str


class OperationResult(BaseModel):
    """Result of applying an operation"""
    success: bool
    message: str
    stats_before: DatasetStats
    stats_after: DatasetStats
    next_problem: Optional[ProblemWithOptions]
    session_complete: bool


# Request/Response models for API endpoints

class StartSessionRequest(BaseModel):
    """Request to start a cleaning session"""
    temp_file_path: str
    dataset_name: str


class StartSessionResponse(BaseModel):
    """Response when starting a cleaning session"""
    session_id: str
    session_state: SessionState
    first_problem: Optional[ProblemWithOptions]
    summary: str


class ApplyOperationRequest(BaseModel):
    """Request to apply a cleaning operation"""
    session_id: str
    option_id: str


class SkipProblemRequest(BaseModel):
    """Request to skip a problem"""
    session_id: str


class UndoLastRequest(BaseModel):
    """Request to undo the last operation"""
    session_id: str
