# Inspection Agent - Detailed Step-by-Step Guide

> **A comprehensive walkthrough of every file and how they work together**

---

## Table of Contents

1. [Overview](#overview)
2. [File Structure](#file-structure)
3. [Detailed File Explanations](#detailed-file-explanations)
4. [Complete Execution Flow](#complete-execution-flow)
5. [Real Example Walkthrough](#real-example-walkthrough)

---

## Overview

The Inspection Agent consists of 7 core files that work together to analyze data quality and generate detailed reports with GPT-4 powered insights.

```
backend/Agents/inspection_agent/
├── __init__.py                 # Module initialization and exports
├── models.py                   # Data structures (Pydantic models)
├── config.py                   # Configuration constants
├── data_quality_checks.py      # Detection functions (the core checks)
├── analyzer.py                 # Main orchestrator (ties everything together)
├── openai_client.py            # GPT-4 communication
└── prompts.py                  # GPT-4 prompt templates
```

---

## File Structure

### Quick Reference

| File | Purpose | Key Exports | Dependencies |
|------|---------|-------------|--------------|
| `__init__.py` | Module entry point | `InspectionAnalyzer`, models | All other files |
| `models.py` | Data structures | `InspectionReport`, `DataIssue`, etc. | pydantic |
| `config.py` | Settings | Thresholds, constants, issue types | os |
| `data_quality_checks.py` | Detection logic | All `detect_*` functions | pandas, numpy, scipy, sklearn |
| `analyzer.py` | Main orchestrator | `InspectionAnalyzer` class | All above + openai_client |
| `openai_client.py` | GPT-4 integration | `OpenAIClient` class | openai, prompts, config |
| `prompts.py` | Prompt templates | Prompt builder functions | json, typing |

---

## Detailed File Explanations

---

## 1. `__init__.py` - Module Entry Point

### Purpose
This file makes the `inspection_agent` directory a Python package and defines what gets imported when someone does `from Agents.inspection_agent import ...`

### Complete Code
```python
"""
Inspection Agent for Data Quality Analysis
"""
from .analyzer import InspectionAnalyzer
from .models import (
    InspectionRequest,
    InspectionReport,
    DataIssue,
    ColumnStatistics,
    DatasetSummary,
    InspectionErrorResponse
)

__all__ = [
    'InspectionAnalyzer',
    'InspectionRequest',
    'InspectionReport',
    'DataIssue',
    'ColumnStatistics',
    'DatasetSummary',
    'InspectionErrorResponse'
]
```

### What It Does (Step-by-Step)

**Step 1:** Imports the main analyzer class
```python
from .analyzer import InspectionAnalyzer
```
- Brings in the `InspectionAnalyzer` class from `analyzer.py`
- This is the main class users interact with

**Step 2:** Imports all data models
```python
from .models import (...)
```
- Imports all Pydantic models that define data structures
- These are used for API requests/responses and internal data passing

**Step 3:** Defines public API
```python
__all__ = [...]
```
- Lists what's publicly available when importing
- Hides internal implementation details

### Usage Example
```python
# Without __init__.py, you'd need:
from Agents.inspection_agent.analyzer import InspectionAnalyzer

# With __init__.py, you can do:
from Agents.inspection_agent import InspectionAnalyzer
```

---

## 2. `models.py` - Data Structures

### Purpose
Defines all data structures using Pydantic models. These models:
- Validate data types automatically
- Provide clear API contracts
- Generate JSON schemas
- Enable IDE autocomplete

### Key Components

#### A. Request Models

**`InspectionRequest`** - What the API receives
```python
class InspectionRequest(BaseModel):
    temp_file_path: str = Field(..., description="Path to temporary CSV file")
    include_sample_rows: bool = Field(default=True, description="Include sample rows in analysis")
    max_sample_rows: int = Field(default=20, description="Maximum number of sample rows")
```

**Step-by-Step:**
1. `temp_file_path`: Required string pointing to CSV file location
2. `include_sample_rows`: Optional boolean (default: True) - whether to send samples to GPT-4
3. `max_sample_rows`: Optional int (default: 20) - how many sample rows to include

**Example Usage:**
```python
request = InspectionRequest(
    temp_file_path="./uploads/temp_abc123.csv",
    include_sample_rows=True,
    max_sample_rows=20
)
```

#### B. Response Models

**`DataIssue`** - Represents a single data quality problem
```python
class DataIssue(BaseModel):
    issue_id: str                           # UUID for tracking
    type: str                               # Issue category (e.g., "missing_values")
    severity: str                           # "critical", "warning", or "info"
    title: str                              # Short description
    description: str                        # Detailed explanation
    affected_columns: List[str]             # Which columns have this issue
    recommendation: str                     # How to fix it
    visualization_impact: str               # How it affects charts (GPT-4 generated)
    metadata: Optional[Dict[str, Any]]      # Extra data (counts, percentages, etc.)
```

**Step-by-Step Example:**
```python
# Creating a DataIssue
issue = DataIssue(
    issue_id="550e8400-e29b-41d4-a716-446655440000",
    type="missing_values",
    severity="warning",
    title="Missing values in 'age'",
    description="Column 'age' has 45 missing values (15% of total rows).",
    affected_columns=["age"],
    recommendation="Consider imputation with median age.",
    visualization_impact="Missing age values will create gaps in age distribution charts...",
    metadata={
        "null_count": 45,
        "null_percentage": 15.0
    }
)
```

**`ColumnStatistics`** - Statistics for one column
```python
class ColumnStatistics(BaseModel):
    column_name: str
    data_type: str
    null_count: int
    null_percentage: float
    unique_count: int

    # Numeric columns only
    min: Optional[float] = None
    max: Optional[float] = None
    mean: Optional[float] = None
    median: Optional[float] = None
    std_dev: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    has_outliers: Optional[bool] = None
    outlier_count: Optional[int] = None
    outlier_method: Optional[str] = None

    # Categorical columns only
    top_values: Optional[List[Dict[str, Any]]] = None
    is_high_cardinality: Optional[bool] = None
    cardinality_level: Optional[str] = None

    # String columns only
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    avg_length: Optional[float] = None
```

**Step-by-Step Example:**
```python
# For a numeric column "price"
price_stats = ColumnStatistics(
    column_name="price",
    data_type="float64",
    null_count=5,
    null_percentage=2.5,
    unique_count=87,
    min=9.99,
    max=199.99,
    mean=49.50,
    median=45.00,
    std_dev=25.30,
    skewness=0.8,
    kurtosis=2.1,
    has_outliers=True,
    outlier_count=3,
    outlier_method="iqr"
)
```

**`DatasetSummary`** - Overall dataset metrics
```python
class DatasetSummary(BaseModel):
    row_count: int                      # Total number of rows
    column_count: int                   # Total number of columns
    file_size_bytes: int                # Size on disk
    duplicate_row_count: int            # Number of duplicate rows
    duplicate_row_percentage: float     # % of duplicates
    duplicate_column_count: int         # Number of duplicate columns
    overall_completeness: float         # % of non-null cells
    memory_usage_mb: Optional[float]    # RAM usage
```

**Step-by-Step Example:**
```python
summary = DatasetSummary(
    row_count=1000,
    column_count=15,
    file_size_bytes=524288,  # 512 KB
    duplicate_row_count=23,
    duplicate_row_percentage=2.3,
    duplicate_column_count=1,
    overall_completeness=96.5,
    memory_usage_mb=2.5
)
```

**`InspectionReport`** - Complete analysis result
```python
class InspectionReport(BaseModel):
    success: bool = True
    analysis_timestamp: str

    dataset_summary: DatasetSummary
    column_statistics: List[ColumnStatistics]

    issues: List[DataIssue]
    critical_issues_count: int = 0
    warning_issues_count: int = 0
    info_issues_count: int = 0

    gpt_summary: str
    visualization_concerns: List[str]

    analysis_duration_seconds: Optional[float] = None
```

**What each field means:**
1. `success`: Did the analysis complete?
2. `analysis_timestamp`: When was this run?
3. `dataset_summary`: High-level stats
4. `column_statistics`: Per-column details
5. `issues`: All detected problems
6. `*_issues_count`: Count by severity
7. `gpt_summary`: GPT-4's overall assessment
8. `visualization_concerns`: GPT-4's specific warnings
9. `analysis_duration_seconds`: How long it took

---

## 3. `config.py` - Configuration Constants

### Purpose
Central location for all configurable settings, thresholds, and constants. Makes it easy to tune the agent without changing code.

### Key Sections

#### A. OpenAI Settings
```python
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_TEMPERATURE = 0.3
OPENAI_MAX_TOKENS = 2000
```

**What each does:**
1. `OPENAI_API_KEY`: Reads from environment variable
2. `OPENAI_MODEL`: Which GPT model to use (default: gpt-4o)
3. `OPENAI_TEMPERATURE`: Creativity level (0.3 = more deterministic)
4. `OPENAI_MAX_TOKENS`: Maximum response length

#### B. Detection Thresholds

**Missing Values:**
```python
MISSING_VALUE_INFO_THRESHOLD = 0.01      # 1% missing → Info
MISSING_VALUE_WARNING_THRESHOLD = 0.05   # 5% missing → Warning
MISSING_VALUE_CRITICAL_THRESHOLD = 0.20  # 20% missing → Critical
```

**How it works:**
```python
if null_percentage >= 20:
    severity = "critical"
elif null_percentage >= 5:
    severity = "warning"
elif null_percentage >= 1:
    severity = "info"
else:
    # Don't report (too few)
    pass
```

**Outlier Detection:**
```python
OUTLIER_IQR_MULTIPLIER = 1.5              # Standard: Q1 - 1.5*IQR, Q3 + 1.5*IQR
OUTLIER_ZSCORE_THRESHOLD = 3.0            # 3 standard deviations
OUTLIER_ISOLATION_CONTAMINATION = 0.1     # Expect 10% outliers
OUTLIER_MIN_SAMPLES = 50                  # Need 50+ rows for Isolation Forest
```

**How each is used:**
1. **IQR**: `lower_bound = Q1 - 1.5 * IQR`
2. **Z-Score**: `outlier if |z| > 3.0`
3. **Isolation Forest**: Trained expecting 10% outliers
4. **Min Samples**: Skip Isolation Forest if < 50 rows

**Duplicate Detection:**
```python
DUPLICATE_ROW_WARNING_THRESHOLD = 0.05    # 5% duplicates → Warning
```

**How it works:**
```python
if duplicate_percentage > 5:
    severity = "warning"
else:
    severity = "info"
```

**Cardinality:**
```python
LOW_CARDINALITY_MAX = 10           # ≤10 unique values
MEDIUM_CARDINALITY_MAX = 50        # ≤50 unique values
HIGH_CARDINALITY_THRESHOLD = 100   # >100 unique values = problem
```

**Classification logic:**
```python
if unique_count <= 10:
    level = "low"         # Good for categorical charts
elif unique_count <= 50:
    level = "medium"      # May need aggregation
elif unique_count <= 100:
    level = "high"        # Challenging to visualize
else:
    level = "very_high"   # Requires special handling
```

#### C. Null Representations
```python
NULL_REPRESENTATIONS = [
    '', 'null', 'NULL', 'None', 'NA', 'N/A', 'n/a',
    'nan', 'NaN', '#N/A', '#NA', 'missing', 'MISSING',
    '-', '--'
]
```

**How it's used:**
```python
# In detect_missing_values()
if df[column].dtype == 'object':
    null_like_mask = df[column].isin(NULL_REPRESENTATIONS)
    null_like_count = null_like_mask.sum()
```

#### D. Issue Type Constants
```python
class IssueType:
    MISSING_VALUES = "missing_values"
    MISSING_VALUES_PATTERN = "missing_values_pattern"
    DUPLICATE_ROWS = "duplicate_rows"
    DUPLICATE_COLUMNS = "duplicate_columns"
    OUTLIERS_IQR = "outliers_iqr"
    OUTLIERS_ZSCORE = "outliers_zscore"
    OUTLIERS_ISOLATION_FOREST = "outliers_isolation_forest"
    MIXED_DATA_TYPES = "mixed_data_types"
    DATA_TYPE_INCONSISTENCY = "data_type_inconsistency"
    INVALID_VALUES = "invalid_values"
    HIGH_CARDINALITY = "high_cardinality"
    CONSTANT_VALUES = "constant_values"
    SKEWED_DISTRIBUTION = "skewed_distribution"
    LARGE_DATASET = "large_dataset"
    VISUALIZATION_CONCERN = "visualization_concern"
```

**Why use constants?**
- Prevents typos: `IssueType.MISSING_VALUES` vs `"mising_values"`
- IDE autocomplete
- Easy to refactor

#### E. Severity Levels
```python
class Severity:
    CRITICAL = "critical"  # Prevents meaningful visualization
    WARNING = "warning"    # May mislead or reduce quality
    INFO = "info"         # Minor issues worth noting
```

---

## 4. `data_quality_checks.py` - Detection Functions

### Purpose
Contains all the actual detection logic. Pure functions that take data and return analysis results. No GPT-4, no side effects—just pandas/numpy/scipy/sklearn operations.

### Key Functions

#### A. Missing Values Detection

```python
def detect_missing_values(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """Detect missing values in a column"""
```

**Step-by-Step Execution:**

**Step 1:** Count standard null values
```python
null_count = df[column].isna().sum()
null_percentage = (null_count / len(df)) * 100
```
- Uses pandas `.isna()` to find NaN/None/NaT
- Calculates percentage

**Step 2:** Check for null-like strings (if text column)
```python
if df[column].dtype == 'object':
    null_like_mask = df[column].isin(NULL_REPRESENTATIONS)
    null_like_count = null_like_mask.sum()
```
- Only for text columns
- Checks if values match null-like strings: '', 'NA', 'null', etc.

**Step 3:** Return combined results
```python
return {
    'null_count': int(null_count),
    'null_percentage': float(null_percentage),
    'null_like_count': int(null_like_count),
    'total_null_count': int(total_null_count),
    'total_null_percentage': float(total_null_percentage)
}
```

**Example:**
```python
# Input: Column "age" with [25, NaN, 30, None, 'NA', 40]
result = detect_missing_values(df, "age")
# Output:
{
    'null_count': 2,           # NaN and None
    'null_percentage': 33.3,
    'null_like_count': 1,      # 'NA'
    'total_null_count': 3,
    'total_null_percentage': 50.0
}
```

#### B. Duplicate Row Detection

```python
def detect_duplicate_rows(df: pd.DataFrame) -> Dict[str, Any]:
    """Detect duplicate rows in the dataset"""
```

**Step-by-Step:**

**Step 1:** Find duplicates
```python
duplicate_count = df.duplicated().sum()
```
- `.duplicated()` marks rows that are exact copies of earlier rows
- `.sum()` counts them

**Step 2:** Calculate percentage
```python
duplicate_percentage = (duplicate_count / len(df)) * 100 if len(df) > 0 else 0
```

**Step 3:** Return results
```python
return {
    'duplicate_count': int(duplicate_count),
    'duplicate_percentage': float(duplicate_percentage)
}
```

**Example:**
```python
# Input: DataFrame with rows [A, B, C, A, D] (A is duplicate)
result = detect_duplicate_rows(df)
# Output:
{
    'duplicate_count': 1,
    'duplicate_percentage': 20.0
}
```

#### C. Duplicate Column Detection

```python
def detect_duplicate_columns(df: pd.DataFrame) -> List[Tuple[str, str]]:
    """Detect duplicate columns (columns with identical values)"""
```

**Step-by-Step:**

**Step 1:** Compare all column pairs
```python
columns = df.columns.tolist()
for i in range(len(columns)):
    for j in range(i + 1, len(columns)):
        col1, col2 = columns[i], columns[j]
```
- Nested loop to check every pair
- Only check each pair once (i < j)

**Step 2:** Check if columns are identical
```python
if df[col1].equals(df[col2]):
    duplicate_pairs.append((col1, col2))
```
- `.equals()` checks if all values match
- Handles NaN correctly (NaN equals NaN)

**Step 3:** Return list of duplicate pairs
```python
return duplicate_pairs  # e.g., [('customer_id', 'customer_ID'), ...]
```

**Example:**
```python
# Input: DataFrame with columns ['A', 'B', 'C'] where A and C are identical
result = detect_duplicate_columns(df)
# Output:
[('A', 'C')]
```

#### D. Outlier Detection - IQR Method

```python
def detect_outliers_iqr(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """Detect outliers using IQR method"""
```

**Step-by-Step:**

**Step 1:** Calculate quartiles
```python
Q1 = values.quantile(0.25)  # 25th percentile
Q3 = values.quantile(0.75)  # 75th percentile
IQR = Q3 - Q1               # Interquartile range
```

**Step 2:** Calculate bounds
```python
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR
```
- Standard Tukey fences
- 1.5 is the multiplier (configurable)

**Step 3:** Find outliers
```python
outlier_mask = (df[column] < lower_bound) | (df[column] > upper_bound)
outlier_indices = df[outlier_mask].index.tolist()
```

**Step 4:** Return results
```python
return {
    'has_outliers': outlier_count > 0,
    'outlier_count': int(outlier_count),
    'outlier_indices': outlier_indices[:100],  # Limit for performance
    'lower_bound': float(lower_bound),
    'upper_bound': float(upper_bound),
    'method': 'iqr'
}
```

**Visual Example:**
```
Data: [10, 12, 13, 14, 15, 16, 18, 100]

Q1 = 12.5
Q3 = 16.5
IQR = 4

lower_bound = 12.5 - 1.5*4 = 6.5
upper_bound = 16.5 + 1.5*4 = 22.5

Outliers: [100] (> 22.5)
```

#### E. Outlier Detection - Z-Score Method

```python
def detect_outliers_zscore(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """Detect outliers using Z-score method"""
```

**Step-by-Step:**

**Step 1:** Calculate Z-scores
```python
z_scores = np.abs(stats.zscore(values))
```
- Z-score = (value - mean) / std_dev
- Takes absolute value

**Step 2:** Find values beyond threshold
```python
outlier_mask = z_scores > OUTLIER_ZSCORE_THRESHOLD  # Default: 3.0
```
- Values more than 3 standard deviations from mean

**Step 3:** Return outlier information
```python
return {
    'has_outliers': outlier_count > 0,
    'outlier_count': int(outlier_count),
    'outlier_indices': outlier_indices[:100],
    'threshold': float(OUTLIER_ZSCORE_THRESHOLD),
    'method': 'zscore'
}
```

**Visual Example:**
```
Data: [10, 12, 13, 14, 15, 16, 18, 100]

mean = 24.75
std_dev = 29.57

Z-score for 100: |100 - 24.75| / 29.57 = 2.54
Z-score for 18: |18 - 24.75| / 29.57 = 0.23

If threshold is 3.0, no outliers detected
If threshold is 2.0, 100 is an outlier
```

#### F. Outlier Detection - Isolation Forest

```python
def detect_outliers_isolation_forest(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """Detect outliers using Isolation Forest (machine learning)"""
```

**Step-by-Step:**

**Step 1:** Check minimum sample requirement
```python
if len(values) < OUTLIER_MIN_SAMPLES:  # Default: 50
    return {'has_outliers': False, ...}
```

**Step 2:** Reshape data for sklearn
```python
X = values.values.reshape(-1, 1)
```
- Converts pandas Series to numpy array
- Reshapes to 2D (required by sklearn)

**Step 3:** Train Isolation Forest
```python
iso_forest = IsolationForest(
    contamination=0.1,  # Expect 10% outliers
    random_state=42     # Reproducible results
)
predictions = iso_forest.fit_predict(X)
```

**Step 4:** Extract outliers
```python
outlier_mask = predictions == -1  # -1 means outlier
outlier_indices = values[outlier_mask].index.tolist()
```

**How Isolation Forest Works:**
1. Randomly splits data into partitions
2. Outliers get isolated faster (fewer splits needed)
3. Scores each point based on isolation speed

**Example:**
```python
# Input: [10, 11, 12, 13, 14, 15, 100, 105] (50+ rows total)
# Isolation Forest identifies: [100, 105] as outliers
# They're isolated from the main cluster [10-15]
```

#### G. Mixed Data Type Detection

```python
def detect_mixed_data_types(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """Detect mixed data types in a column"""
```

**Step-by-Step:**

**Step 1:** Check if column is object type
```python
if df[column].dtype != 'object':
    return {'has_mixed_types': False, 'type_distribution': {}}
```
- Non-object columns are already typed
- Only text columns can have mixed types

**Step 2:** Analyze each value's actual type
```python
type_counts = {}
for value in non_null_values:
    value_type = type(value).__name__
    type_counts[value_type] = type_counts.get(value_type, 0) + 1
```

**Step 3:** Check if values can be numbers
```python
numeric_count = 0
for value in non_null_values:
    try:
        float(value)
        numeric_count += 1
    except (ValueError, TypeError):
        pass
```

**Step 4:** Calculate type distribution
```python
type_distribution = {
    type_name: {
        'count': count,
        'percentage': (count / total) * 100
    }
    for type_name, count in type_counts.items()
}
```

**Example:**
```python
# Input column: ['10', '20', 'N/A', '30', 'pending', '40']
result = detect_mixed_data_types(df, column)
# Output:
{
    'has_mixed_types': True,
    'type_distribution': {
        'str': {'count': 6, 'percentage': 100.0},
        'numeric_string': {'count': 4, 'percentage': 66.7}
    },
    'total_types': 2
}
# Explanation: All are strings, but 4 can be converted to numbers
```

#### H. Cardinality Analysis

```python
def analyze_cardinality(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """Analyze cardinality of a column"""
```

**Step-by-Step:**

**Step 1:** Count unique values
```python
unique_count = df[column].nunique()
total_count = len(df)
cardinality_ratio = unique_count / total_count
```

**Step 2:** Classify cardinality level
```python
if unique_count <= 10:
    cardinality_level = "low"          # Good for pie charts, color coding
    is_high_cardinality = False
elif unique_count <= 50:
    cardinality_level = "medium"       # May need aggregation
    is_high_cardinality = False
elif unique_count <= 100:
    cardinality_level = "high"         # Challenging
    is_high_cardinality = True
else:
    cardinality_level = "very_high"    # Requires special handling
    is_high_cardinality = True
```

**Example:**
```python
# Low cardinality (good):
# Column "status" with values: ['active', 'inactive', 'pending']
# Result: level = "low", is_high_cardinality = False

# High cardinality (bad):
# Column "customer_id" with 5000 unique values
# Result: level = "very_high", is_high_cardinality = True
```

#### I. Distribution Analysis

```python
def analyze_distribution(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """Analyze distribution characteristics of numeric column"""
```

**Step-by-Step:**

**Step 1:** Calculate skewness
```python
skewness = float(values.skew())
```
- Measures asymmetry of distribution
- Positive: right tail (most values on left)
- Negative: left tail (most values on right)
- Zero: symmetric

**Step 2:** Calculate kurtosis
```python
kurtosis = float(values.kurtosis())
```
- Measures "tailedness"
- High: heavy tails (more extreme values)
- Low: light tails (fewer extreme values)

**Step 3:** Determine if problematic
```python
is_skewed = abs(skewness) > 1.0
is_heavy_tailed = kurtosis > 3.0
```

**Visual Example:**
```
Skewness:
  -2.0 ← Left skewed     |  Symmetric → 0.0  |  Right skewed → +2.0

  ___                          ___                    ___
 |   \                      __/   \__                /   |
 |    \___              ___/         \___       ___/    |
____________          _____________________   _____________________

Kurtosis:
  Low (< 3)           Normal (≈ 3)          High (> 3)

    ___                  ___                  ___
  _/   \_              _/   \_               /   \
 /       \           _/       \_            /     \
__________         ________________       /         \
                                         ___________
```

---

## 5. `analyzer.py` - Main Orchestrator

### Purpose
The heart of the inspection agent. Coordinates all detection functions, manages the analysis pipeline, and integrates with GPT-4.

### Key Components

#### A. InspectionAnalyzer Class

```python
class InspectionAnalyzer:
    def __init__(self, openai_api_key: str = None):
        self.openai_client = OpenAIClient(api_key=openai_api_key)
```

**What happens:**
1. Initializes OpenAI client for GPT-4 calls
2. Stores client for later use

#### B. Main Analysis Method

```python
def analyze_csv(
    self,
    file_path: str,
    include_sample_rows: bool = True,
    max_sample_rows: int = MAX_SAMPLE_ROWS
) -> InspectionReport:
```

**Complete Step-by-Step Execution:**

**STEP 1: Load and Validate File**
```python
# Validate file exists
if not Path(file_path).exists():
    raise FileNotFoundError(f"CSV file not found: {file_path}")

# Load CSV
df = pd.read_csv(file_path)
file_size_bytes = Path(file_path).stat().st_size
```

**What happens:**
1. Checks file exists
2. Loads entire CSV into pandas DataFrame
3. Gets file size in bytes

**STEP 2: Calculate Dataset Summary**
```python
dataset_summary = self._calculate_dataset_summary(df, file_size_bytes)
```

**Internally calls:**
```python
def _calculate_dataset_summary(self, df, file_size_bytes):
    # Get duplicate rows
    dup_result = detect_duplicate_rows(df)

    # Get duplicate columns
    dup_columns = detect_duplicate_columns(df)

    # Calculate completeness
    total_cells = df.shape[0] * df.shape[1]
    non_null_cells = total_cells - df.isna().sum().sum()
    overall_completeness = (non_null_cells / total_cells * 100)

    # Calculate memory
    memory_usage_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)

    return DatasetSummary(
        row_count=len(df),
        column_count=len(df.columns),
        file_size_bytes=file_size_bytes,
        duplicate_row_count=dup_result['duplicate_count'],
        duplicate_row_percentage=dup_result['duplicate_percentage'],
        duplicate_column_count=len(dup_columns),
        overall_completeness=overall_completeness,
        memory_usage_mb=memory_usage_mb
    )
```

**Example output:**
```python
DatasetSummary(
    row_count=1000,
    column_count=10,
    file_size_bytes=102400,  # 100 KB
    duplicate_row_count=15,
    duplicate_row_percentage=1.5,
    duplicate_column_count=0,
    overall_completeness=98.5,
    memory_usage_mb=1.2
)
```

**STEP 3: Calculate Column Statistics**
```python
column_stats_list = self._calculate_column_statistics(df)
```

**Internally processes each column:**
```python
def _calculate_column_statistics(self, df):
    stats_list = []

    for column in df.columns:
        col_data = df[column]

        # Basic stats (all columns)
        stat_dict = {
            'column_name': column,
            'data_type': str(col_data.dtype),
            'null_count': int(col_data.isna().sum()),
            'null_percentage': float(...),
            'unique_count': int(col_data.nunique())
        }

        # Numeric columns: add statistics
        if pd.api.types.is_numeric_dtype(col_data):
            # Run outlier detection
            outlier_iqr = detect_outliers_iqr(df, column)
            outlier_zscore = detect_outliers_zscore(df, column)
            outlier_iforest = detect_outliers_isolation_forest(df, column)

            # Distribution analysis
            dist_result = analyze_distribution(df, column)

            stat_dict.update({
                'min': float(non_null.min()),
                'max': float(non_null.max()),
                'mean': float(non_null.mean()),
                'median': float(non_null.median()),
                'std_dev': float(non_null.std()),
                'skewness': dist_result.get('skewness'),
                'kurtosis': dist_result.get('kurtosis'),
                'has_outliers': outlier_iqr['has_outliers'],
                'outlier_count': outlier_iqr['outlier_count'],
                'outlier_method': 'iqr'
            })

        # Categorical columns: add cardinality
        if dtype_str == 'object':
            card_result = analyze_cardinality(df, column)

            # Top values
            top_values = []
            value_counts = col_data.value_counts().head(10)
            for value, count in value_counts.items():
                top_values.append({
                    'value': str(value),
                    'count': int(count),
                    'percentage': float((count / len(df)) * 100)
                })

            stat_dict.update({
                'top_values': top_values,
                'is_high_cardinality': card_result['is_high_cardinality'],
                'cardinality_level': card_result['cardinality_level']
            })

        stats_list.append(ColumnStatistics(**stat_dict))

    return stats_list
```

**Example output for one column:**
```python
ColumnStatistics(
    column_name="price",
    data_type="float64",
    null_count=5,
    null_percentage=0.5,
    unique_count=87,
    min=9.99,
    max=199.99,
    mean=49.50,
    median=45.00,
    std_dev=25.30,
    skewness=0.8,
    kurtosis=2.1,
    has_outliers=True,
    outlier_count=3,
    outlier_method="iqr"
)
```

**STEP 4: Detect All Issues**
```python
issues = self._detect_issues(df, dataset_summary, column_stats_list)
```

**Internally runs all checks:**
```python
def _detect_issues(self, df, dataset_summary, column_stats_list):
    issues = []

    # 1. Missing values in each column
    issues.extend(self._detect_missing_value_issues(df))

    # 2. Duplicate rows (if any)
    if dataset_summary.duplicate_row_count > 0:
        issues.append(self._create_duplicate_row_issue(dataset_summary))

    # 3. Duplicate columns (if any)
    dup_columns = detect_duplicate_columns(df)
    if len(dup_columns) > 0:
        issues.append(self._create_duplicate_column_issue(dup_columns))

    # 4. Outliers in numeric columns
    issues.extend(self._detect_outlier_issues(df, column_stats_list))

    # 5. Mixed data types
    issues.extend(self._detect_mixed_type_issues(df))

    # 6. Large dataset warning
    if dataset_summary.row_count > LARGE_DATASET_THRESHOLD:
        issues.append(self._create_large_dataset_issue(dataset_summary))

    return issues
```

**At this point, each issue has a placeholder:**
```python
DataIssue(
    ...
    visualization_impact="[GPT-4 will generate dynamic impact]",  # Placeholder
    ...
)
```

**STEP 5: Enrich Issues with GPT-4 Impacts**
```python
print(f"[INFO] Enriching {len(issues)} issues with GPT-4 visualization impacts...")
issues = self._enrich_issues_with_impacts(df, issues, column_stats_list)
```

**This is the magic step! Here's what happens:**
```python
def _enrich_issues_with_impacts(self, df, issues, column_stats_list):
    enriched_issues = []

    for issue in issues:
        # Get column details
        column_details = {}
        for col_name in issue.affected_columns:
            col_stat = next((c for c in column_stats_list
                           if c.column_name == col_name), None)
            if col_stat:
                column_details[col_name] = col_stat.dict()

        # Get sample values
        sample_values = None
        if issue.affected_columns and len(issue.affected_columns) > 0:
            col_name = issue.affected_columns[0]
            if col_name in df.columns:
                sample_values = df[col_name].dropna().head(10).tolist()

        # 🤖 Call GPT-4 to generate custom impact explanation
        visualization_impact = self.openai_client.generate_visualization_impact(
            issue_title=issue.title,
            issue_type=issue.type,
            issue_description=issue.description,
            affected_columns=issue.affected_columns,
            column_details=column_details,
            sample_values=sample_values
        )

        # Replace placeholder with GPT-4 generated text
        issue.visualization_impact = visualization_impact
        enriched_issues.append(issue)

        print(f"  ✓ Generated impact for: {issue.title}")

    return enriched_issues
```

**What GPT-4 receives for each issue:**
```python
{
    "issue_title": "Missing values in 'sales_amount'",
    "issue_type": "missing_values",
    "issue_description": "Column 'sales_amount' has 87 missing values (8.7% of total rows).",
    "affected_columns": ["sales_amount"],
    "column_details": {
        "sales_amount": {
            "data_type": "float64",
            "null_count": 87,
            "null_percentage": 8.7,
            "min": 10.50,
            "max": 9999.99,
            "mean": 245.67
        }
    },
    "sample_values": [150.00, 275.50, 89.99, 425.00, ...]
}
```

**What GPT-4 generates:**
```
"The 'sales_amount' column has 87 missing values (8.7% of data). In a line chart
showing sales trends over time, these gaps will create disconnected segments,
making it difficult to identify patterns. Bar charts comparing sales across regions
will have incomplete data for certain time periods, and your average sales calculation
will only reflect 91.3% of transactions, potentially underestimating total revenue."
```

**STEP 6: Get Sample Rows for GPT-4 Overall Analysis**
```python
sample_rows = []
if include_sample_rows:
    sample_rows = self._get_sample_rows(df, max_sample_rows)
```

**Simple process:**
```python
def _get_sample_rows(self, df, n=20):
    sample_df = df.head(n)
    return sample_df.to_dict('records')
```

**Output:**
```python
[
    {"date": "2024-01-01", "product": "Widget", "quantity": 10, "price": 29.99},
    {"date": "2024-01-02", "product": "Gadget", "quantity": None, "price": 45.00},
    ...
]
```

**STEP 7: GPT-4 Overall Analysis**
```python
gpt_result = self._get_gpt_analysis(
    dataset_summary=dataset_summary.dict(),
    column_statistics=[col.dict() for col in column_stats_list],
    sample_rows=sample_rows,
    detected_issues_summary=self._get_issues_summary(issues)
)
```

**What GPT-4 receives:**
```python
{
    "dataset_summary": {"row_count": 1000, "column_count": 10, ...},
    "column_statistics": [{"column_name": "price", ...}, ...],
    "sample_rows": [{...}, {...}, ...],
    "detected_issues_summary": {
        "missing_values_count": 3,
        "outliers_count": 2,
        "duplicate_rows": 15,
        "total_issues": 8
    }
}
```

**What GPT-4 returns:**
```python
{
    "success": True,
    "summary": "Your sales dataset is mostly clean with 95% completeness. The main concerns are missing values in the quantity column and some outliers in pricing data. Overall, the data is suitable for visualization with minor cleaning.",
    "visualization_concerns": [
        "Gaps in quantity data may affect trend analysis",
        "Price outliers could skew scale of charts"
    ],
    "additional_issues": [
        {
            "type": "inconsistent_formatting",
            "severity": "info",
            "title": "Date format inconsistency",
            "description": "Some dates use MM/DD/YYYY while others use DD-MM-YYYY",
            "affected_columns": ["date"],
            "recommendation": "Standardize date format",
            "visualization_impact": "Timeline visualizations may misinterpret dates..."
        }
    ]
}
```

**STEP 8: Merge GPT-4 Additional Issues**
```python
if gpt_result.get('success') and gpt_result.get('additional_issues'):
    for issue_data in gpt_result['additional_issues']:
        issues.append(self._create_data_issue(
            issue_type=issue_data.get('type', IssueType.VISUALIZATION_CONCERN),
            severity=issue_data.get('severity', Severity.INFO),
            title=issue_data.get('title', 'GPT-4 Detected Issue'),
            description=issue_data.get('description', ''),
            affected_columns=issue_data.get('affected_columns', []),
            recommendation=issue_data.get('recommendation', ''),
            visualization_impact=issue_data.get('visualization_impact', '...'),
            metadata=issue_data.get('metadata')
        ))
```

**STEP 9: Count Issues by Severity**
```python
critical_count = sum(1 for issue in issues if issue.severity == Severity.CRITICAL)
warning_count = sum(1 for issue in issues if issue.severity == Severity.WARNING)
info_count = sum(1 for issue in issues if issue.severity == Severity.INFO)
```

**STEP 10: Build Final Report**
```python
analysis_duration = time.time() - start_time

report = InspectionReport(
    success=True,
    dataset_summary=dataset_summary,
    column_statistics=column_stats_list,
    issues=issues,  # Now with GPT-4 impacts!
    critical_issues_count=critical_count,
    warning_issues_count=warning_count,
    info_issues_count=info_count,
    gpt_summary=gpt_summary,
    visualization_concerns=visualization_concerns,
    analysis_duration_seconds=round(analysis_duration, 2)
)

return report
```

---

## 6. `openai_client.py` - GPT-4 Integration

### Purpose
Handles all communication with OpenAI's GPT-4 API. Two main operations: generating visualization impacts and overall analysis.

### Key Components

#### A. OpenAIClient Class

```python
class OpenAIClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API key not found.")
        self.client = OpenAI(api_key=self.api_key)
```

#### B. Generate Visualization Impact (Per Issue)

```python
def generate_visualization_impact(
    self,
    issue_title: str,
    issue_type: str,
    issue_description: str,
    affected_columns: List[str],
    column_details: Dict[str, Any],
    sample_values: List[Any] = None
) -> str:
```

**Step-by-Step Execution:**

**Step 1:** Build the prompt
```python
prompt = build_visualization_impact_prompt(
    issue_title=issue_title,
    issue_type=issue_type,
    issue_description=issue_description,
    affected_columns=affected_columns,
    column_details=column_details,
    sample_values=sample_values
)
```

**Prompt looks like:**
```
You are a data visualization expert. Generate a clear, educational explanation
of how this specific data quality issue will affect data visualizations.

**Issue Details:**
- Title: Missing values in 'sales_amount'
- Type: missing_values
- Description: Column 'sales_amount' has 87 missing values (8.7% of total rows).
- Affected Columns: sales_amount

**Column Context:**
{
  "sales_amount": {
    "data_type": "float64",
    "null_count": 87,
    "null_percentage": 8.7,
    "min": 10.50,
    "max": 9999.99,
    "mean": 245.67
  }
}

**Sample Values Showing Issue:**
[150.00, 275.50, 89.99, 425.00, 189.75, 567.25, 99.99, 345.50, 1234.56, 78.90]

**Task:**
Generate a 2-3 sentence explanation that:
1. Explains what this issue is in simple terms
2. Describes the SPECIFIC impact on visualizations (charts, graphs, plots)
3. Uses concrete examples relevant to this data

Focus on the visualization impact, not recommendations. Be educational and
specific to this situation.

Return ONLY the explanation text, no JSON, no extra formatting.
```

**Step 2:** Call GPT-4
```python
response = self.client.chat.completions.create(
    model=OPENAI_MODEL,  # "gpt-4o"
    messages=[
        {
            "role": "system",
            "content": "You are a data visualization expert who explains how data quality issues affect visualizations in clear, educational terms."
        },
        {
            "role": "user",
            "content": prompt
        }
    ],
    temperature=0.7,      # Slightly higher for natural language
    max_tokens=300        # Concise responses
)
```

**Step 3:** Extract and return response
```python
impact_text = response.choices[0].message.content.strip()
return impact_text
```

**Example response from GPT-4:**
```
"The 'sales_amount' column is missing 87 values (8.7% of your transactions). In a
time-series line chart, these gaps will create disconnected segments where the line
breaks, making it difficult to identify continuous sales trends. Bar charts comparing
monthly totals will show artificially lower values for months with missing data,
and scatter plots correlating sales with other variables will exclude these 87
transactions entirely, potentially hiding important patterns in your pricing or
customer behavior."
```

**Step 4:** Fallback on error
```python
except Exception as e:
    print(f"[WARNING] Failed to generate visualization impact: {str(e)}")
    return "This data quality issue may affect the accuracy and clarity of your visualizations, potentially leading to misleading or incomplete visual representations of your data."
```

#### C. Overall Dataset Analysis

```python
def analyze_dataset(
    self,
    dataset_summary: Dict[str, Any],
    column_statistics: List[Dict[str, Any]],
    sample_rows: List[Dict[str, Any]],
    detected_issues_summary: Dict[str, Any]
) -> Dict[str, Any]:
```

**Step-by-Step:**

**Step 1:** Build prompts from templates
```python
system_prompt = build_system_prompt()
user_prompt = build_user_prompt(
    dataset_summary,
    column_statistics,
    sample_rows,
    detected_issues_summary
)
```

**Step 2:** Call GPT-4 with JSON mode
```python
response = self.client.chat.completions.create(
    model=OPENAI_MODEL,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    temperature=OPENAI_TEMPERATURE,
    max_tokens=OPENAI_MAX_TOKENS,
    response_format={"type": "json_object"}  # Forces JSON response
)
```

**Step 3:** Parse JSON response
```python
content = response.choices[0].message.content
parsed_response = json.loads(content)
```

**Step 4:** Return structured result
```python
return {
    "success": True,
    "summary": parsed_response['summary'],
    "visualization_concerns": parsed_response.get('visualization_concerns', []),
    "additional_issues": parsed_response.get('additional_issues', []),
    "usage": {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }
}
```

---

## 7. `prompts.py` - Prompt Templates

### Purpose
Contains all prompt engineering templates for GPT-4. Clean separation of AI logic from code.

### Key Functions

#### A. System Prompt for Overall Analysis

```python
def build_system_prompt() -> str:
    return """You are an expert data quality analyst specializing in exploratory
    data analysis (EDA) for data visualization projects.

    Your role is to analyze CSV datasets and identify data quality issues that
    could impact visualization and analysis. Focus on issues that would affect:
    - Chart readability and accuracy
    - Statistical validity
    - User interpretation
    - Performance and rendering

    **Analysis Guidelines:**
    1. Be specific about which columns are affected
    2. Quantify issues with percentages and counts when possible
    3. Prioritize issues by impact on visualization
    4. Provide actionable recommendations
    5. Consider the visualization use case

    **Output Format:**
    You must respond with a valid JSON object with this structure:
    {
      "summary": "2-3 sentence overall assessment of data quality",
      "visualization_concerns": [
        "Specific concern 1 about visualization",
        "Specific concern 2 about visualization"
      ],
      "additional_issues": [
        {
          "type": "issue_type",
          "severity": "critical|warning|info",
          "title": "Brief title",
          "description": "Detailed description",
          "affected_columns": ["col1", "col2"],
          "recommendation": "What to do about it",
          "visualization_impact": "Educational explanation..."
        }
      ]
    }

    **Severity Guidelines:**
    - CRITICAL: Issues that prevent meaningful visualization or analysis
    - WARNING: Issues that may mislead or reduce visualization quality
    - INFO: Minor issues or observations worth noting

    Be concise but thorough. Focus on actionable insights."""
```

#### B. User Prompt for Overall Analysis

```python
def build_user_prompt(
    dataset_summary: Dict[str, Any],
    column_statistics: List[Dict[str, Any]],
    sample_rows: List[Dict[str, Any]],
    detected_issues_summary: Dict[str, Any]
) -> str:
```

**Builds a detailed prompt with:**

1. **Dataset Overview Section**
```python
**Dataset Overview:**
- Total Rows: 1,000
- Total Columns: 10
- Overall Completeness: 95.0%
- Duplicate Rows: 15 (1.5%)
- Memory Usage: 1.20 MB
```

2. **Column Details Section**
```python
**Column Details:**
- price (float64): 87 unique values, 0.5% missing, 3 outliers detected
- category (object): 8 unique values, 0.0% missing, HIGH CARDINALITY
- ...
```

3. **Detected Issues Summary**
```python
**Programmatically Detected Issues:**
- Missing Values: 3 columns affected
- Outliers: 2 columns with outliers
- High Cardinality: 1 columns
- Duplicate Rows: 15
```

4. **Sample Data**
```python
**Sample Data (first 20 rows):**
```json
[
  {"date": "2024-01-01", "product": "Widget", "quantity": 10, "price": 29.99},
  ...
]
```
```

5. **Task Instructions**
```python
Based on this information, provide your analysis focusing on:
1. Issues not captured by basic statistics
2. Patterns in the sample data that could cause visualization problems
3. Data type mismatches or format inconsistencies
4. Relationships between columns that could cause confusion
5. Recommendations for data cleaning before visualization

Remember to return a valid JSON object as specified in your instructions.
```

#### C. Visualization Impact Prompt

```python
def build_visualization_impact_prompt(
    issue_title: str,
    issue_type: str,
    issue_description: str,
    affected_columns: List[str],
    column_details: Dict[str, Any],
    sample_values: List[Any] = None
) -> str:
```

**Builds targeted prompt for single issue:**

```
You are a data visualization expert. Generate a clear, educational explanation
of how this specific data quality issue will affect data visualizations.

**Issue Details:**
- Title: [issue_title]
- Type: [issue_type]
- Description: [issue_description]
- Affected Columns: [affected_columns]

**Column Context:**
[column_details as JSON]

**Sample Values Showing Issue:**
[sample_values as JSON]

**Task:**
Generate a 2-3 sentence explanation that:
1. Explains what this issue is in simple terms
2. Describes the SPECIFIC impact on visualizations (charts, graphs, plots)
3. Uses concrete examples relevant to this data

Focus on the visualization impact, not recommendations. Be educational and
specific to this situation.

Return ONLY the explanation text, no JSON, no extra formatting.
```

---

## Complete Execution Flow

### Timeline of a Full Analysis

```
User uploads CSV
     ↓
Frontend calls /agents/eda/analyze
     ↓
Backend (routes/eda.py) receives request
     ↓
InspectionAnalyzer.analyze_csv() starts
     ↓
┌─────────────────────────────────────────────────┐
│ STEP 1: Load CSV (0.5s)                         │
│ - Read file with pandas                         │
│ - Get file size                                 │
└─────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────┐
│ STEP 2: Calculate Dataset Summary (0.3s)        │
│ - Count rows/columns                            │
│ - Detect duplicate rows                         │
│ - Detect duplicate columns                      │
│ - Calculate completeness                        │
│ - Measure memory usage                          │
└─────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────┐
│ STEP 3: Calculate Column Statistics (1.5s)      │
│ For each column:                                │
│   - Basic: nulls, unique count                  │
│   - Numeric: min/max/mean/median/std            │
│   - Outliers: Run 3 detection methods           │
│   - Distribution: skewness, kurtosis            │
│   - Categorical: top values, cardinality        │
└─────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────┐
│ STEP 4: Detect Issues (0.8s)                    │
│ - Check each column for missing values          │
│ - Check for duplicate rows (if found)           │
│ - Check for duplicate columns (if found)        │
│ - Check numeric columns for outliers            │
│ - Check object columns for mixed types          │
│ - Check dataset size                            │
│ Result: List of issues with placeholders        │
└─────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────┐
│ STEP 5: Enrich with GPT-4 Impacts (5-10s)       │
│ For each issue (e.g., 8 issues):                │
│   1. Gather column details                      │
│   2. Get sample values                          │
│   3. Call GPT-4 (0.5-1s per call)               │
│   4. Replace placeholder with response          │
│   5. Print progress: "✓ Generated impact for X" │
│ Result: All issues now have custom impacts      │
└─────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────┐
│ STEP 6: Get Sample Rows (0.1s)                  │
│ - Take first 20 rows                            │
│ - Convert to JSON                               │
└─────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────┐
│ STEP 7: GPT-4 Overall Analysis (2-3s)           │
│ - Build comprehensive prompt                    │
│ - Send to GPT-4                                 │
│ - Parse JSON response                           │
│ Result: summary, concerns, additional issues    │
└─────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────┐
│ STEP 8: Merge GPT-4 Additional Issues (0.1s)    │
│ - Add any new issues GPT-4 found               │
│ - These already have visualization_impact       │
└─────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────┐
│ STEP 9: Count by Severity (0.1s)                │
│ - critical_count = sum(severity == "critical")  │
│ - warning_count = sum(severity == "warning")    │
│ - info_count = sum(severity == "info")          │
└─────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────┐
│ STEP 10: Build Report (0.1s)                    │
│ - Assemble InspectionReport object              │
│ - Include all components                        │
│ - Calculate duration                            │
│ - Return to API                                 │
└─────────────────────────────────────────────────┘
     ↓
Backend returns JSON to frontend
     ↓
Frontend displays results in Stage 2
     ↓
User sees issues with custom GPT-4 impacts! ✨

Total Time: ~10-15 seconds
```

---

## Real Example Walkthrough

### Input: sales_data.csv

```csv
date,product,quantity,price,region
2024-01-01,Widget,10,29.99,North
2024-01-02,Gadget,,45.00,South
2024-01-03,Widget,10,29.99,North
2024-01-04,Doohickey,5,99999.99,East
2024-01-05,Widget,8,32.00,West
2024-01-06,Gadget,12,47.50,North
```

### Execution Trace

**STEP 1: Load CSV**
```python
df = pd.read_csv("sales_data.csv")
# Result: DataFrame with 6 rows × 5 columns
# file_size_bytes = 245
```

**STEP 2: Dataset Summary**
```python
dataset_summary = DatasetSummary(
    row_count=6,
    column_count=5,
    file_size_bytes=245,
    duplicate_row_count=1,           # Row 3 = Row 1
    duplicate_row_percentage=16.67,
    duplicate_column_count=0,
    overall_completeness=96.67,      # 29/30 cells filled
    memory_usage_mb=0.001
)
```

**STEP 3: Column Statistics**

For "quantity":
```python
ColumnStatistics(
    column_name="quantity",
    data_type="float64",          # pandas converts to float due to NaN
    null_count=1,
    null_percentage=16.67,
    unique_count=4,               # [10, 5, 8, 12]
    min=5.0,
    max=12.0,
    mean=9.0,
    median=9.0,
    std_dev=2.55,
    skewness=0.0,
    kurtosis=-1.3,
    has_outliers=False,
    outlier_count=0
)
```

For "price":
```python
ColumnStatistics(
    column_name="price",
    data_type="float64",
    null_count=0,
    null_percentage=0.0,
    unique_count=5,
    min=29.99,
    max=99999.99,                 # Outlier!
    mean=20040.91,                # Skewed by outlier
    median=38.50,                 # More representative
    std_dev=40746.51,
    has_outliers=True,            # Detected by IQR
    outlier_count=1,              # 99999.99
    outlier_method="iqr"
)
```

**STEP 4: Detect Issues**

Issue #1: Missing Values
```python
DataIssue(
    issue_id="550e8400-...",
    type="missing_values",
    severity="warning",
    title="Missing values in 'quantity'",
    description="Column 'quantity' has 1 missing values (16.7% of total rows).",
    affected_columns=["quantity"],
    recommendation="Moderate missing values. Consider...",
    visualization_impact="[GPT-4 will generate dynamic impact]",  # Placeholder
    metadata={
        'null_count': 1,
        'null_percentage': 16.67
    }
)
```

Issue #2: Duplicate Rows
```python
DataIssue(
    issue_id="660f9511-...",
    type="duplicate_rows",
    severity="warning",
    title="Duplicate rows detected",
    description="Found 1 duplicate rows (16.7% of dataset).",
    affected_columns=[],
    recommendation="Review duplicates...",
    visualization_impact="[GPT-4 will generate dynamic impact]",  # Placeholder
    metadata={
        'duplicate_count': 1,
        'duplicate_percentage': 16.67
    }
)
```

Issue #3: Outliers
```python
DataIssue(
    issue_id="770fa622-...",
    type="outliers_iqr",
    severity="warning",
    title="Outliers detected in 'price'",
    description="Column 'price' contains outliers detected by multiple methods: IQR (1 outliers), Z-score (1 outliers).",
    affected_columns=["price"],
    recommendation="Review outliers...",
    visualization_impact="[GPT-4 will generate dynamic impact]",  # Placeholder
    metadata={
        'iqr_result': {'outlier_count': 1, 'lower_bound': 14.74, 'upper_bound': 62.75},
        'zscore_result': {'outlier_count': 1},
        'methods_count': 2
    }
)
```

**STEP 5: GPT-4 Enrichment**

For Issue #1 (Missing Values), GPT-4 receives:
```python
{
    "issue_title": "Missing values in 'quantity'",
    "issue_type": "missing_values",
    "issue_description": "Column 'quantity' has 1 missing values (16.7% of total rows).",
    "affected_columns": ["quantity"],
    "column_details": {
        "quantity": {
            "data_type": "float64",
            "null_count": 1,
            "null_percentage": 16.67,
            "min": 5.0,
            "max": 12.0,
            "mean": 9.0
        }
    },
    "sample_values": [10.0, 5.0, 10.0, 8.0, 12.0]
}
```

GPT-4 generates:
```
"The 'quantity' column is missing one value (16.7% of your data). In a bar chart
showing product quantities over time, January 2nd will appear with either no bar
or a zero value, creating a misleading gap that suggests no sales occurred that day.
Line charts will show a break in the trend line, and summary statistics like average
daily quantity will be calculated on only 5 out of 6 days, potentially
underestimating your typical sales volume."
```

This replaces the placeholder:
```python
issue.visualization_impact = "The 'quantity' column is missing one value..."
```

**STEP 6: Sample Rows**
```python
sample_rows = [
    {"date": "2024-01-01", "product": "Widget", "quantity": 10.0, "price": 29.99, "region": "North"},
    {"date": "2024-01-02", "product": "Gadget", "quantity": None, "price": 45.00, "region": "South"},
    ...
]
```

**STEP 7: GPT-4 Overall Analysis**

GPT-4 returns:
```python
{
    "success": True,
    "summary": "Your sales dataset is small (6 rows) with moderate data quality issues. The main concerns are a missing quantity value on 2024-01-02, a duplicate transaction, and an extreme price outlier (99999.99) that will significantly skew visualizations. The dataset is otherwise complete and structurally sound.",
    "visualization_concerns": [
        "Price outlier will compress normal price range in charts",
        "Missing quantity value creates gap in time series",
        "Duplicate row inflates Widget sales count"
    ],
    "additional_issues": []
}
```

**STEP 8-10: Finalize**

Count severities:
- critical_count = 0
- warning_count = 3
- info_count = 0

Build final report with all enriched issues.

**Final Output:**
```python
InspectionReport(
    success=True,
    analysis_timestamp="2024-01-07T10:30:45.123Z",
    dataset_summary=DatasetSummary(...),
    column_statistics=[...],
    issues=[
        DataIssue(
            title="Missing values in 'quantity'",
            visualization_impact="The 'quantity' column is missing one value..."  # GPT-4!
        ),
        DataIssue(
            title="Duplicate rows detected",
            visualization_impact="Your dataset contains one duplicate row..."  # GPT-4!
        ),
        DataIssue(
            title="Outliers detected in 'price'",
            visualization_impact="The extreme price value of 99999.99..."  # GPT-4!
        )
    ],
    critical_issues_count=0,
    warning_issues_count=3,
    info_issues_count=0,
    gpt_summary="Your sales dataset is small (6 rows) with moderate...",
    visualization_concerns=[...],
    analysis_duration_seconds=8.45
)
```

---

## Summary

### File Responsibilities

1. **`__init__.py`**: Package initialization, public API
2. **`models.py`**: Data structures and type definitions
3. **`config.py`**: All configurable settings and constants
4. **`data_quality_checks.py`**: Pure detection functions (the algorithms)
5. **`analyzer.py`**: Main orchestrator (ties everything together)
6. **`openai_client.py`**: GPT-4 communication layer
7. **`prompts.py`**: Prompt engineering templates

### Data Flow

```
CSV File
  → Load & Statistics (analyzer.py)
  → Detection Functions (data_quality_checks.py)
  → Issues with Placeholders (models.py)
  → GPT-4 Enrichment (openai_client.py + prompts.py)
  → Final Report (models.py)
  → API Response
```

### Key Concepts

1. **Separation of Concerns**: Each file has one clear responsibility
2. **Pure Functions**: Detection functions have no side effects
3. **Dynamic Generation**: GPT-4 creates custom explanations
4. **Type Safety**: Pydantic models ensure data validity
5. **Configurable**: Easy to tune thresholds without code changes

This architecture makes the inspection agent:
- **Maintainable**: Clear structure, easy to modify
- **Testable**: Pure functions can be unit tested
- **Extensible**: Easy to add new detection methods
- **Robust**: Type validation and error handling throughout

---

**End of Step-by-Step Guide**
