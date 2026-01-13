"""
Problem detection functions for the cleaning agent.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any
import uuid

from .models import Problem, ProblemType
from .config import DETECTION_THRESHOLDS, VISUALIZATION_IMPACT_TEMPLATES


def detect_all_problems(df: pd.DataFrame) -> List[Problem]:
    """
    Detect all data quality problems in the dataset.

    Returns:
        List of Problem objects
    """
    problems = []

    # Detect missing values
    problems.extend(detect_missing_value_problems(df))

    # Detect outliers
    problems.extend(detect_outlier_problems(df))

    # Detect duplicate rows
    duplicate_row_problem = detect_duplicate_row_problem(df)
    if duplicate_row_problem:
        problems.append(duplicate_row_problem)

    # Detect duplicate columns
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
            severity = "critical"
        elif null_percentage >= thresholds["warning_percentage"]:
            severity = "warning"
        else:
            severity = "info"

        # Get visualization impact
        vis_impact = VISUALIZATION_IMPACT_TEMPLATES["missing_values"][severity].format(
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
            severity = "critical"
        else:
            severity = "warning"

        # Get visualization impact
        vis_impact = VISUALIZATION_IMPACT_TEMPLATES["outliers"][severity].format(
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
        severity = "critical"
        vis_impact = VISUALIZATION_IMPACT_TEMPLATES["duplicates_rows"]["critical"]
    else:
        severity = "warning"
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
    severity = "warning" if duplicate_count > 2 else "info"
    vis_impact = VISUALIZATION_IMPACT_TEMPLATES["duplicates_columns"][severity].format(
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
