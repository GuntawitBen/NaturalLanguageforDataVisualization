"""
Configuration for Inspection Agent
"""
import os

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_TEMPERATURE = 0.3
OPENAI_MAX_TOKENS = 2000

# Analysis Configuration
MAX_SAMPLE_ROWS = 20
MAX_UNIQUE_VALUES_TO_SHOW = 10

# Missing Values Detection
MISSING_VALUE_INFO_THRESHOLD = 0.01  # 1% - just notify
MISSING_VALUE_WARNING_THRESHOLD = 0.05  # 5% - warning
MISSING_VALUE_CRITICAL_THRESHOLD = 0.20  # 20% - critical

# Outlier Detection
OUTLIER_IQR_MULTIPLIER = 1.5  # Standard IQR multiplier
OUTLIER_ZSCORE_THRESHOLD = 3.0  # Z-score threshold (3 standard deviations)
OUTLIER_ISOLATION_CONTAMINATION = 0.1  # Expected proportion of outliers (10%)
OUTLIER_MIN_SAMPLES = 50  # Minimum samples to run Isolation Forest

# Duplicate Detection
DUPLICATE_ROW_WARNING_THRESHOLD = 0.05  # 5% duplicate rows triggers warning
DUPLICATE_COLUMN_SIMILARITY_THRESHOLD = 1.0  # 100% identical = duplicate column

# Data Type Detection
MIXED_TYPE_THRESHOLD = 0.05  # If >5% of values are different type, flag as mixed
NULL_REPRESENTATIONS = ['', 'null', 'NULL', 'None', 'NA', 'N/A', 'n/a', 'nan', 'NaN', '#N/A', '#NA', 'missing', 'MISSING', '-', '--']

# Cardinality Thresholds
LOW_CARDINALITY_MAX = 10
MEDIUM_CARDINALITY_MAX = 50
HIGH_CARDINALITY_THRESHOLD = 100

# Distribution Analysis
SKEWNESS_THRESHOLD = 1.0
KURTOSIS_THRESHOLD = 3.0

# Performance
LARGE_DATASET_THRESHOLD = 100000
VISUALIZATION_SAMPLE_SIZE = 10000

# Severity Levels
class Severity:
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

# Issue Types
class IssueType:
    # Missing Values
    MISSING_VALUES = "missing_values"
    MISSING_VALUES_PATTERN = "missing_values_pattern"

    # Duplicates
    DUPLICATE_ROWS = "duplicate_rows"
    DUPLICATE_COLUMNS = "duplicate_columns"

    # Outliers
    OUTLIERS_IQR = "outliers_iqr"
    OUTLIERS_ZSCORE = "outliers_zscore"
    OUTLIERS_ISOLATION_FOREST = "outliers_isolation_forest"

    # Data Type Issues
    MIXED_DATA_TYPES = "mixed_data_types"
    DATA_TYPE_INCONSISTENCY = "data_type_inconsistency"
    INVALID_VALUES = "invalid_values"

    # Other
    HIGH_CARDINALITY = "high_cardinality"
    CONSTANT_VALUES = "constant_values"
    SKEWED_DISTRIBUTION = "skewed_distribution"
    LARGE_DATASET = "large_dataset"
    VISUALIZATION_CONCERN = "visualization_concern"
