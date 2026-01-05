"""
Pydantic models for EDA Agent API
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# ============================================================================
# REQUEST MODELS
# ============================================================================

class EDARequest(BaseModel):
    """Request model for EDA analysis endpoint"""
    temp_file_path: str = Field(..., description="Path to temporary CSV file")
    include_sample_rows: bool = Field(default=True, description="Include sample rows in analysis")
    max_sample_rows: int = Field(default=20, description="Maximum number of sample rows")

# ============================================================================
# RESPONSE MODELS
# ============================================================================

class DataIssue(BaseModel):
    """Model for a single data quality issue"""
    issue_id: str = Field(..., description="Unique identifier for this issue")
    type: str = Field(..., description="Type of issue (e.g., missing_values, outliers)")
    severity: str = Field(..., description="Severity level: critical, warning, or info")
    title: str = Field(..., description="Short title for the issue")
    description: str = Field(..., description="Detailed description of the issue")
    affected_columns: List[str] = Field(default_factory=list, description="Columns affected by this issue")
    recommendation: str = Field(..., description="Recommendation for addressing the issue")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata (counts, percentages, etc.)")

class ColumnStatistics(BaseModel):
    """Statistical summary for a single column"""
    column_name: str
    data_type: str
    null_count: int
    null_percentage: float
    unique_count: int

    # Numeric columns
    min: Optional[float] = None
    max: Optional[float] = None
    mean: Optional[float] = None
    median: Optional[float] = None
    std_dev: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    has_outliers: Optional[bool] = None
    outlier_count: Optional[int] = None

    # Categorical columns
    top_values: Optional[List[Dict[str, Any]]] = None
    is_high_cardinality: Optional[bool] = None
    cardinality_level: Optional[str] = None  # "low", "medium", "high", "very_high"

    # String columns
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    avg_length: Optional[float] = None

class DatasetSummary(BaseModel):
    """High-level summary of the dataset"""
    row_count: int
    column_count: int
    file_size_bytes: int
    duplicate_row_count: int
    duplicate_row_percentage: float
    overall_completeness: float  # Percentage of non-null cells
    memory_usage_mb: Optional[float] = None

class EDAReport(BaseModel):
    """Complete EDA analysis report"""
    success: bool = True
    analysis_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    # Summary
    dataset_summary: DatasetSummary
    column_statistics: List[ColumnStatistics]

    # Issues
    issues: List[DataIssue]
    critical_issues_count: int = 0
    warning_issues_count: int = 0
    info_issues_count: int = 0

    # GPT-4 Analysis
    gpt_summary: str = Field(..., description="Overall assessment from GPT-4")
    visualization_concerns: List[str] = Field(default_factory=list, description="Specific concerns for visualization")

    # Performance
    analysis_duration_seconds: Optional[float] = None

class EDAErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    error_type: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
