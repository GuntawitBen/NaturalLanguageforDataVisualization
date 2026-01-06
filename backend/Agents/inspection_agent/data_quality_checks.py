"""
Data Quality Check Functions
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any
from scipy import stats
from sklearn.ensemble import IsolationForest

from .config import (
    OUTLIER_IQR_MULTIPLIER,
    OUTLIER_ZSCORE_THRESHOLD,
    OUTLIER_ISOLATION_CONTAMINATION,
    OUTLIER_MIN_SAMPLES,
    DUPLICATE_COLUMN_SIMILARITY_THRESHOLD,
    NULL_REPRESENTATIONS,
    MIXED_TYPE_THRESHOLD,
    LOW_CARDINALITY_MAX,
    MEDIUM_CARDINALITY_MAX,
    HIGH_CARDINALITY_THRESHOLD,
    SKEWNESS_THRESHOLD,
    KURTOSIS_THRESHOLD
)

# ============================================================================
# MISSING VALUES DETECTION
# ============================================================================

def detect_missing_values(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """
    Detect missing values in a column

    Returns:
        Dict with null_count, null_percentage, and pattern info
    """
    null_count = df[column].isna().sum()
    null_percentage = (null_count / len(df)) * 100 if len(df) > 0 else 0

    # Check for null-like string representations
    if df[column].dtype == 'object':
        null_like_mask = df[column].isin(NULL_REPRESENTATIONS)
        null_like_count = null_like_mask.sum()
        total_null_count = null_count + null_like_count
        total_null_percentage = (total_null_count / len(df)) * 100 if len(df) > 0 else 0
    else:
        null_like_count = 0
        total_null_count = null_count
        total_null_percentage = null_percentage

    return {
        'null_count': int(null_count),
        'null_percentage': float(null_percentage),
        'null_like_count': int(null_like_count),
        'total_null_count': int(total_null_count),
        'total_null_percentage': float(total_null_percentage)
    }

# ============================================================================
# DUPLICATE DETECTION
# ============================================================================

def detect_duplicate_rows(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Detect duplicate rows in the dataset

    Returns:
        Dict with duplicate_count and duplicate_percentage
    """
    duplicate_count = df.duplicated().sum()
    duplicate_percentage = (duplicate_count / len(df)) * 100 if len(df) > 0 else 0

    return {
        'duplicate_count': int(duplicate_count),
        'duplicate_percentage': float(duplicate_percentage)
    }

