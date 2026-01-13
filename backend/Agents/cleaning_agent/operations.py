"""
DataFrame cleaning operations.
"""

import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Any
from dateutil import parser as date_parser

from .config import DETECTION_THRESHOLDS, DATE_FORMAT_OPTIONS, BOOLEAN_FORMAT_OPTIONS


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

    # ========================================================================
    # Format Standardization Operations
    # ========================================================================

    @staticmethod
    def standardize_date_format(
        df: pd.DataFrame,
        columns: List[str],
        target_format: str
    ) -> Tuple[pd.DataFrame, str]:
        """
        Standardize date formats in specified columns.

        Args:
            df: DataFrame to clean
            columns: List of columns containing dates
            target_format: Target format key (e.g., "YYYY-MM-DD")

        Returns:
            Tuple of (cleaned DataFrame, description message)
        """
        df_cleaned = df.copy()

        # Get the strftime format string
        format_info = DATE_FORMAT_OPTIONS.get(target_format, {})
        strftime_format = format_info.get("strftime", "%Y-%m-%d")

        converted_count = 0
        failed_count = 0

        for column in columns:
            if column not in df_cleaned.columns:
                continue

            def convert_date(val):
                nonlocal converted_count, failed_count
                if pd.isna(val):
                    return val
                try:
                    val_str = str(val)
                    
                    # Smart parsing: Check if month > 12, then swap day/month
                    # Pattern: YYYY-MM-DD or YYYY/MM/DD where MM > 12
                    import re
                    match = re.match(r'^(\d{4})[-/](\d{2})[-/](\d{2})$', val_str)
                    if match:
                        year, first_num, second_num = match.groups()
                        first_int = int(first_num)
                        second_int = int(second_num)
                        
                        # If first number > 12, it's likely day-month instead of month-day
                        if first_int > 12 and second_int <= 12:
                            # Swap: assume it's DD-MM-YYYY format
                            val_str = f"{year}-{second_num}-{first_num}"
                    
                    # Try to parse the date string
                    parsed = date_parser.parse(val_str, fuzzy=True)
                    converted_count += 1
                    return parsed.strftime(strftime_format)
                except (ValueError, TypeError):
                    failed_count += 1
                    return val  # Keep original if parsing fails

            df_cleaned[column] = df_cleaned[column].apply(convert_date)

        message = f"Converted {converted_count} dates to {target_format} format in {', '.join(columns)}"
        if failed_count > 0:
            message += f" ({failed_count} values could not be parsed)"

        return df_cleaned, message

    @staticmethod
    def standardize_boolean_format(
        df: pd.DataFrame,
        columns: List[str],
        target_format: str
    ) -> Tuple[pd.DataFrame, str]:
        """
        Standardize boolean formats in specified columns.

        Args:
            df: DataFrame to clean
            columns: List of columns containing boolean values
            target_format: Target format key (e.g., "Yes/No", "True/False")

        Returns:
            Tuple of (cleaned DataFrame, description message)
        """
        df_cleaned = df.copy()

        # Get the target true/false values
        format_info = BOOLEAN_FORMAT_OPTIONS.get(target_format, {})
        true_value = format_info.get("true_value", "True")
        false_value = format_info.get("false_value", "False")

        # Define all known boolean representations
        true_values = {"yes", "y", "true", "t", "1", "on"}
        false_values = {"no", "n", "false", "f", "0", "off"}

        converted_count = 0

        for column in columns:
            if column not in df_cleaned.columns:
                continue

            def convert_boolean(val):
                nonlocal converted_count
                if pd.isna(val):
                    return val
                val_lower = str(val).strip().lower()
                if val_lower in true_values:
                    converted_count += 1
                    return true_value
                elif val_lower in false_values:
                    converted_count += 1
                    return false_value
                return val  # Keep original if not recognized

            df_cleaned[column] = df_cleaned[column].apply(convert_boolean)

        message = f"Converted {converted_count} boolean values to {target_format} format in {', '.join(columns)}"
        return df_cleaned, message

    @staticmethod
    def standardize_case(
        df: pd.DataFrame,
        columns: List[str],
        target_case: str
    ) -> Tuple[pd.DataFrame, str]:
        """
        Standardize text case in specified columns.

        Args:
            df: DataFrame to clean
            columns: List of columns containing text
            target_case: Target case style ("Title Case", "UPPERCASE", "lowercase", "Sentence case")

        Returns:
            Tuple of (cleaned DataFrame, description message)
        """
        df_cleaned = df.copy()
        converted_count = 0

        for column in columns:
            if column not in df_cleaned.columns:
                continue

            def convert_case(val):
                nonlocal converted_count
                if pd.isna(val):
                    return val

                val_str = str(val).strip()
                if not val_str:
                    return val

                converted_count += 1

                if target_case == "Title Case":
                    return val_str.title()
                elif target_case == "UPPERCASE":
                    return val_str.upper()
                elif target_case == "lowercase":
                    return val_str.lower()
                elif target_case == "Sentence case":
                    return val_str.capitalize()
                else:
                    return val_str

            df_cleaned[column] = df_cleaned[column].apply(convert_case)

        message = f"Converted {converted_count} values to {target_case} in {', '.join(columns)}"
        message = f"Converted {converted_count} values to {target_case} in {', '.join(columns)}"
        return df_cleaned, message


    @staticmethod
    def convert_mixed_to_numeric(
        df: pd.DataFrame,
        columns: List[str]
    ) -> Tuple[pd.DataFrame, str]:
        """
        Convert mixed data type columns to numeric.
        Text values that cannot be converted are set to NaN (missing).

        Args:
            df: DataFrame to clean
            columns: List of columns to convert

        Returns:
            Tuple of (cleaned DataFrame, description message)
        """
        df_cleaned = df.copy()
        converted_count = 0
        failed_count = 0

        for column in columns:
            if column not in df_cleaned.columns:
                continue

            # Check original missing values to distinguish from new ones
            original_nulls = df_cleaned[column].isna().sum()

            def convert_val(val):
                if pd.isna(val):
                    return val
                
                # Optimized for speed: try float conversion first
                try:
                    return float(val)
                except (ValueError, TypeError):
                    pass
                
                # If parsed as string, try to convert text number
                val_str = str(val).lower().strip()
                
                # Simple dictionary for common number words
                # This covers the requested "Thirty" case and other common ones
                text_numbers = {
                    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 
                    'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
                    'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13, 
                    'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 
                    'seventeen': 17, 'eighteen': 18, 'nineteen': 19,
                    'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50,
                    'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90,
                    'hundred': 100, 'thousand': 1000
                }
                
                if val_str in text_numbers:
                    return float(text_numbers[val_str])
                
                # Handle compound numbers simple case (e.g. "twenty five")
                parts = val_str.replace('-', ' ').split()
                if len(parts) == 2:
                    if parts[0] in text_numbers and parts[1] in text_numbers:
                        # e.g. "twenty" (20) + "five" (5) = 25
                        # Only sum if first is >= 20 (simple logic)
                        v1 = text_numbers[parts[0]]
                        v2 = text_numbers[parts[1]]
                        if v1 >= 20: 
                            return float(v1 + v2)
                
                return np.nan

            # Apply conversion with smart text parsing
            df_cleaned[column] = df_cleaned[column].apply(convert_val)

            # Count how many non-null values became null (failed conversions)
            new_nulls = df_cleaned[column].isna().sum()
            failed_in_col = new_nulls - original_nulls
            failed_count += failed_in_col

            # Count successful conversions (approximate: total - failed - original nulls)
            converted_in_col = len(df) - new_nulls
            converted_count += converted_in_col

        message = f"Converted columns {', '.join(columns)} to numeric."
        if failed_count > 0:
            message += f" {failed_count} text values were set to missing (NaN)."

        return df_cleaned, message


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
    # Format standardization operations
    "standardize_date_format": CleaningOperations.standardize_date_format,
    "standardize_boolean_format": CleaningOperations.standardize_boolean_format,
    "standardize_boolean_format": CleaningOperations.standardize_boolean_format,
    "standardize_case": CleaningOperations.standardize_case,
    "convert_mixed_to_numeric": CleaningOperations.convert_mixed_to_numeric,
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
