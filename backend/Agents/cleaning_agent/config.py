"""
Configuration and templates for cleaning operations.
"""

# Thresholds for problem detection
DETECTION_THRESHOLDS = {
    "missing_values": {
        "min_percentage": 1.0,  # Minimum 1% missing to report as problem
        "critical_percentage": 50.0,  # >50% missing is critical
        "warning_percentage": 20.0,  # 20-50% is warning
    },
    "outliers": {
        "iqr_multiplier": 1.5,  # Standard IQR multiplier
        "min_count": 1,  # Minimum outliers to report
        "critical_percentage": 10.0,  # >10% outliers is critical
    },
    "duplicates": {
        "min_count": 1,  # Minimum duplicates to report
        "critical_percentage": 20.0,  # >20% duplicates is critical
    }
}

# Predefined cleaning operations
CLEANING_OPERATIONS = {
    "missing_values": {
        "drop_column": {
            "name": "Drop the entire column",
            "function": "drop_columns",
            "parameters": {"columns": []},
            "description": "Remove the entire column from the dataset (recommended when most values are missing)",
            "min_missing_percentage": 50.0  # Only offer this when >50% missing
        },
        "drop_rows": {
            "name": "Drop rows with missing values",
            "function": "drop_missing_rows",
            "parameters": {"columns": []},
            "description": "Remove all rows that contain missing values in the affected columns"
        },
        "fill_mean": {
            "name": "Fill with mean value",
            "function": "fill_with_mean",
            "parameters": {"columns": []},
            "description": "Replace missing values with the mean of the column (numeric only)"
        },
        "fill_median": {
            "name": "Fill with median value",
            "function": "fill_with_median",
            "parameters": {"columns": []},
            "description": "Replace missing values with the median of the column (numeric only)"
        },
        "fill_mode": {
            "name": "Fill with most frequent value",
            "function": "fill_with_mode",
            "parameters": {"columns": []},
            "description": "Replace missing values with the most common value in the column"
        },
        "keep_missing": {
            "name": "Leave as-is",
            "function": "no_operation",
            "parameters": {},
            "description": "Keep missing values unchanged - useful when missing data is meaningful"
        }
    },
    "outliers": {
        "remove_outliers": {
            "name": "Remove outlier rows",
            "function": "remove_outliers",
            "parameters": {"columns": [], "method": "iqr"},
            "description": "Remove all rows that contain outliers in the affected columns using IQR method"
        },
        "cap_outliers": {
            "name": "Cap outliers at boundaries",
            "function": "cap_outliers",
            "parameters": {"columns": [], "method": "iqr"},
            "description": "Replace outliers with the nearest boundary value (Q1-1.5*IQR or Q3+1.5*IQR)"
        },
        "keep_outliers": {
            "name": "Keep outliers (no action)",
            "function": "no_operation",
            "parameters": {},
            "description": "Preserve the data as-is without removing outliers"
        }
    },
    "duplicates_rows": {
        "drop_duplicates_first": {
            "name": "Remove duplicate rows (keep first)",
            "function": "drop_duplicate_rows",
            "parameters": {"keep": "first"},
            "description": "Remove duplicate rows, keeping the first occurrence"
        }
    },
    "duplicates_columns": {
        "drop_duplicate_columns": {
            "name": "Remove duplicate columns",
            "function": "drop_duplicate_columns",
            "parameters": {"columns": []},
            "description": "Remove columns that have identical values to other columns"
        }
    }
}

# Session configuration
SESSION_CONFIG = {
    "max_backups": 10,  # Maximum number of backups to keep per session
    "session_timeout": 1800,  # Session timeout in seconds (30 minutes)
    "backup_cleanup_interval": 3600,  # Cleanup interval in seconds (1 hour)
}

