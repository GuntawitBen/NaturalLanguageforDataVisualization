"""
Configuration for EDA Agent
"""
import os
from typing import List

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")  # Default to GPT-4o
OPENAI_TEMPERATURE = 0.3  # Low temperature for consistent analysis
OPENAI_MAX_TOKENS = 2000  # Sufficient for structured JSON response

# Analysis Configuration
MAX_SAMPLE_ROWS = 20  # Number of sample rows to send to GPT-4
MAX_UNIQUE_VALUES_TO_SHOW = 10  # Max unique values for categorical columns
OUTLIER_IQR_MULTIPLIER = 1.5  # IQR multiplier for outlier detection (standard is 1.5)
MISSING_VALUE_WARNING_THRESHOLD = 0.05  # 5% missing values triggers warning
MISSING_VALUE_CRITICAL_THRESHOLD = 0.20  # 20% missing values triggers critical

# Distribution Analysis
SKEWNESS_THRESHOLD = 1.0  # Absolute skewness > 1 indicates high skew
KURTOSIS_THRESHOLD = 3.0  # Kurtosis > 3 indicates heavy tails

# Cardinality Thresholds (for visualization purposes)
LOW_CARDINALITY_MAX = 10  # Suitable for color encoding
MEDIUM_CARDINALITY_MAX = 50  # May need aggregation
HIGH_CARDINALITY_THRESHOLD = 100  # Requires special handling

# Data Volume
LARGE_DATASET_THRESHOLD = 100000  # May need sampling for viz
VISUALIZATION_SAMPLE_SIZE = 10000  # Max points to plot

# Severity Levels
class Severity:
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

# Issue Types
class IssueType:
    MISSING_VALUES = "missing_values"
    DATA_TYPE_INCONSISTENCY = "data_type_inconsistency"
    OUTLIERS = "outliers"
    HIGH_CARDINALITY = "high_cardinality"
    DUPLICATE_ROWS = "duplicate_rows"
    ZERO_VARIANCE = "zero_variance"
    DATE_FORMAT_ISSUE = "date_format_issue"
    SKEWED_DISTRIBUTION = "skewed_distribution"
    HEAVY_TAILS = "heavy_tails"
    LARGE_DATASET = "large_dataset"
    VISUALIZATION_CONCERN = "visualization_concern"
