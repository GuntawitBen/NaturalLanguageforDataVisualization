"""
Problem detection functions for the cleaning agent.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import uuid
import re
from collections import Counter

from .models import Problem, ProblemType, ProblemSeverity
from .config import DETECTION_THRESHOLDS, VISUALIZATION_IMPACT_TEMPLATES


def detect_all_problems(df: pd.DataFrame) -> List[Problem]:
    """
    Detect all data quality problems in the dataset.
    
    Detection Order (Priority):
    1. Format Inconsistencies - Must be fixed first for accurate subsequent detection
    2. Missing Values - More accurate after format standardization
    3. Outliers - Requires properly formatted numeric data
    4. Duplicate Rows - Structural issue
    5. Duplicate Columns - Structural issue

    Returns:
        List of Problem objects ordered by priority
    """
    problems = []

    # PRIORITY 1: Detect format inconsistencies FIRST
    # This ensures data is in consistent format before other checks
    # Example: "N/A" in date columns won't be detected as missing until format is standardized
    problems.extend(detect_format_inconsistency_problems(df))

    # PRIORITY 2: Detect missing values
    # Now that formats are consistent, missing values are more accurately detected
    problems.extend(detect_missing_value_problems(df))

    # PRIORITY 3: Detect outliers
    # Properly formatted numeric data allows accurate outlier detection
    problems.extend(detect_outlier_problems(df))

    # PRIORITY 4: Detect duplicate rows
    duplicate_row_problem = detect_duplicate_row_problem(df)
    if duplicate_row_problem:
        problems.append(duplicate_row_problem)

    # PRIORITY 5: Detect duplicate columns
    duplicate_column_problem = detect_duplicate_column_problem(df)
    if duplicate_column_problem:
        problems.append(duplicate_column_problem)

    return problems


def detect_missing_value_problems(df: pd.DataFrame) -> List[Problem]:
    """
    Detect missing value problems for each column with missing data.

    Returns:
        List of Problem objects for columns with missing values
    """
    problems = []
    thresholds = DETECTION_THRESHOLDS["missing_values"]

    for column in df.columns:
        null_count = df[column].isna().sum()
        null_percentage = (null_count / len(df)) * 100 if len(df) > 0 else 0

        # Only report if above minimum threshold
        if null_percentage < thresholds["min_percentage"]:
            continue

        # Determine severity
        if null_percentage >= thresholds["critical_percentage"]:
            severity = ProblemSeverity.CRITICAL
        elif null_percentage >= thresholds["warning_percentage"]:
            severity = ProblemSeverity.WARNING
        else:
            severity = ProblemSeverity.INFO

        # Get visualization impact
        vis_impact = VISUALIZATION_IMPACT_TEMPLATES["missing_values"][severity.name.lower()].format(
            percentage=f"{null_percentage:.1f}"
        )

        problem = Problem(
            problem_id=str(uuid.uuid4()),
            problem_type=ProblemType.MISSING_VALUES,
            severity=severity,
            title=f"Missing Values in '{column}'",
            description=f"{null_count} rows ({null_percentage:.1f}%) have missing values in the '{column}' column.",
            affected_columns=[column],
            visualization_impact=vis_impact,
            metadata={
                "null_count": int(null_count),
                "null_percentage": float(null_percentage),
                "column": column
            }
        )
        problems.append(problem)

    return problems


def detect_outlier_problems(df: pd.DataFrame) -> List[Problem]:
    """
    Detect outlier problems for numeric columns using IQR method.

    Returns:
        List of Problem objects for columns with outliers
    """
    problems = []
    thresholds = DETECTION_THRESHOLDS["outliers"]

    # Only check numeric columns
    numeric_columns = df.select_dtypes(include=[np.number]).columns

    for column in numeric_columns:
        outlier_info = _detect_outliers_iqr(df, column)

        if outlier_info["outlier_count"] < thresholds["min_count"]:
            continue

        outlier_percentage = (outlier_info["outlier_count"] / len(df)) * 100 if len(df) > 0 else 0

        # Determine severity
        if outlier_percentage >= thresholds["critical_percentage"]:
            severity = ProblemSeverity.CRITICAL
        else:
            severity = ProblemSeverity.WARNING

        # Get visualization impact
        vis_impact = VISUALIZATION_IMPACT_TEMPLATES["outliers"][severity.name.lower()].format(
            count=outlier_info["outlier_count"],
            percentage=f"{outlier_percentage:.1f}"
        )

        problem = Problem(
            problem_id=str(uuid.uuid4()),
            problem_type=ProblemType.OUTLIERS,
            severity=severity,
            title=f"Outliers in '{column}'",
            description=f"{outlier_info['outlier_count']} outliers ({outlier_percentage:.1f}%) detected using IQR method in the '{column}' column.",
            affected_columns=[column],
            visualization_impact=vis_impact,
            metadata={
                "outlier_count": outlier_info["outlier_count"],
                "outlier_percentage": float(outlier_percentage),
                "lower_bound": outlier_info["lower_bound"],
                "upper_bound": outlier_info["upper_bound"],
                "example_outliers": outlier_info["example_outliers"],
                "column": column
            }
        )
        problems.append(problem)

    return problems


def detect_duplicate_row_problem(df: pd.DataFrame) -> Problem:
    """
    Detect duplicate rows in the dataset.

    Returns:
        Problem object if duplicates found, None otherwise
    """
    thresholds = DETECTION_THRESHOLDS["duplicates"]

    duplicate_count = df.duplicated().sum()

    if duplicate_count < thresholds["min_count"]:
        return None

    duplicate_percentage = (duplicate_count / len(df)) * 100 if len(df) > 0 else 0

    # Determine severity
    if duplicate_percentage >= thresholds["critical_percentage"]:
        severity = ProblemSeverity.CRITICAL
        vis_impact = VISUALIZATION_IMPACT_TEMPLATES["duplicates_rows"]["critical"]
    else:
        severity = ProblemSeverity.WARNING
        vis_impact = VISUALIZATION_IMPACT_TEMPLATES["duplicates_rows"]["warning"]

    vis_impact = vis_impact.format(
        count=duplicate_count,
        percentage=f"{duplicate_percentage:.1f}"
    )

    return Problem(
        problem_id=str(uuid.uuid4()),
        problem_type=ProblemType.DUPLICATES_ROWS,
        severity=severity,
        title="Duplicate Rows Detected",
        description=f"{duplicate_count} duplicate rows ({duplicate_percentage:.1f}%) found in the dataset.",
        affected_columns=[],  # Affects all columns
        visualization_impact=vis_impact,
        metadata={
            "duplicate_count": int(duplicate_count),
            "duplicate_percentage": float(duplicate_percentage)
        }
    )


def detect_duplicate_column_problem(df: pd.DataFrame) -> Problem:
    """
    Detect duplicate columns in the dataset.

    Returns:
        Problem object if duplicate columns found, None otherwise
    """
    duplicate_pairs = _detect_duplicate_columns(df)

    if len(duplicate_pairs) == 0:
        return None

    # Extract unique duplicate columns (each column may appear in multiple pairs)
    duplicate_columns = set()
    for col1, col2 in duplicate_pairs:
        duplicate_columns.add(col2)  # Keep first column, mark second as duplicate

    duplicate_count = len(duplicate_columns)

    # Determine severity (duplicate columns are typically warning or info)
    severity = ProblemSeverity.WARNING if duplicate_count > 2 else ProblemSeverity.INFO
    vis_impact = VISUALIZATION_IMPACT_TEMPLATES["duplicates_columns"][severity.name.lower()].format(
        count=duplicate_count
    )

    # Format column pairs for description
    pair_descriptions = [f"'{col1}' and '{col2}'" for col1, col2 in duplicate_pairs[:3]]
    if len(duplicate_pairs) > 3:
        pair_descriptions.append(f"and {len(duplicate_pairs) - 3} more pairs")

    return Problem(
        problem_id=str(uuid.uuid4()),
        problem_type=ProblemType.DUPLICATES_COLUMNS,
        severity=severity,
        title="Duplicate Columns Detected",
        description=f"{duplicate_count} duplicate columns found: {', '.join(pair_descriptions)}.",
        affected_columns=list(duplicate_columns),
        visualization_impact=vis_impact,
        metadata={
            "duplicate_count": duplicate_count,
            "duplicate_pairs": duplicate_pairs,
            "columns_to_remove": list(duplicate_columns)
        }
    )


# ============================================================================
# Helper Functions
# ============================================================================

def _detect_outliers_iqr(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """
    Detect outliers using IQR method.

    Returns:
        Dict with outlier information including sample values
    """
    values = df[column].dropna()

    if len(values) < 4:  # Need at least 4 values for IQR
        return {
            'outlier_count': 0,
            'lower_bound': None,
            'upper_bound': None,
            'example_outliers': []
        }

    Q1 = values.quantile(0.25)
    Q3 = values.quantile(0.75)
    IQR = Q3 - Q1

    iqr_multiplier = DETECTION_THRESHOLDS["outliers"]["iqr_multiplier"]
    lower_bound = Q1 - iqr_multiplier * IQR
    upper_bound = Q3 + iqr_multiplier * IQR

    outlier_mask = (df[column] < lower_bound) | (df[column] > upper_bound)
    outlier_count = outlier_mask.sum()

    # Get sample outlier values (up to 5 examples)
    example_outliers = []
    if outlier_count > 0:
        outlier_values = df.loc[outlier_mask, column].dropna()
        # Get unique outlier values, sorted by how extreme they are
        unique_outliers = outlier_values.unique()
        # Take up to 5 examples, prefer extreme values
        sorted_outliers = sorted(unique_outliers, key=lambda x: abs(x - values.median()), reverse=True)
        example_outliers = [round(float(v), 2) for v in sorted_outliers[:5]]

    return {
        'outlier_count': int(outlier_count),
        'lower_bound': float(lower_bound),
        'upper_bound': float(upper_bound),
        'example_outliers': example_outliers
    }


def _detect_duplicate_columns(df: pd.DataFrame) -> List[tuple]:
    """
    Detect duplicate columns (columns with identical values).

    Returns:
        List of tuples containing duplicate column pairs
    """
    duplicate_pairs = []
    columns = df.columns.tolist()

    for i in range(len(columns)):
        for j in range(i + 1, len(columns)):
            col1, col2 = columns[i], columns[j]

            # Compare columns element-wise
            try:
                if df[col1].equals(df[col2]):
                    duplicate_pairs.append((col1, col2))
            except:
                # Handle comparison errors (e.g., different dtypes)
                continue

    return duplicate_pairs


# ============================================================================
# Format Inconsistency Detection
# ============================================================================

# Date format patterns with their canonical names
DATE_PATTERNS = {
    "YYYY-MM-DD": r"^\d{4}-\d{2}-\d{2}$",
    "DD/MM/YYYY": r"^\d{2}/\d{2}/\d{4}$",
    "MM/DD/YYYY": r"^\d{2}/\d{2}/\d{4}$",
    "DD-MM-YYYY": r"^\d{2}-\d{2}-\d{4}$",
    "MM-DD-YYYY": r"^\d{2}-\d{2}-\d{4}$",
    "YYYY/MM/DD": r"^\d{4}/\d{2}/\d{2}$",
    "DD.MM.YYYY": r"^\d{2}\.\d{2}\.\d{4}$",
    "Mon DD, YYYY": r"^[A-Za-z]{3}\s+\d{1,2},?\s+\d{4}$",
    "Month DD, YYYY": r"^[A-Za-z]+\s+\d{1,2},?\s+\d{4}$",
    "DD Mon YYYY": r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}$",
    "DD Month YYYY": r"^\d{1,2}\s+[A-Za-z]+\s+\d{4}$",
}

# Boolean value patterns
BOOLEAN_PATTERNS = {
    "Yes/No": {"yes", "no"},
    "Y/N": {"y", "n"},
    "True/False": {"true", "false"},
    "1/0": {"1", "0"},
    "T/F": {"t", "f"},
    "On/Off": {"on", "off"},
}

# Case patterns
CASE_PATTERNS = {
    "UPPERCASE": lambda s: s.isupper(),
    "lowercase": lambda s: s.islower(),
    "Title Case": lambda s: s.istitle(),
    "Sentence case": lambda s: s[0].isupper() and s[1:].islower() if len(s) > 1 else s.isupper(),
}


def detect_format_inconsistency_problems(df: pd.DataFrame) -> List[Problem]:
    """
    Detect format inconsistency problems in the dataset.

    Checks for:
    - Date format inconsistencies
    - Boolean/Yes-No format inconsistencies
    - Text case inconsistencies
    - Mixed data types (numeric columns with text values)

    Returns:
        List of Problem objects for columns with format inconsistencies
    """
    problems = []
    thresholds = DETECTION_THRESHOLDS.get("format_inconsistency", {
        "min_inconsistency_percentage": 5.0,
        "min_unique_formats": 2
    })

    for column in df.columns:
        # Skip numeric columns for format checks (but check for mixed types below)
        if pd.api.types.is_numeric_dtype(df[column]):
            continue

        non_null_values = df[column].dropna()
        if len(non_null_values) < 3:  # Need at least 3 values to detect patterns
            continue

        # Check for mixed data types (numeric strings mixed with text)
        mixed_type_problem = _detect_mixed_numeric_text(df, column, non_null_values, thresholds)
        if mixed_type_problem:
            problems.append(mixed_type_problem)
            continue  # Don't check other formats if it's a mixed type issue

        # Check for date format inconsistencies
        date_problem = _detect_date_format_inconsistency(df, column, non_null_values, thresholds)
        if date_problem:
            problems.append(date_problem)
            continue  # Don't check other formats if it's a date column

        # Check for boolean format inconsistencies
        boolean_problem = _detect_boolean_format_inconsistency(df, column, non_null_values, thresholds)
        if boolean_problem:
            problems.append(boolean_problem)
            continue

        # Check for case inconsistencies (only for text columns that look like names/titles)
        case_problem = _detect_case_inconsistency(df, column, non_null_values, thresholds)
        if case_problem:
            problems.append(case_problem)

    return problems


def _detect_mixed_numeric_text(
    df: pd.DataFrame,
    column: str,
    values: pd.Series,
    thresholds: Dict
) -> Optional[Problem]:
    """
    Detect if a column contains a mix of numeric and text values.
    This indicates a data quality issue where a numeric column has text entries.
    """
    str_values = values.astype(str)
    
    numeric_count = 0
    text_count = 0
    numeric_examples = []
    text_examples = []
    
    for val in str_values:
        try:
            float(val)
            numeric_count += 1
            if len(numeric_examples) < 3:
                numeric_examples.append(val)
        except (ValueError, TypeError):
            text_count += 1
            if len(text_examples) < 3:
                text_examples.append(val)
    
    # Need both numeric and text values
    if numeric_count == 0 or text_count == 0:
        return None
    
    # At least 50% should be numeric for this to be considered a numeric column
    if numeric_count < len(values) * 0.5:
        return None
    
    text_percentage = (text_count / len(values)) * 100
    severity = ProblemSeverity.WARNING if text_percentage > 20 else ProblemSeverity.INFO
    
    vis_impact = f"Mixed data types will prevent proper numeric analysis and may cause visualization errors. {text_count} text values found in what appears to be a numeric column."
    
    return Problem(
        problem_id=str(uuid.uuid4()),
        problem_type=ProblemType.FORMAT_INCONSISTENCY,
        severity=severity,
        title=f"Mixed Data Types in '{column}'",
        description=f"Column '{column}' contains {numeric_count} numeric values and {text_count} text values. This should be a numeric column.",
        affected_columns=[column],
        visualization_impact=vis_impact,
        metadata={
            "format_type": "mixed_numeric_text",
            "column": column,
            "numeric_count": int(numeric_count),
            "text_count": int(text_count),
            "text_percentage": float(text_percentage),
            "numeric_examples": numeric_examples,
            "text_examples": text_examples,
            "total_values": int(len(values))
        }
    )


def _detect_date_format_inconsistency(
    df: pd.DataFrame,
    column: str,
    values: pd.Series,
    thresholds: Dict
) -> Optional[Problem]:
    """
    Detect if a column contains dates in multiple formats.
    """
    # Convert to strings
    str_values = values.astype(str)

    # Count how many values match each date pattern
    format_counts = {}
    matched_values = set()

    for format_name, pattern in DATE_PATTERNS.items():
        matches = str_values.str.match(pattern, na=False)
        match_count = matches.sum()
        if match_count > 0:
            format_counts[format_name] = match_count
            matched_values.update(str_values[matches].tolist())

    # Check if we have multiple formats
    if len(format_counts) < 2:
        return None

    # Calculate total matched and check if enough values are dates
    total_matched = len(matched_values)
    if total_matched < len(values) * 0.5:  # At least 50% should be dates
        return None

    # Sort formats by count
    sorted_formats = sorted(format_counts.items(), key=lambda x: x[1], reverse=True)
    detected_formats = {fmt: int(count) for fmt, count in sorted_formats}  # Convert to Python int

    # Get examples of each format
    format_examples = {}
    for format_name, pattern in DATE_PATTERNS.items():
        if format_name in detected_formats:
            matches = str_values[str_values.str.match(pattern, na=False)]
            format_examples[format_name] = matches.head(3).tolist()

    # Create problem
    inconsistent_count = total_matched - sorted_formats[0][1]
    inconsistent_percentage = (inconsistent_count / len(values)) * 100

    severity = ProblemSeverity.WARNING if inconsistent_percentage > 20 else ProblemSeverity.INFO

    vis_impact = VISUALIZATION_IMPACT_TEMPLATES.get("format_inconsistency", {}).get(
        "date",
        "Inconsistent date formats may cause parsing errors and incorrect chronological ordering in visualizations."
    )

    return Problem(
        problem_id=str(uuid.uuid4()),
        problem_type=ProblemType.FORMAT_INCONSISTENCY,
        severity=severity,
        title=f"Inconsistent Date Formats in '{column}'",
        description=f"Found {len(detected_formats)} different date formats in '{column}': {', '.join(detected_formats.keys())}.",
        affected_columns=[column],
        visualization_impact=vis_impact,
        metadata={
            "format_type": "date",
            "column": column,
            "detected_formats": detected_formats,
            "format_examples": format_examples,
            "total_values": int(len(values)),
            "inconsistent_count": int(inconsistent_count),
            "inconsistent_percentage": float(inconsistent_percentage)
        }
    )


def _detect_boolean_format_inconsistency(
    df: pd.DataFrame,
    column: str,
    values: pd.Series,
    thresholds: Dict
) -> Optional[Problem]:
    """
    Detect if a column contains boolean values in multiple formats.
    """
    # Get unique values (lowercased for comparison)
    str_values = values.astype(str).str.strip()
    unique_values = set(str_values.str.lower().unique())

    # Check which boolean patterns are present
    detected_patterns = {}
    for pattern_name, pattern_values in BOOLEAN_PATTERNS.items():
        matching_values = unique_values.intersection(pattern_values)
        if len(matching_values) > 0:
            # Count how many rows match this pattern
            mask = str_values.str.lower().isin(pattern_values)
            count = mask.sum()
            if count > 0:
                detected_patterns[pattern_name] = {
                    "count": count,
                    "values": list(matching_values)
                }

    # Check if we have multiple formats
    if len(detected_patterns) < 2:
        return None

    # Calculate coverage - should cover most of the data
    total_matched = sum(p["count"] for p in detected_patterns.values())
    if total_matched < len(values) * 0.8:  # At least 80% should be boolean-like
        return None

    # Get examples of actual values
    format_examples = {}
    for pattern_name, pattern_info in detected_patterns.items():
        pattern_values = BOOLEAN_PATTERNS[pattern_name]
        mask = str_values.str.lower().isin(pattern_values)
        examples = str_values[mask].head(3).tolist()
        format_examples[pattern_name] = examples

    severity = ProblemSeverity.INFO

    vis_impact = VISUALIZATION_IMPACT_TEMPLATES.get("format_inconsistency", {}).get(
        "boolean",
        "Inconsistent boolean formats may cause grouping errors and incorrect aggregations."
    )

    return Problem(
        problem_id=str(uuid.uuid4()),
        problem_type=ProblemType.FORMAT_INCONSISTENCY,
        severity=severity,
        title=f"Inconsistent Boolean Formats in '{column}'",
        description=f"Found {len(detected_patterns)} different boolean formats: {', '.join(detected_patterns.keys())}.",
        affected_columns=[column],
        visualization_impact=vis_impact,
        metadata={
            "format_type": "boolean",
            "column": column,
            "detected_formats": {k: int(v["count"]) for k, v in detected_patterns.items()},  # Convert to Python int
            "format_examples": format_examples,
            "total_values": len(values)
        }
    )


def _detect_case_inconsistency(
    df: pd.DataFrame,
    column: str,
    values: pd.Series,
    thresholds: Dict
) -> Optional[Problem]:
    """
    Detect if a text column has inconsistent casing (e.g., mix of UPPERCASE, lowercase, Title Case).
    Only applies to columns that look like names or categorical text.
    """
    # Convert to strings and filter out very long values (likely descriptions, not names)
    str_values = values.astype(str).str.strip()
    str_values = str_values[str_values.str.len() <= 50]  # Focus on shorter text
    str_values = str_values[str_values.str.len() >= 2]   # At least 2 characters

    if len(str_values) < 5:
        return None

    # Check for numeric-heavy values (skip if >50% contain numbers)
    has_numbers = str_values.str.contains(r'\d', regex=True)
    if has_numbers.sum() > len(str_values) * 0.5:
        return None

    # Detect case patterns
    case_counts = {
        "UPPERCASE": 0,
        "lowercase": 0,
        "Title Case": 0,
        "Mixed Case": 0
    }

    for val in str_values:
        # Only check alphabetic characters
        alpha_only = ''.join(c for c in val if c.isalpha())
        if len(alpha_only) < 2:
            continue

        if alpha_only.isupper():
            case_counts["UPPERCASE"] += 1
        elif alpha_only.islower():
            case_counts["lowercase"] += 1
        elif val.istitle() or _is_title_case(val):
            case_counts["Title Case"] += 1
        else:
            case_counts["Mixed Case"] += 1

    # Remove zero counts
    case_counts = {k: v for k, v in case_counts.items() if v > 0}

    # Check if we have multiple case styles
    if len(case_counts) < 2:
        return None

    # Check if the inconsistency is significant
    total = sum(case_counts.values())
    if total < 5:
        return None

    # Get the dominant case
    dominant_case = max(case_counts, key=case_counts.get)
    dominant_count = case_counts[dominant_case]

    # If one case dominates >90%, might not be worth reporting
    if dominant_count / total > 0.9:
        return None

    # Get examples of each case
    case_examples = {
        "UPPERCASE": [],
        "lowercase": [],
        "Title Case": [],
        "Mixed Case": []
    }

    for val in str_values:
        alpha_only = ''.join(c for c in val if c.isalpha())
        if len(alpha_only) < 2:
            continue

        if alpha_only.isupper() and len(case_examples["UPPERCASE"]) < 3:
            case_examples["UPPERCASE"].append(val)
        elif alpha_only.islower() and len(case_examples["lowercase"]) < 3:
            case_examples["lowercase"].append(val)
        elif (val.istitle() or _is_title_case(val)) and len(case_examples["Title Case"]) < 3:
            case_examples["Title Case"].append(val)
        elif len(case_examples["Mixed Case"]) < 3:
            case_examples["Mixed Case"].append(val)

    # Remove empty examples
    case_examples = {k: v for k, v in case_examples.items() if v}

    severity = ProblemSeverity.INFO

    vis_impact = VISUALIZATION_IMPACT_TEMPLATES.get("format_inconsistency", {}).get(
        "case",
        "Inconsistent text casing may cause duplicate categories in charts and incorrect groupings."
    )

    return Problem(
        problem_id=str(uuid.uuid4()),
        problem_type=ProblemType.FORMAT_INCONSISTENCY,
        severity=severity,
        title=f"Inconsistent Text Casing in '{column}'",
        description=f"Found {len(case_counts)} different text case styles: {', '.join(case_counts.keys())}.",
        affected_columns=[column],
        visualization_impact=vis_impact,
        metadata={
            "format_type": "case",
            "column": column,
            "detected_formats": {k: int(v) for k, v in case_counts.items()},  # Convert to Python int
            "format_examples": case_examples,
            "total_values": len(str_values)
        }
    )


def _is_title_case(s: str) -> bool:
    """
    Check if a string is in title case, allowing for common exceptions.
    """
    words = s.split()
    if not words:
        return False

    # Common words that don't need to be capitalized in titles
    exceptions = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}

    for i, word in enumerate(words):
        alpha_only = ''.join(c for c in word if c.isalpha())
        if not alpha_only:
            continue

        # First word should always be capitalized
        if i == 0:
            if not alpha_only[0].isupper():
                return False
        # Other words should be capitalized unless they're exceptions
        elif word.lower() not in exceptions:
            if not alpha_only[0].isupper():
                return False

    return True
