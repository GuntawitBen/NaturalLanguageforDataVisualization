"""
Statistical analysis functions for EDA
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from .config import (
    OUTLIER_IQR_MULTIPLIER,
    HIGH_CARDINALITY_THRESHOLD,
    LOW_CARDINALITY_MAX,
    MEDIUM_CARDINALITY_MAX,
    MAX_UNIQUE_VALUES_TO_SHOW,
    SKEWNESS_THRESHOLD,
    KURTOSIS_THRESHOLD
)

def calculate_column_statistics(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """
    Calculate comprehensive statistics for a single column

    Args:
        df: Pandas DataFrame
        column: Column name

    Returns:
        Dictionary with statistical metrics
    """
    col_data = df[column]
    stats = {
        "column_name": column,
        "data_type": str(col_data.dtype),
        "null_count": int(col_data.isnull().sum()),
        "null_percentage": float(col_data.isnull().sum() / len(df) * 100),
        "unique_count": int(col_data.nunique())
    }

    # Numeric columns
    if pd.api.types.is_numeric_dtype(col_data):
        non_null_data = col_data.dropna()

        if len(non_null_data) > 0:
            stats.update({
                "min": float(non_null_data.min()),
                "max": float(non_null_data.max()),
                "mean": float(non_null_data.mean()),
                "median": float(non_null_data.median()),
                "std_dev": float(non_null_data.std()),
                "skewness": float(non_null_data.skew()),
                "kurtosis": float(non_null_data.kurtosis()),
            })

            # Outlier detection using IQR method
            if len(non_null_data) > 3:  # Need at least 4 values for quartiles
                Q1 = non_null_data.quantile(0.25)
                Q3 = non_null_data.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - OUTLIER_IQR_MULTIPLIER * IQR
                upper_bound = Q3 + OUTLIER_IQR_MULTIPLIER * IQR
                outlier_mask = (non_null_data < lower_bound) | (non_null_data > upper_bound)
                stats["has_outliers"] = bool(outlier_mask.any())
                stats["outlier_count"] = int(outlier_mask.sum())
            else:
                stats["has_outliers"] = False
                stats["outlier_count"] = 0

    # Categorical/String columns
    elif pd.api.types.is_string_dtype(col_data) or pd.api.types.is_object_dtype(col_data):
        non_null_data = col_data.dropna()

        if len(non_null_data) > 0:
            # String length statistics
            lengths = non_null_data.astype(str).str.len()
            stats.update({
                "min_length": int(lengths.min()),
                "max_length": int(lengths.max()),
                "avg_length": float(lengths.mean())
            })

            # Cardinality categorization
            unique_count = col_data.nunique()
            if unique_count <= LOW_CARDINALITY_MAX:
                stats["cardinality_level"] = "low"
            elif unique_count <= MEDIUM_CARDINALITY_MAX:
                stats["cardinality_level"] = "medium"
            elif unique_count <= HIGH_CARDINALITY_THRESHOLD:
                stats["cardinality_level"] = "high"
            else:
                stats["cardinality_level"] = "very_high"

            stats["is_high_cardinality"] = unique_count > HIGH_CARDINALITY_THRESHOLD

            if unique_count <= MAX_UNIQUE_VALUES_TO_SHOW:
                value_counts = col_data.value_counts().head(MAX_UNIQUE_VALUES_TO_SHOW)
                stats["top_values"] = [
                    {"value": str(val), "count": int(count)}
                    for val, count in value_counts.items()
                ]

    return stats

def detect_outliers_iqr(df: pd.DataFrame, column: str, multiplier: float = OUTLIER_IQR_MULTIPLIER) -> Tuple[pd.Series, int]:
    """
    Detect outliers using IQR (Interquartile Range) method

    IQR method is more robust than Z-score as it doesn't assume normal distribution
    and is less sensitive to extreme outliers.

    Returns:
        Tuple of (outlier_mask, outlier_count)
    """
    col_data = df[column].dropna()

    if not pd.api.types.is_numeric_dtype(col_data) or len(col_data) <= 3:
        return pd.Series([False] * len(df)), 0

    # Calculate quartiles and IQR
    Q1 = col_data.quantile(0.25)
    Q3 = col_data.quantile(0.75)
    IQR = Q3 - Q1

    # Calculate bounds
    lower_bound = Q1 - multiplier * IQR
    upper_bound = Q3 + multiplier * IQR

    # Identify outliers
    outlier_mask = (col_data < lower_bound) | (col_data > upper_bound)

    return outlier_mask, int(outlier_mask.sum())

def detect_duplicate_rows(df: pd.DataFrame) -> Tuple[int, float]:
    """
    Detect duplicate rows

    Returns:
        Tuple of (duplicate_count, duplicate_percentage)
    """
    duplicate_count = df.duplicated().sum()
    duplicate_percentage = (duplicate_count / len(df)) * 100 if len(df) > 0 else 0

    return int(duplicate_count), float(duplicate_percentage)

def calculate_dataset_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate high-level dataset summary statistics
    """
    duplicate_count, duplicate_percentage = detect_duplicate_rows(df)

    total_cells = df.shape[0] * df.shape[1]
    null_cells = df.isnull().sum().sum()
    completeness = ((total_cells - null_cells) / total_cells * 100) if total_cells > 0 else 0

    return {
        "row_count": int(df.shape[0]),
        "column_count": int(df.shape[1]),
        "duplicate_row_count": duplicate_count,
        "duplicate_row_percentage": duplicate_percentage,
        "overall_completeness": float(completeness),
        "memory_usage_mb": float(df.memory_usage(deep=True).sum() / (1024 * 1024))
    }

def get_sample_rows(df: pd.DataFrame, n: int = 20) -> List[Dict[str, Any]]:
    """
    Get sample rows from dataframe as list of dictionaries
    Handles various data types and converts to JSON-serializable format
    """
    sample_df = df.head(n)

    # Convert to dict and handle non-serializable types
    sample_data = []
    for _, row in sample_df.iterrows():
        row_dict = {}
        for col, val in row.items():
            if pd.isna(val):
                row_dict[col] = None
            elif isinstance(val, (np.integer, np.floating)):
                row_dict[col] = float(val)
            elif isinstance(val, (pd.Timestamp, np.datetime64)):
                row_dict[col] = str(val)
            else:
                row_dict[col] = str(val)
        sample_data.append(row_dict)

    return sample_data
