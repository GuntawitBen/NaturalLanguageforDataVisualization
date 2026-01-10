"""
DataFrame cleaning operations.
"""

import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Any

from .config import DETECTION_THRESHOLDS


class CleaningOperations:
    """Static methods for cleaning operations"""

    @staticmethod
    def drop_columns(df: pd.DataFrame, columns: List[str]) -> Tuple[pd.DataFrame, str]:
        """
        Drop columns entirely (useful when they have too many missing values).

        Args:
            df: DataFrame to clean
            columns: List of columns to drop

        Returns:
            Tuple of (cleaned DataFrame, description message)
        """
        df_cleaned = df.drop(columns=columns, errors='ignore')
        dropped_count = len(columns)

        message = f"Dropped {dropped_count} column(s) with excessive missing values: {', '.join(columns)}"
        return df_cleaned, message

    @staticmethod
    def drop_missing_rows(df: pd.DataFrame, columns: List[str]) -> Tuple[pd.DataFrame, str]:
        """
        Drop rows with missing values in specified columns.

        Args:
            df: DataFrame to clean
            columns: List of columns to check for missing values

        Returns:
            Tuple of (cleaned DataFrame, description message)
        """
        initial_rows = len(df)
        df_cleaned = df.dropna(subset=columns)
        rows_dropped = initial_rows - len(df_cleaned)

        message = f"Dropped {rows_dropped} rows with missing values in {', '.join(columns)}"
        return df_cleaned, message

    @staticmethod
    def fill_with_mean(df: pd.DataFrame, columns: List[str]) -> Tuple[pd.DataFrame, str]:
        """
        Fill missing values with mean for numeric columns.

        Args:
            df: DataFrame to clean
            columns: List of numeric columns to fill

        Returns:
            Tuple of (cleaned DataFrame, description message)
        """
        df_cleaned = df.copy()
        filled_counts = []

        for column in columns:
            if pd.api.types.is_numeric_dtype(df_cleaned[column]):
                null_count = df_cleaned[column].isna().sum()
                mean_value = df_cleaned[column].mean()
                df_cleaned[column].fillna(mean_value, inplace=True)
                filled_counts.append(f"{column} ({null_count} values)")

        message = f"Filled missing values with mean in {', '.join(filled_counts)}"
        return df_cleaned, message

    @staticmethod
    def fill_with_median(df: pd.DataFrame, columns: List[str]) -> Tuple[pd.DataFrame, str]:
        """
        Fill missing values with median for numeric columns.

        Args:
            df: DataFrame to clean
            columns: List of numeric columns to fill

        Returns:
            Tuple of (cleaned DataFrame, description message)
        """
        df_cleaned = df.copy()
        filled_counts = []

        for column in columns:
            if pd.api.types.is_numeric_dtype(df_cleaned[column]):
                null_count = df_cleaned[column].isna().sum()
                median_value = df_cleaned[column].median()
                df_cleaned[column].fillna(median_value, inplace=True)
                filled_counts.append(f"{column} ({null_count} values)")

        message = f"Filled missing values with median in {', '.join(filled_counts)}"
        return df_cleaned, message

    @staticmethod
    def fill_with_mode(df: pd.DataFrame, columns: List[str]) -> Tuple[pd.DataFrame, str]:
        """
        Fill missing values with mode (most frequent value).

        Args:
            df: DataFrame to clean
            columns: List of columns to fill

        Returns:
            Tuple of (cleaned DataFrame, description message)
        """
        df_cleaned = df.copy()
        filled_counts = []

        for column in columns:
            null_count = df_cleaned[column].isna().sum()
            mode_values = df_cleaned[column].mode()

            if len(mode_values) > 0:
                mode_value = mode_values[0]
                df_cleaned[column].fillna(mode_value, inplace=True)
                filled_counts.append(f"{column} ({null_count} values)")

        message = f"Filled missing values with mode in {', '.join(filled_counts)}"
        return df_cleaned, message

    @staticmethod
    def remove_outliers(df: pd.DataFrame, columns: List[str], method: str = "iqr") -> Tuple[pd.DataFrame, str]:
        """
        Remove rows containing outliers using IQR method.

        Args:
            df: DataFrame to clean
            columns: List of numeric columns to check for outliers
            method: Outlier detection method (currently only "iqr" supported)

        Returns:
            Tuple of (cleaned DataFrame, description message)
        """
        df_cleaned = df.copy()
        initial_rows = len(df_cleaned)
        iqr_multiplier = DETECTION_THRESHOLDS["outliers"]["iqr_multiplier"]

        outlier_mask = pd.Series([False] * len(df_cleaned))

        for column in columns:
            if pd.api.types.is_numeric_dtype(df_cleaned[column]):
                values = df_cleaned[column].dropna()

                if len(values) >= 4:
                    Q1 = values.quantile(0.25)
                    Q3 = values.quantile(0.75)
                    IQR = Q3 - Q1

                    lower_bound = Q1 - iqr_multiplier * IQR
                    upper_bound = Q3 + iqr_multiplier * IQR

                    # Mark rows with outliers
                    outlier_mask |= (df_cleaned[column] < lower_bound) | (df_cleaned[column] > upper_bound)

        # Remove rows with outliers
        df_cleaned = df_cleaned[~outlier_mask]
        rows_removed = initial_rows - len(df_cleaned)

        message = f"Removed {rows_removed} rows containing outliers in {', '.join(columns)} using IQR method"
        return df_cleaned, message

    @staticmethod
    def cap_outliers(df: pd.DataFrame, columns: List[str], method: str = "iqr") -> Tuple[pd.DataFrame, str]:
        """
        Cap outliers at boundary values using IQR method.

        Args:
            df: DataFrame to clean
            columns: List of numeric columns to cap outliers
            method: Outlier detection method (currently only "iqr" supported)

        Returns:
            Tuple of (cleaned DataFrame, description message)
        """
        df_cleaned = df.copy()
        iqr_multiplier = DETECTION_THRESHOLDS["outliers"]["iqr_multiplier"]
        total_capped = 0

        for column in columns:
            if pd.api.types.is_numeric_dtype(df_cleaned[column]):
                values = df_cleaned[column].dropna()

                if len(values) >= 4:
                    Q1 = values.quantile(0.25)
                    Q3 = values.quantile(0.75)
                    IQR = Q3 - Q1

                    lower_bound = Q1 - iqr_multiplier * IQR
                    upper_bound = Q3 + iqr_multiplier * IQR

                    # Cap values at boundaries
                    lower_outliers = df_cleaned[column] < lower_bound
                    upper_outliers = df_cleaned[column] > upper_bound

                    total_capped += lower_outliers.sum() + upper_outliers.sum()

                    df_cleaned.loc[lower_outliers, column] = lower_bound
                    df_cleaned.loc[upper_outliers, column] = upper_bound

        message = f"Capped {total_capped} outlier values at IQR boundaries in {', '.join(columns)}"
        return df_cleaned, message

    @staticmethod
    def drop_duplicate_rows(df: pd.DataFrame, keep: str = "first") -> Tuple[pd.DataFrame, str]:
        """
        Remove duplicate rows.

        Args:
            df: DataFrame to clean
            keep: Which duplicates to keep ('first', 'last', or False to remove all)

        Returns:
            Tuple of (cleaned DataFrame, description message)
        """
        initial_rows = len(df)
        df_cleaned = df.drop_duplicates(keep=keep)
        rows_removed = initial_rows - len(df_cleaned)

        message = f"Removed {rows_removed} duplicate rows (kept {keep} occurrence)"
        return df_cleaned, message

    @staticmethod
    def drop_duplicate_columns(df: pd.DataFrame, columns: List[str]) -> Tuple[pd.DataFrame, str]:
        """
        Remove duplicate columns.

        Args:
            df: DataFrame to clean
            columns: List of column names to remove

        Returns:
            Tuple of (cleaned DataFrame, description message)
        """
        df_cleaned = df.drop(columns=columns, errors='ignore')
        removed_count = len(columns)

        message = f"Removed {removed_count} duplicate columns: {', '.join(columns)}"
        return df_cleaned, message

    @staticmethod
    def no_operation(df: pd.DataFrame, **kwargs) -> Tuple[pd.DataFrame, str]:
        """
        No-op operation (keep data as-is).

        Args:
            df: DataFrame (unchanged)

        Returns:
            Tuple of (unchanged DataFrame, description message)
        """
        message = "No operation performed - data kept as-is"
        return df.copy(), message


