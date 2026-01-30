"""
Configuration for the proactive agent.
"""

# Detection thresholds for signal detection
DETECTION_THRESHOLDS = {
    "trend": {
        "r_squared_min": 0.6,  # Minimum R² for trend detection
        "min_data_points": 5,  # Minimum data points for trend analysis
    },
    "outlier": {
        "iqr_multiplier": 1.5,  # IQR multiplier for outlier detection
        "min_count": 1,  # Minimum outlier count to report
    },
    "dominance": {
        "min_percentage": 50,  # Minimum % for a category to be dominant
        "min_categories": 2,  # Minimum categories needed
    },
    "seasonality": {
        "acf_threshold": 0.5,  # Minimum ACF peak for seasonality
        "min_periods": 2,  # Minimum periods to detect
    },
    "imbalance": {
        "gini_threshold": 0.4,  # Minimum Gini coefficient for imbalance
        "min_categories": 3,  # Minimum categories needed
    },
}

# Importance levels based on signal strength
IMPORTANCE_THRESHOLDS = {
    "high": 0.8,
    "medium": 0.5,
    "low": 0.0,
}

# OpenAI configuration for LLM calls
OPENAI_CONFIG = {
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 500,
    "timeout": 15,
}

# Chart type mappings for exploration choices (using string keys)
CHART_MAPPINGS = {
    "trend": {
        "explore_trend": "line_with_trendline",
        "drill_down": "multi_line",
        "compare_periods": "grouped_bar",
    },
    "outlier": {
        "investigate": "scatter_highlight",
        "see_distribution": "histogram",
        "compare_context": "box_plot",
    },
    "dominance": {
        "see_breakdown": "pie",
        "compare_over_time": "stacked_bar",
        "drill_into_dominant": "bar",
    },
    "seasonality": {
        "view_pattern": "line_full",
        "compare_periods": "multi_line",
        "see_decomposition": "area",
    },
    "imbalance": {
        "compare_distribution": "histogram",
        "see_breakdown": "bar",
        "pareto_analysis": "pareto",
    },
}

# SQL templates for common exploration queries
SQL_TEMPLATES = {
    "trend_over_time": """
        SELECT {date_column}, {value_column}
        FROM {table_name}
        ORDER BY {date_column}
    """,
    "trend_by_category": """
        SELECT {date_column}, {category_column}, SUM({value_column}) as total
        FROM {table_name}
        GROUP BY {date_column}, {category_column}
        ORDER BY {date_column}
    """,
    "outlier_details": """
        SELECT *
        FROM {table_name}
        WHERE {column} < {lower_bound} OR {column} > {upper_bound}
        ORDER BY {column} DESC
        LIMIT 100
    """,
    "category_breakdown": """
        SELECT {category_column}, COUNT(*) as count,
               ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM {table_name}), 2) as percentage
        FROM {table_name}
        GROUP BY {category_column}
        ORDER BY count DESC
    """,
    "distribution": """
        SELECT {column}, COUNT(*) as frequency
        FROM {table_name}
        GROUP BY {column}
        ORDER BY {column}
    """,
}

# Maximum insights to return
MAX_INSIGHTS = 10
MAX_CHOICES_PER_OBSERVATION = 3