def detect_duplicate_columns(df: pd.DataFrame) -> List[Tuple[str, str]]:
    """
    Detect duplicate columns (columns with identical values)

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
# OUTLIER DETECTION
# ============================================================================

def detect_outliers_iqr(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """
    Detect outliers using IQR method

    Returns:
        Dict with outlier information
    """
    values = df[column].dropna()

    if len(values) < 4:  # Need at least 4 values for IQR
        return {
            'has_outliers': False,
            'outlier_count': 0,
            'outlier_indices': [],
            'lower_bound': None,
            'upper_bound': None
        }

    Q1 = values.quantile(0.25)
    Q3 = values.quantile(0.75)
    IQR = Q3 - Q1

    lower_bound = Q1 - OUTLIER_IQR_MULTIPLIER * IQR
    upper_bound = Q3 + OUTLIER_IQR_MULTIPLIER * IQR

    outlier_mask = (df[column] < lower_bound) | (df[column] > upper_bound)
    outlier_indices = df[outlier_mask].index.tolist()
    outlier_count = len(outlier_indices)

    return {
        'has_outliers': outlier_count > 0,
        'outlier_count': int(outlier_count),
        'outlier_indices': outlier_indices[:100],  # Limit to first 100
        'lower_bound': float(lower_bound),
        'upper_bound': float(upper_bound),
        'method': 'iqr'
    }

def detect_outliers_zscore(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """
    Detect outliers using Z-score method

    Returns:
        Dict with outlier information
    """
    values = df[column].dropna()

    if len(values) < 3:  # Need at least 3 values
        return {
            'has_outliers': False,
            'outlier_count': 0,
            'outlier_indices': [],
            'threshold': OUTLIER_ZSCORE_THRESHOLD
        }

    z_scores = np.abs(stats.zscore(values))
    outlier_mask = z_scores > OUTLIER_ZSCORE_THRESHOLD

    # Map back to original dataframe indices
    outlier_indices = values[outlier_mask].index.tolist()
    outlier_count = len(outlier_indices)

    return {
        'has_outliers': outlier_count > 0,
        'outlier_count': int(outlier_count),
        'outlier_indices': outlier_indices[:100],  # Limit to first 100
        'threshold': float(OUTLIER_ZSCORE_THRESHOLD),
        'method': 'zscore'
    }

def detect_outliers_isolation_forest(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """
    Detect outliers using Isolation Forest

    Returns:
        Dict with outlier information
    """
    values = df[column].dropna()

    if len(values) < OUTLIER_MIN_SAMPLES:
        return {
            'has_outliers': False,
            'outlier_count': 0,
            'outlier_indices': [],
            'note': f'Insufficient samples (need at least {OUTLIER_MIN_SAMPLES})'
        }

    try:
        # Reshape for sklearn
        X = values.values.reshape(-1, 1)

        # Fit Isolation Forest
        iso_forest = IsolationForest(
            contamination=OUTLIER_ISOLATION_CONTAMINATION,
            random_state=42
        )
        predictions = iso_forest.fit_predict(X)

        # -1 indicates outliers
        outlier_mask = predictions == -1
        outlier_indices = values[outlier_mask].index.tolist()
        outlier_count = len(outlier_indices)

        return {
            'has_outliers': outlier_count > 0,
            'outlier_count': int(outlier_count),
            'outlier_indices': outlier_indices[:100],  # Limit to first 100
            'contamination': float(OUTLIER_ISOLATION_CONTAMINATION),
            'method': 'isolation_forest'
        }
    except Exception as e:
        return {
            'has_outliers': False,
            'outlier_count': 0,
            'outlier_indices': [],
            'error': str(e)
        }

# ============================================================================
# DATA TYPE DETECTION
# ============================================================================

def detect_mixed_data_types(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """
    Detect mixed data types in a column

    Returns:
        Dict with type distribution information
    """
    if df[column].dtype != 'object':
        # Non-object columns are already typed
        return {
            'has_mixed_types': False,
            'type_distribution': {}
        }

    # Analyze actual types of non-null values
    non_null_values = df[column].dropna()

    if len(non_null_values) == 0:
        return {
            'has_mixed_types': False,
            'type_distribution': {}
        }

    type_counts = {}
    for value in non_null_values:
        value_type = type(value).__name__
        type_counts[value_type] = type_counts.get(value_type, 0) + 1

    # Check if values can be interpreted as numbers
    numeric_count = 0
    for value in non_null_values:
        try:
            float(value)
            numeric_count += 1
        except (ValueError, TypeError):
            pass

    if numeric_count > 0:
        type_counts['numeric_string'] = numeric_count

    # Determine if mixed
    has_mixed_types = len(type_counts) > 1

    # Calculate percentages
    total = len(non_null_values)
    type_distribution = {
        type_name: {
            'count': count,
            'percentage': (count / total) * 100
        }
        for type_name, count in type_counts.items()
    }

    return {
        'has_mixed_types': has_mixed_types,
        'type_distribution': type_distribution,
        'total_types': len(type_counts)
    }

def detect_invalid_values(df: pd.DataFrame, column: str, expected_type: str = None) -> Dict[str, Any]:
    """
    Detect invalid values based on expected data type

    Returns:
        Dict with invalid value information
    """
    invalid_indices = []
    invalid_values = []

    # If column should be numeric but contains non-numeric strings
    if expected_type == 'numeric' or pd.api.types.is_numeric_dtype(df[column]):
        if df[column].dtype == 'object':
            for idx, value in df[column].items():
                if pd.notna(value):
                    try:
                        float(value)
                    except (ValueError, TypeError):
                        invalid_indices.append(idx)
                        invalid_values.append(str(value))

    return {
        'has_invalid_values': len(invalid_indices) > 0,
        'invalid_count': len(invalid_indices),
        'invalid_indices': invalid_indices[:100],  # Limit to first 100
        'invalid_samples': invalid_values[:10]  # Show first 10 examples
    }

# ============================================================================
# CARDINALITY DETECTION
# ============================================================================

def analyze_cardinality(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """
    Analyze cardinality of a column

    Returns:
        Dict with cardinality information
    """
    unique_count = df[column].nunique()
    total_count = len(df)
    cardinality_ratio = unique_count / total_count if total_count > 0 else 0

    # Determine cardinality level
    if unique_count <= LOW_CARDINALITY_MAX:
        cardinality_level = "low"
        is_high_cardinality = False
    elif unique_count <= MEDIUM_CARDINALITY_MAX:
        cardinality_level = "medium"
        is_high_cardinality = False
    elif unique_count <= HIGH_CARDINALITY_THRESHOLD:
        cardinality_level = "high"
        is_high_cardinality = True
    else:
        cardinality_level = "very_high"
        is_high_cardinality = True

    return {
        'unique_count': int(unique_count),
        'cardinality_ratio': float(cardinality_ratio),
        'cardinality_level': cardinality_level,
        'is_high_cardinality': is_high_cardinality
    }

# ============================================================================
# STATISTICAL ANALYSIS
# ============================================================================

def analyze_distribution(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """
    Analyze distribution characteristics of numeric column

    Returns:
        Dict with distribution statistics
    """
    values = df[column].dropna()

    if len(values) < 3:
        return {
            'skewness': None,
            'kurtosis': None,
            'is_skewed': False,
            'is_heavy_tailed': False
        }

    try:
        skewness = float(values.skew())
        kurtosis = float(values.kurtosis())

        is_skewed = abs(skewness) > SKEWNESS_THRESHOLD
        is_heavy_tailed = kurtosis > KURTOSIS_THRESHOLD

        return {
            'skewness': skewness,
            'kurtosis': kurtosis,
            'is_skewed': is_skewed,
            'is_heavy_tailed': is_heavy_tailed
        }
    except Exception as e:
        return {
            'skewness': None,
            'kurtosis': None,
            'is_skewed': False,
            'is_heavy_tailed': False,
            'error': str(e)
        }