# Operation registry mapping function names to actual functions
OPERATION_REGISTRY = {
    "drop_columns": CleaningOperations.drop_columns,
    "drop_missing_rows": CleaningOperations.drop_missing_rows,
    "fill_with_mean": CleaningOperations.fill_with_mean,
    "fill_with_median": CleaningOperations.fill_with_median,
    "fill_with_mode": CleaningOperations.fill_with_mode,
    "remove_outliers": CleaningOperations.remove_outliers,
    "cap_outliers": CleaningOperations.cap_outliers,
    "drop_duplicate_rows": CleaningOperations.drop_duplicate_rows,
    "drop_duplicate_columns": CleaningOperations.drop_duplicate_columns,
    "no_operation": CleaningOperations.no_operation,
}


def execute_operation(operation_type: str, df: pd.DataFrame, parameters: Dict[str, Any]) -> Tuple[pd.DataFrame, str]:
    """
    Execute a cleaning operation by name.

    Args:
        operation_type: Name of the operation (e.g., "drop_missing_rows")
        df: DataFrame to clean
        parameters: Parameters for the operation

    Returns:
        Tuple of (cleaned DataFrame, description message)

    Raises:
        ValueError: If operation_type is not recognized
    """
    if operation_type not in OPERATION_REGISTRY:
        raise ValueError(f"Unknown operation type: {operation_type}")

    operation_func = OPERATION_REGISTRY[operation_type]
    return operation_func(df, **parameters)
