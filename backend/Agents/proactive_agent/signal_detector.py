"""
Signal detection functions for the proactive agent.

Detects patterns in data:
- Trends (linear regression)
- Outliers (IQR method)
- Dominance (single category percentage)
- Seasonality (autocorrelation)
- Imbalance (Gini coefficient)
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import uuid
from scipy import stats

from .models import Signal, SignalType
from .config import DETECTION_THRESHOLDS


def detect_all_signals(df: pd.DataFrame, table_name: str = "data") -> List[Signal]:
    """
    Detect all signals in the dataset.

    Args:
        df: DataFrame to analyze
        table_name: Name of the table for SQL generation

    Returns:
        List of Signal objects ordered by strength
    """
    signals = []

    # Detect trends (numeric columns with date/time columns)
    signals.extend(detect_trends(df, table_name))

    # Detect outliers (numeric columns)
    signals.extend(detect_outliers(df, table_name))

    # Detect dominance (categorical columns)
    signals.extend(detect_dominance(df, table_name))

    # Detect seasonality (time series)
    signals.extend(detect_seasonality(df, table_name))

    # Detect imbalance (categorical columns)
    signals.extend(detect_imbalance(df, table_name))

    # Sort by strength (highest first)
    signals.sort(key=lambda s: s.strength, reverse=True)

    return signals


def detect_trends(df: pd.DataFrame, table_name: str) -> List[Signal]:
    """
    Detect linear trends in numeric columns over time.

    Uses linear regression to find columns with strong R² values.
    """
    signals = []
    thresholds = DETECTION_THRESHOLDS["trend"]

    # Find date/datetime columns
    date_columns = _find_date_columns(df)
    if not date_columns:
        return signals

    # Find numeric columns
    numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()

    for date_col in date_columns:
        for num_col in numeric_columns:
            if date_col == num_col:
                continue

            # Get non-null pairs
            mask = df[date_col].notna() & df[num_col].notna()
            if mask.sum() < thresholds["min_data_points"]:
                continue

            try:
                # Convert date to numeric (days from first date)
                dates = pd.to_datetime(df.loc[mask, date_col])
                x = (dates - dates.min()).dt.total_seconds() / 86400  # Days
                y = df.loc[mask, num_col].values

                # Perform linear regression
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                r_squared = r_value ** 2

                if r_squared >= thresholds["r_squared_min"]:
                    # Calculate trend direction and percentage
                    start_value = intercept
                    end_value = intercept + slope * x.max()

                    if start_value != 0:
                        change_pct = ((end_value - start_value) / abs(start_value)) * 100
                    else:
                        change_pct = 100 if end_value > 0 else -100

                    direction = "upward" if slope > 0 else "downward"

                    signals.append(Signal(
                        signal_id=str(uuid.uuid4()),
                        signal_type=SignalType.TREND,
                        columns=[date_col, num_col],
                        strength=float(r_squared),
                        metadata={
                            "date_column": date_col,
                            "value_column": num_col,
                            "direction": direction,
                            "slope": float(slope),
                            "r_squared": float(r_squared),
                            "change_percentage": float(change_pct),
                            "p_value": float(p_value),
                            "data_points": int(mask.sum()),
                            "table_name": table_name,
                        }
                    ))
            except Exception as e:
                # Skip columns that fail analysis
                continue

    return signals


def detect_outliers(df: pd.DataFrame, table_name: str) -> List[Signal]:
    """
    Detect outliers using IQR method.

    Reuses the IQR logic from cleaning_agent/detection.py
    """
    signals = []
    thresholds = DETECTION_THRESHOLDS["outlier"]

    numeric_columns = df.select_dtypes(include=[np.number]).columns

    for column in numeric_columns:
        values = df[column].dropna()

        if len(values) < 4:  # Need at least 4 values for IQR
            continue

        Q1 = values.quantile(0.25)
        Q3 = values.quantile(0.75)
        IQR = Q3 - Q1

        if IQR == 0:  # No variation
            continue

        multiplier = thresholds["iqr_multiplier"]
        lower_bound = Q1 - multiplier * IQR
        upper_bound = Q3 + multiplier * IQR

        outlier_mask = (df[column] < lower_bound) | (df[column] > upper_bound)
        outlier_count = outlier_mask.sum()

        if outlier_count < thresholds["min_count"]:
            continue

        outlier_percentage = (outlier_count / len(df)) * 100

        # Get sample outlier values
        outlier_values = df.loc[outlier_mask, column].dropna()
        example_outliers = sorted(outlier_values.unique(), key=lambda x: abs(x - values.median()), reverse=True)[:5]

        # Strength based on how extreme the outliers are
        if len(outlier_values) > 0:
            max_deviation = max(abs(outlier_values.max() - Q3), abs(Q1 - outlier_values.min()))
            strength = min(1.0, max_deviation / (3 * IQR)) if IQR > 0 else 0.5
        else:
            strength = 0.5

        signals.append(Signal(
            signal_id=str(uuid.uuid4()),
            signal_type=SignalType.OUTLIER,
            columns=[column],
            strength=float(strength),
            metadata={
                "column": column,
                "outlier_count": int(outlier_count),
                "outlier_percentage": float(outlier_percentage),
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
                "example_outliers": [float(v) for v in example_outliers],
                "q1": float(Q1),
                "q3": float(Q3),
                "iqr": float(IQR),
                "table_name": table_name,
            }
        ))

    return signals


def detect_dominance(df: pd.DataFrame, table_name: str) -> List[Signal]:
    """
    Detect dominant categories (single category > 50% of total).
    """
    signals = []
    thresholds = DETECTION_THRESHOLDS["dominance"]

    # Find categorical columns (object, category, or low-cardinality)
    categorical_columns = _find_categorical_columns(df)

    for column in categorical_columns:
        value_counts = df[column].value_counts(dropna=True)

        if len(value_counts) < thresholds["min_categories"]:
            continue

        total = value_counts.sum()
        if total == 0:
            continue

        # Check for dominant category
        top_category = value_counts.index[0]
        top_count = value_counts.iloc[0]
        top_percentage = (top_count / total) * 100

        if top_percentage >= thresholds["min_percentage"]:
            # Strength based on how dominant (50% = 0.5, 100% = 1.0)
            strength = top_percentage / 100

            signals.append(Signal(
                signal_id=str(uuid.uuid4()),
                signal_type=SignalType.DOMINANCE,
                columns=[column],
                strength=float(strength),
                metadata={
                    "column": column,
                    "dominant_category": str(top_category),
                    "dominant_count": int(top_count),
                    "dominant_percentage": float(top_percentage),
                    "total_categories": len(value_counts),
                    "total_count": int(total),
                    "distribution": {str(k): int(v) for k, v in value_counts.head(5).items()},
                    "table_name": table_name,
                }
            ))

    return signals


def detect_seasonality(df: pd.DataFrame, table_name: str) -> List[Signal]:
    """
    Detect seasonality using autocorrelation.

    Looks for regular patterns in time series data.
    """
    signals = []
    thresholds = DETECTION_THRESHOLDS["seasonality"]

    date_columns = _find_date_columns(df)
    if not date_columns:
        return signals

    numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()

    for date_col in date_columns:
        for num_col in numeric_columns:
            if date_col == num_col:
                continue

            try:
                # Sort by date and get values
                df_sorted = df[[date_col, num_col]].dropna().sort_values(date_col)
                values = df_sorted[num_col].values

                if len(values) < 10:  # Need enough data for ACF
                    continue

                # Compute autocorrelation for different lags
                acf_values = _compute_acf(values, max_lag=min(len(values) // 2, 50))

                # Find peaks in ACF (excluding lag 0)
                peaks = _find_acf_peaks(acf_values[1:], thresholds["acf_threshold"])

                if len(peaks) >= thresholds["min_periods"]:
                    # Estimate period from first peak
                    period = peaks[0] + 1  # +1 because we excluded lag 0
                    peak_acf = acf_values[period]

                    signals.append(Signal(
                        signal_id=str(uuid.uuid4()),
                        signal_type=SignalType.SEASONALITY,
                        columns=[date_col, num_col],
                        strength=float(abs(peak_acf)),
                        metadata={
                            "date_column": date_col,
                            "value_column": num_col,
                            "estimated_period": int(period),
                            "peak_acf": float(peak_acf),
                            "num_periods_detected": len(peaks),
                            "data_points": len(values),
                            "table_name": table_name,
                        }
                    ))
            except Exception:
                continue

    return signals


def detect_imbalance(df: pd.DataFrame, table_name: str) -> List[Signal]:
    """
    Detect distribution imbalance using Gini coefficient.

    High Gini = unequal distribution (some categories have much more than others)
    """
    signals = []
    thresholds = DETECTION_THRESHOLDS["imbalance"]

    categorical_columns = _find_categorical_columns(df)

    for column in categorical_columns:
        value_counts = df[column].value_counts(dropna=True)

        if len(value_counts) < thresholds["min_categories"]:
            continue

        # Calculate Gini coefficient
        gini = _calculate_gini(value_counts.values)

        if gini >= thresholds["gini_threshold"]:
            signals.append(Signal(
                signal_id=str(uuid.uuid4()),
                signal_type=SignalType.IMBALANCE,
                columns=[column],
                strength=float(gini),
                metadata={
                    "column": column,
                    "gini_coefficient": float(gini),
                    "num_categories": len(value_counts),
                    "max_count": int(value_counts.max()),
                    "min_count": int(value_counts.min()),
                    "mean_count": float(value_counts.mean()),
                    "distribution": {str(k): int(v) for k, v in value_counts.head(10).items()},
                    "table_name": table_name,
                }
            ))

    return signals


# ============================================================================
# Helper Functions
# ============================================================================

def _find_date_columns(df: pd.DataFrame) -> List[str]:
    """Find columns that contain date/datetime values."""
    date_columns = []

    # Check datetime dtypes
    for col in df.select_dtypes(include=['datetime64']).columns:
        date_columns.append(col)

    # Check object columns that might be dates
    for col in df.select_dtypes(include=['object']).columns:
        if col in date_columns:
            continue

        sample = df[col].dropna().head(100)
        if len(sample) == 0:
            continue

        try:
            pd.to_datetime(sample, errors='raise')
            date_columns.append(col)
        except:
            continue

    return date_columns


def _find_categorical_columns(df: pd.DataFrame, max_cardinality: int = 50) -> List[str]:
    """Find columns that are categorical (object, category, or low-cardinality numeric)."""
    categorical = []

    # Object and category columns
    for col in df.select_dtypes(include=['object', 'category']).columns:
        n_unique = df[col].nunique()
        if n_unique <= max_cardinality and n_unique >= 2:
            categorical.append(col)

    # Low-cardinality integer columns (could be encoded categories)
    for col in df.select_dtypes(include=['int64', 'int32']).columns:
        n_unique = df[col].nunique()
        if 2 <= n_unique <= 20:  # Likely categorical
            categorical.append(col)

    return categorical


def _compute_acf(values: np.ndarray, max_lag: int) -> np.ndarray:
    """Compute autocorrelation function for given lags."""
    n = len(values)
    mean = np.mean(values)
    var = np.var(values)

    if var == 0:
        return np.zeros(max_lag + 1)

    acf = np.zeros(max_lag + 1)
    acf[0] = 1.0  # Lag 0 is always 1

    for lag in range(1, max_lag + 1):
        cov = np.sum((values[:n-lag] - mean) * (values[lag:] - mean)) / n
        acf[lag] = cov / var

    return acf


def _find_acf_peaks(acf: np.ndarray, threshold: float) -> List[int]:
    """Find significant peaks in ACF values."""
    peaks = []

    for i in range(1, len(acf) - 1):
        # Check if it's a local maximum above threshold
        if acf[i] > threshold and acf[i] > acf[i-1] and acf[i] > acf[i+1]:
            peaks.append(i)

    return peaks


def _calculate_gini(values: np.ndarray) -> float:
    """
    Calculate Gini coefficient for a distribution.

    0 = perfect equality, 1 = perfect inequality
    """
    values = np.array(values, dtype=float)
    values = values[values > 0]  # Remove zeros

    if len(values) == 0:
        return 0.0

    # Sort values
    values = np.sort(values)
    n = len(values)

    # Calculate Gini using the formula
    index = np.arange(1, n + 1)
    gini = (2 * np.sum(index * values) - (n + 1) * np.sum(values)) / (n * np.sum(values))

    return max(0.0, min(1.0, gini))