# Visualization impact templates
VISUALIZATION_IMPACT_TEMPLATES = {
    "missing_values": {
        "critical": "This high level of missing data ({percentage}%) will create significant gaps in visualizations, making patterns unreliable and potentially misleading.",
        "warning": "Missing values ({percentage}%) will create noticeable gaps in charts and may affect statistical summaries and trend lines.",
        "info": "A small amount of missing data ({percentage}%) may cause minor gaps in visualizations but shouldn't significantly affect overall patterns."
    },
    "outliers": {
        "critical": "Many outliers ({count} values, {percentage}%) will severely skew scale and distribution in charts, making it difficult to see meaningful patterns.",
        "warning": "Outliers ({count} values, {percentage}%) may distort the scale of visualizations and affect statistical measures like mean and standard deviation.",
        "info": "Few outliers ({count} values) may extend the range of charts but shouldn't significantly affect overall patterns."
    },
    "duplicates_rows": {
        "critical": "Many duplicate rows ({count}, {percentage}%) will inflate counts and frequencies in visualizations, leading to misleading conclusions.",
        "warning": "Duplicate rows ({count}, {percentage}%) will inflate aggregated metrics and frequency counts in visualizations.",
        "info": "Few duplicate rows ({count}) may slightly inflate counts but shouldn't significantly affect analysis."
    },
    "duplicates_columns": {
        "warning": "Duplicate columns ({count}) will create redundant information in visualizations and may confuse interpretation.",
        "info": "Duplicate columns ({count}) detected - these create redundancy but don't directly affect visualization accuracy."
    }
}

# Default pros/cons fallbacks (used if GPT-4 fails)
DEFAULT_PROS_CONS = {
    "drop_columns": {
        "pros": "Removes columns with excessive missing data that provide little value. Preserves all rows and prevents introducing mostly artificial data. Reduces dataset complexity.",
        "cons": "Permanently loses any information that column might have contained. Cannot recover the column later if needed."
    },
    "drop_rows": {
        "pros": "Ensures completely clean data with no missing values. Simple and straightforward approach.",
        "cons": "May lose significant amount of data, potentially introducing sampling bias if missing data is not random."
    },
    "fill_mean": {
        "pros": "Preserves all rows. Mean is appropriate for normally distributed data and won't drastically change the distribution.",
        "cons": "Introduces artificial values. Can be affected by outliers. Not suitable for categorical data."
    },
    "fill_median": {
        "pros": "Preserves all rows. Robust to outliers. Better than mean for skewed distributions.",
        "cons": "Introduces artificial values. May not preserve the exact distribution shape."
    },
    "fill_mode": {
        "pros": "Preserves all rows. Works for both numeric and categorical data. Uses actual values from the dataset.",
        "cons": "May over-represent the most common value. Not suitable for continuous data with no repeated values."
    },
    "remove_outliers": {
        "pros": "Removes extreme values that may distort analysis. Creates cleaner visualizations with better scale.",
        "cons": "May lose important data points. Could remove legitimate extreme values that are not errors."
    },
    "cap_outliers": {
        "pros": "Preserves all rows while reducing the impact of extremes. Maintains more information than removal.",
        "cons": "Introduces artificial values. May distort the true distribution of data."
    },
    "keep_outliers": {
        "pros": "Preserves all original data. Outliers may contain important information or represent real phenomena.",
        "cons": "May distort visualizations and statistical summaries. Can make it difficult to see patterns in the majority of data."
    },
    "drop_duplicates_first": {
        "pros": "Removes redundant data that inflates counts. Keeps the first occurrence which may be chronologically earlier.",
        "cons": "Loses information if duplicate rows contain slight variations. May not keep the 'best' version of duplicated data."
    },
    "drop_duplicate_columns": {
        "pros": "Reduces data redundancy and file size. Simplifies visualizations and analysis.",
        "cons": "May remove columns that seem identical now but could diverge with future data updates."
    },
    "keep_missing": {
        "pros": "Preserves original data without modification. Missing values may be meaningful (e.g., 'not applicable'). Avoids introducing artificial data.",
        "cons": "Visualizations may show gaps. Some analysis methods cannot handle missing values. May need special handling downstream."
    }
}

# GPT-4 configuration
OPENAI_CONFIG = {
    "model": "gpt-4o",
    "temperature": 0.7,
    "max_tokens": 800,
    "timeout": 10,  # seconds
}

# GPT Recommendation configuration
RECOMMENDATION_CONFIG = {
    "enabled": True,  # Global toggle
    "min_options": 2,  # Only recommend if 2+ options available
    "timeout": 8,  # Timeout for recommendation API calls (seconds)
    "temperature": 0.3,  # Lower = more deterministic recommendations
    "max_tokens": 150,  # Keep reasons short and concise
    "max_retries": 1,  # Retry once on failure (2 attempts total)
}
