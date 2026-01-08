# Inspection Agent

> **Advanced Data Quality Analysis for Visualization Pipelines**

The Inspection Agent is a comprehensive data quality assessment system designed specifically for data visualization workflows. It combines programmatic analysis with GPT-4 powered insights to detect issues that could impact visualization quality, accuracy, and performance.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Data Quality Checks](#data-quality-checks)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

---

## Overview

The Inspection Agent analyzes CSV datasets and produces detailed reports on data quality issues, with a focus on how these issues will affect data visualizations. It uses multiple detection algorithms and GPT-4 to provide context-aware, educational explanations.

### Key Capabilities

- **Multi-Method Outlier Detection**: IQR, Z-Score, and Isolation Forest
- **Advanced Missing Value Detection**: Detects null values and null-like strings
- **Duplicate Detection**: Finds duplicate rows and duplicate columns
- **Data Type Analysis**: Identifies mixed types and invalid values
- **Dynamic GPT-4 Integration**: Generates context-aware visualization impact explanations
- **Statistical Analysis**: Distribution metrics, skewness, kurtosis
- **Performance Warnings**: Large dataset and cardinality alerts

---

## Features

### 1. Data Quality Checks

#### Missing Values
- Detects standard null/NaN values
- Identifies null-like strings: `''`, `'null'`, `'NA'`, `'N/A'`, `'nan'`, etc.
- Severity classification: Critical (>20%), Warning (>5%), Info (>1%)

#### Duplicate Detection
- **Duplicate Rows**: Exact row duplicates
- **Duplicate Columns**: Columns with identical values (NEW!)

#### Outlier Detection (3 Methods)
- **IQR Method**: Standard interquartile range (1.5 × IQR)
- **Z-Score Method**: Statistical standard deviations (threshold: 3σ)
- **Isolation Forest**: Machine learning-based anomaly detection

#### Data Type Issues
- **Mixed Data Types**: Columns containing multiple data types
- **Invalid Values**: Values that don't match expected types

### 2. GPT-4 Powered Analysis

#### Dynamic Visualization Impacts
Every detected issue receives a **custom GPT-4 generated explanation** that:
- Explains what the issue is in simple terms
- Describes specific impact on charts, graphs, and plots
- Uses concrete examples relevant to the actual data
- References actual column names and values

#### Smart Summarization
- Overall data quality assessment
- Visualization-specific concerns
- Additional issues not caught by programmatic checks

### 3. Comprehensive Reporting

The Inspection Agent generates structured reports containing:
- **Dataset Summary**: Row/column counts, completeness, duplicates
- **Column Statistics**: Per-column metrics, distributions, cardinality
- **Issues**: Detailed list with severity, recommendations, and impacts
- **GPT-4 Insights**: Natural language summary and concerns

---

## Architecture

```
inspection_agent/
├── __init__.py              # Module exports
├── models.py                # Pydantic data models
├── config.py                # Configuration constants
├── data_quality_checks.py   # Core detection functions
├── analyzer.py              # Main orchestration logic
├── openai_client.py         # GPT-4 integration
├── prompts.py               # GPT-4 prompt templates
└── README.md                # This documentation
```

### Component Overview

#### 1. **Models** (`models.py`)
Pydantic models for request/response:
- `InspectionRequest`: API request parameters
- `InspectionReport`: Complete analysis report
- `DataIssue`: Individual data quality issue
- `ColumnStatistics`: Per-column metrics
- `DatasetSummary`: High-level dataset info

#### 2. **Data Quality Checks** (`data_quality_checks.py`)
Pure functions for detection:
- `detect_missing_values()`
- `detect_duplicate_rows()` / `detect_duplicate_columns()`
- `detect_outliers_iqr()` / `detect_outliers_zscore()` / `detect_outliers_isolation_forest()`
- `detect_mixed_data_types()`
- `detect_invalid_values()`
- `analyze_cardinality()`
- `analyze_distribution()`

#### 3. **Analyzer** (`analyzer.py`)
Main orchestrator that:
1. Loads and validates CSV file
2. Calculates dataset and column statistics
3. Runs all quality checks
4. Enriches issues with GPT-4 visualization impacts
5. Sends summary to GPT-4 for additional insights
6. Assembles final report

#### 4. **OpenAI Client** (`openai_client.py`)
Handles all GPT-4 interactions:
- `analyze_dataset()`: Overall analysis and summary
- `generate_visualization_impact()`: Dynamic impact explanations

#### 5. **Prompts** (`prompts.py`)
Prompt engineering templates:
- `build_system_prompt()`: Role and output format
- `build_user_prompt()`: Dataset analysis request
- `build_visualization_impact_prompt()`: Issue-specific impact generation

---

## Installation

### Requirements
- Python 3.14+
- pandas
- numpy
- scipy
- scikit-learn
- openai
- pydantic
- fastapi (for API integration)

### Dependencies

```bash
pip install pandas numpy scipy scikit-learn openai pydantic fastapi
```

### Environment Variables

```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional
OPENAI_MODEL=gpt-4o  # Default model
```

---

## Quick Start

### Python API

```python
from Agents.inspection_agent import InspectionAnalyzer

# Initialize analyzer
analyzer = InspectionAnalyzer()

# Analyze CSV file
report = analyzer.analyze_csv(
    file_path="./data/my_dataset.csv",
    include_sample_rows=True,
    max_sample_rows=20
)

# Access results
print(f"Total Issues: {len(report.issues)}")
print(f"Critical: {report.critical_issues_count}")
print(f"Warnings: {report.warning_issues_count}")
print(f"Info: {report.info_issues_count}")

# Examine issues
for issue in report.issues:
    print(f"\n{issue.severity.upper()}: {issue.title}")
    print(f"Impact: {issue.visualization_impact}")
    print(f"Recommendation: {issue.recommendation}")
```

### REST API

```bash
# Analyze dataset
curl -X POST "http://localhost:8000/agents/eda/analyze" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "temp_file_path": "./uploads/temp_abc123.csv",
    "include_sample_rows": true,
    "max_sample_rows": 20
  }'
```

---

## Data Quality Checks

### Missing Values Detection

**What it checks:**
- Standard null/NaN values
- Null-like strings: `''`, `'null'`, `'NULL'`, `'None'`, `'NA'`, `'N/A'`, `'n/a'`, `'nan'`, `'NaN'`, `'#N/A'`, `'#NA'`, `'missing'`, `'MISSING'`, `'-'`, `'--'`

**Severity Levels:**
- **Critical**: ≥20% missing
- **Warning**: ≥5% missing
- **Info**: ≥1% missing

**Example Output:**
```python
{
    "title": "Missing values in 'sales_amount'",
    "severity": "warning",
    "description": "Column 'sales_amount' has 87 missing values (8.7% of total rows). This includes 12 null-like values (empty strings, 'NA', etc.).",
    "visualization_impact": "Missing values in the 'sales_amount' column create gaps in financial visualizations. Line charts showing sales trends will have broken lines, bar charts will display incomplete comparisons, and summary statistics like averages will be calculated on only 91.3% of your data, potentially skewing insights.",
    "recommendation": "Moderate missing values. Consider: (1) imputation with mean/median/mode, (2) forward/backward fill for time series, or (3) excluding rows with missing values if acceptable."
}
```

### Duplicate Row Detection

**What it checks:**
- Exact duplicate rows across all columns

**Severity Levels:**
- **Warning**: >5% duplicates
- **Info**: ≤5% duplicates

**Example Output:**
```python
{
    "title": "Duplicate rows detected",
    "severity": "warning",
    "description": "Found 234 duplicate rows (6.2% of dataset).",
    "visualization_impact": "With 234 duplicate rows (6.2% of your data), bar charts will show artificially inflated counts, making certain categories appear 6% more frequent than they actually are. Pie charts will have exaggerated slice sizes, and trend lines may show false spikes where duplicates cluster.",
    "recommendation": "Review duplicates to determine if they're intentional. Consider removing duplicates if they represent data entry errors."
}
```

### Duplicate Column Detection

**What it checks:**
- Columns with 100% identical values

**Severity Level:**
- **Warning**: Any duplicate columns found

**Example Output:**
```python
{
    "title": "Duplicate columns detected",
    "severity": "warning",
    "description": "Found 2 pair(s) of duplicate columns: 'customer_id' = 'customer_ID', 'date' = 'transaction_date'",
    "affected_columns": ["customer_id", "customer_ID", "date", "transaction_date"],
    "visualization_impact": "These duplicate columns don't directly distort visualizations but cause confusion when selecting data for charts. Users might accidentally plot 'customer_id' and 'customer_ID' thinking they're different, creating redundant visualizations that waste space and processing power.",
    "recommendation": "Remove duplicate columns to reduce dataset size and avoid confusion. Keep only one column from each duplicate pair."
}
```

### Outlier Detection (Multi-Method)

**What it checks:**

1. **IQR Method**
   - Lower bound: Q1 - 1.5 × IQR
   - Upper bound: Q3 + 1.5 × IQR

2. **Z-Score Method**
   - Threshold: |Z| > 3 (3 standard deviations)

3. **Isolation Forest**
   - Contamination: 10%
   - Minimum samples: 50

**Severity Level:**
- **Warning**: Outliers detected by any method

**Example Output:**
```python
{
    "title": "Outliers detected in 'order_value'",
    "severity": "warning",
    "description": "Column 'order_value' contains outliers detected by multiple methods: IQR (23 outliers), Z-score (18 outliers), Isolation Forest (25 outliers).",
    "visualization_impact": "In the 'order_value' column, 23 extreme values (ranging up to $45,000 while most orders are $20-$100) compress your chart scales dramatically. In a histogram, 95% of your data will be squeezed into the leftmost bin, making the distribution impossible to read. Box plots will show tiny boxes with extremely long whiskers, and scatter plots will have most points clustered in one corner.",
    "recommendation": "Review outliers and consider: (1) removing them if they're errors, (2) capping extreme values, or (3) using log scale for visualization."
}
```

### Mixed Data Type Detection

**What it checks:**
- Columns with multiple data types (strings, numbers, dates, etc.)
- Numeric strings vs. non-numeric text

**Severity Level:**
- **Warning**: Mixed types detected

**Example Output:**
```python
{
    "title": "Mixed data types in 'quantity'",
    "severity": "warning",
    "description": "Column 'quantity' contains multiple data types: str: 85.3%, numeric_string: 92.1%.",
    "visualization_impact": "The 'quantity' column mixes text like 'N/A' and 'pending' with numeric values like '10' and '25'. Bar charts attempting to plot this data will fail or skip 15% of rows silently. Summary statistics will be impossible to calculate, and any visualization expecting numbers will either error out or produce meaningless results.",
    "recommendation": "Standardize the column to a single data type. Convert or clean inconsistent values."
}
```

### Large Dataset Warning

**What it checks:**
- Datasets with >100,000 rows

**Severity Level:**
- **Info**: Performance notice

**Example Output:**
```python
{
    "title": "Large dataset may impact visualization performance",
    "severity": "info",
    "description": "Dataset has 450,000 rows. Visualizations may be slow or cluttered.",
    "visualization_impact": "With 450,000 rows, scatter plots will render as solid masses of color where individual points are indistinguishable. Interactive charts will lag when panning or zooming. Line charts with time series will become thick bands instead of clear lines. Browser-based visualizations may freeze or crash when trying to render this much data.",
    "recommendation": "Consider sampling to ~10,000 rows for interactive visualizations, using aggregation (binning, grouping), or specialized visualization techniques (heatmaps, density plots)."
}
```

---

## API Reference

### InspectionAnalyzer

Main analyzer class for performing data quality inspections.

#### Constructor

```python
InspectionAnalyzer(openai_api_key: str = None)
```

**Parameters:**
- `openai_api_key` (optional): OpenAI API key. Defaults to `OPENAI_API_KEY` environment variable.

**Raises:**
- `ValueError`: If OpenAI API key is not found

#### Methods

##### `analyze_csv()`

```python
analyze_csv(
    file_path: str,
    include_sample_rows: bool = True,
    max_sample_rows: int = 20
) -> InspectionReport
```

Perform comprehensive data quality analysis on a CSV file.

**Parameters:**
- `file_path` (str): Path to CSV file
- `include_sample_rows` (bool): Include sample rows in GPT-4 analysis
- `max_sample_rows` (int): Maximum number of sample rows to send to GPT-4

**Returns:**
- `InspectionReport`: Complete analysis report

**Raises:**
- `FileNotFoundError`: If CSV file doesn't exist

**Example:**
```python
analyzer = InspectionAnalyzer()
report = analyzer.analyze_csv(
    file_path="./data/sales.csv",
    include_sample_rows=True,
    max_sample_rows=20
)
```

### InspectionReport

Complete analysis report returned by the analyzer.

**Attributes:**
```python
class InspectionReport:
    success: bool                           # Analysis success status
    analysis_timestamp: str                 # ISO timestamp
    dataset_summary: DatasetSummary         # High-level metrics
    column_statistics: List[ColumnStatistics]  # Per-column stats
    issues: List[DataIssue]                 # Detected issues
    critical_issues_count: int              # Count of critical issues
    warning_issues_count: int               # Count of warnings
    info_issues_count: int                  # Count of info items
    gpt_summary: str                        # GPT-4 assessment
    visualization_concerns: List[str]       # Specific concerns
    analysis_duration_seconds: float        # Processing time
```

### DataIssue

Individual data quality issue.

**Attributes:**
```python
class DataIssue:
    issue_id: str                           # Unique identifier
    type: str                               # Issue type (e.g., "missing_values")
    severity: str                           # "critical", "warning", or "info"
    title: str                              # Short title
    description: str                        # Detailed description
    affected_columns: List[str]             # Columns affected
    recommendation: str                     # How to fix
    visualization_impact: str               # GPT-4 generated impact
    metadata: Optional[Dict[str, Any]]      # Additional data
```

### DatasetSummary

High-level dataset metrics.

**Attributes:**
```python
class DatasetSummary:
    row_count: int                          # Total rows
    column_count: int                       # Total columns
    file_size_bytes: int                    # File size
    duplicate_row_count: int                # Number of duplicate rows
    duplicate_row_percentage: float         # Percentage of duplicates
    duplicate_column_count: int             # Number of duplicate columns
    overall_completeness: float             # % of non-null cells
    memory_usage_mb: float                  # Memory usage
```

### ColumnStatistics

Per-column statistics.

**Attributes:**
```python
class ColumnStatistics:
    column_name: str
    data_type: str
    null_count: int
    null_percentage: float
    unique_count: int

    # Numeric columns
    min: Optional[float]
    max: Optional[float]
    mean: Optional[float]
    median: Optional[float]
    std_dev: Optional[float]
    skewness: Optional[float]
    kurtosis: Optional[float]
    has_outliers: Optional[bool]
    outlier_count: Optional[int]
    outlier_method: Optional[str]

    # Categorical columns
    top_values: Optional[List[Dict[str, Any]]]
    is_high_cardinality: Optional[bool]
    cardinality_level: Optional[str]

    # String columns
    min_length: Optional[int]
    max_length: Optional[int]
    avg_length: Optional[float]
```

---

## Configuration

All configuration is in `config.py`. Key settings:

### OpenAI Settings

```python
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_TEMPERATURE = 0.3
OPENAI_MAX_TOKENS = 2000
```

### Detection Thresholds

```python
# Missing Values
MISSING_VALUE_INFO_THRESHOLD = 0.01      # 1%
MISSING_VALUE_WARNING_THRESHOLD = 0.05   # 5%
MISSING_VALUE_CRITICAL_THRESHOLD = 0.20  # 20%

# Outliers
OUTLIER_IQR_MULTIPLIER = 1.5
OUTLIER_ZSCORE_THRESHOLD = 3.0
OUTLIER_ISOLATION_CONTAMINATION = 0.1
OUTLIER_MIN_SAMPLES = 50

# Duplicates
DUPLICATE_ROW_WARNING_THRESHOLD = 0.05   # 5%

# Cardinality
LOW_CARDINALITY_MAX = 10
MEDIUM_CARDINALITY_MAX = 50
HIGH_CARDINALITY_THRESHOLD = 100

# Distribution
SKEWNESS_THRESHOLD = 1.0
KURTOSIS_THRESHOLD = 3.0

# Performance
LARGE_DATASET_THRESHOLD = 100000
VISUALIZATION_SAMPLE_SIZE = 10000
```

### Null Representations

```python
NULL_REPRESENTATIONS = [
    '', 'null', 'NULL', 'None', 'NA', 'N/A', 'n/a',
    'nan', 'NaN', '#N/A', '#NA', 'missing', 'MISSING',
    '-', '--'
]
```

---

## Examples

### Example 1: Basic Analysis

```python
from Agents.inspection_agent import InspectionAnalyzer

analyzer = InspectionAnalyzer()
report = analyzer.analyze_csv("sales_data.csv")

print(f"Analysis Complete!")
print(f"Dataset: {report.dataset_summary.row_count:,} rows × {report.dataset_summary.column_count} columns")
print(f"Completeness: {report.dataset_summary.overall_completeness:.1f}%")
print(f"\nIssues Found:")
print(f"  - Critical: {report.critical_issues_count}")
print(f"  - Warnings: {report.warning_issues_count}")
print(f"  - Info: {report.info_issues_count}")
```

### Example 2: Filtering Issues by Severity

```python
report = analyzer.analyze_csv("data.csv")

# Get only critical issues
critical_issues = [i for i in report.issues if i.severity == "critical"]

for issue in critical_issues:
    print(f"\n🚨 {issue.title}")
    print(f"Columns: {', '.join(issue.affected_columns)}")
    print(f"Impact: {issue.visualization_impact}")
    print(f"Fix: {issue.recommendation}")
```

### Example 3: Column-Level Analysis

```python
report = analyzer.analyze_csv("data.csv")

# Analyze specific column
for col in report.column_statistics:
    if col.column_name == "price":
        print(f"Column: {col.column_name}")
        print(f"Type: {col.data_type}")
        print(f"Missing: {col.null_percentage:.1f}%")
        print(f"Unique: {col.unique_count}")

        if col.has_outliers:
            print(f"Outliers: {col.outlier_count} detected using {col.outlier_method}")

        if col.skewness:
            print(f"Skewness: {col.skewness:.2f}")
```

### Example 4: Export Issues to JSON

```python
import json

report = analyzer.analyze_csv("data.csv")

# Convert issues to JSON
issues_json = [issue.dict() for issue in report.issues]

with open("data_quality_issues.json", "w") as f:
    json.dump(issues_json, f, indent=2)
```

### Example 5: Custom API Integration

```python
from fastapi import APIRouter, HTTPException
from Agents.inspection_agent import InspectionAnalyzer, InspectionRequest, InspectionReport

router = APIRouter()

@router.post("/inspect", response_model=InspectionReport)
async def inspect_dataset(request: InspectionRequest):
    try:
        analyzer = InspectionAnalyzer()
        report = analyzer.analyze_csv(
            file_path=request.temp_file_path,
            include_sample_rows=request.include_sample_rows,
            max_sample_rows=request.max_sample_rows
        )
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Troubleshooting

### Issue: "OpenAI API key not found"

**Solution:**
```bash
export OPENAI_API_KEY="sk-your-key-here"
# or
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

### Issue: "Failed to generate visualization impact"

**Cause:** GPT-4 API error or rate limit

**Solution:**
- Check API key is valid
- Verify API quota and rate limits
- The agent will use fallback messages automatically

### Issue: "Memory error with large datasets"

**Cause:** Dataset too large to fit in memory

**Solution:**
```python
# Use chunking for very large files
import pandas as pd

# Process in chunks
chunk_size = 10000
for chunk in pd.read_csv("large_file.csv", chunksize=chunk_size):
    # Process each chunk
    pass
```

### Issue: "Isolation Forest not detecting outliers"

**Cause:** Dataset too small (< 50 samples)

**Solution:**
- Use IQR or Z-Score methods instead
- Reduce `OUTLIER_MIN_SAMPLES` in config

### Issue: Slow performance

**Optimization tips:**
1. Disable GPT-4 enrichment for quick scans:
   ```python
   # Temporarily disable in analyzer.py
   # Comment out: issues = self._enrich_issues_with_impacts(...)
   ```

2. Reduce sample rows:
   ```python
   report = analyzer.analyze_csv("data.csv", max_sample_rows=5)
   ```

3. Skip sample rows entirely:
   ```python
   report = analyzer.analyze_csv("data.csv", include_sample_rows=False)
   ```

---

## Comparison: Inspection Agent vs. EDA Agent

| Feature | EDA Agent | Inspection Agent |
|---------|-----------|------------------|
| Outlier Detection | IQR only | IQR + Z-Score + Isolation Forest |
| Duplicate Detection | Rows only | Rows + Columns |
| Missing Values | Basic | Advanced (includes null-like strings) |
| Data Type Analysis | No | Yes (mixed types, invalid values) |
| Visualization Impact | Hardcoded | **GPT-4 Dynamic Generation** |
| Python Support | Requires <3.9 libraries | Native 3.14+ |
| Dependencies | ydata-quality (outdated) | Built-in (pandas, scipy, sklearn) |
| Performance | Limited | Optimized with multiple methods |

---

## Best Practices

### 1. Always Review Critical Issues First
```python
critical = [i for i in report.issues if i.severity == "critical"]
# Address these before proceeding
```

### 2. Use Metadata for Deeper Insights
```python
for issue in report.issues:
    if issue.type == "outliers_iqr":
        iqr_result = issue.metadata['iqr_result']
        print(f"Outlier bounds: {iqr_result['lower_bound']} to {iqr_result['upper_bound']}")
```

### 3. Consider Context
Not all issues need fixing. Some "issues" may be legitimate:
- Duplicate rows in transaction logs (same customer, same product)
- Outliers in salary data (executives)
- Missing values in optional fields

### 4. Iterate
```python
# Initial analysis
report1 = analyzer.analyze_csv("data.csv")

# Fix issues...
# Re-analyze
report2 = analyzer.analyze_csv("data_cleaned.csv")

# Compare
print(f"Issues reduced: {len(report1.issues)} → {len(report2.issues)}")
```

---

## License

This project is part of the Natural Language for Data Visualization system.

---

## Support

For issues, questions, or contributions:
- Check existing issues in the project repository
- Review the troubleshooting section above
- Ensure OpenAI API key is properly configured

---

**Built with ❤️ for better data visualization**
