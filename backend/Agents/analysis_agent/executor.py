"""
Predefined pandas analysis functions for statistical analysis.
Safe, no arbitrary code execution.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from .models import AnalysisResult


def _prepare_features(df: pd.DataFrame, target_col: str) -> tuple:
    """
    Prepare features for Random Forest: encode categoricals, drop IDs, handle NaNs.

    Returns:
        (X DataFrame, y Series, feature_names list) or (None, None, None) on failure
    """
    feature_cols = [c for c in df.columns if c != target_col]
    if not feature_cols:
        return None, None, None

    working = df[feature_cols + [target_col]].copy()

    # Drop columns that are likely IDs/unique identifiers
    # Heuristic: >80% unique values in non-numeric columns, or object columns with
    # cardinality close to row count
    cols_to_drop = []
    for col in feature_cols:
        nunique = working[col].nunique()
        total = len(working[col].dropna())
        if total == 0:
            cols_to_drop.append(col)
            continue
        ratio = nunique / total
        # String/object columns with very high cardinality are likely IDs
        if not pd.api.types.is_numeric_dtype(working[col]) and ratio > 0.5:
            cols_to_drop.append(col)
            print(f"[ANALYSIS] Dropping high-cardinality column '{col}' ({nunique}/{total} unique)")

    feature_cols = [c for c in feature_cols if c not in cols_to_drop]
    if not feature_cols:
        return None, None, None

    working = working[feature_cols + [target_col]].copy()

    # Encode categorical/object columns via label encoding
    encoded_col_names = []
    for col in feature_cols:
        if not pd.api.types.is_numeric_dtype(working[col]):
            # Label encode — NaN gets its own code
            working[col] = working[col].astype('category').cat.codes
        encoded_col_names.append(col)

    # Drop rows with NaN in target
    working = working.dropna(subset=[target_col])

    # Fill remaining NaN in features with median
    for col in encoded_col_names:
        if working[col].isna().any():
            working[col] = working[col].fillna(working[col].median())

    X = working[encoded_col_names]
    y = working[target_col]

    return X, y, encoded_col_names


def factor_impact(df: pd.DataFrame, target_col: str) -> AnalysisResult:
    """
    Use Random Forest feature importance to determine which columns most
    influence the target. Returns factors ranked by importance.

    Args:
        df: Dataset as DataFrame
        target_col: Column to measure (e.g., "Survived")

    Returns:
        AnalysisResult with bar chart data ranking factors by importance
    """
    if target_col not in df.columns:
        return AnalysisResult(
            data=[],
            columns=["Factor", "Importance"],
            summary=f"Column '{target_col}' not found in dataset.",
            chart_type="bar",
            chart_config={"x_axis": "Factor", "y_axis": "Importance", "title": "Factor Impact"}
        )

    try:
        X, y, feature_names = _prepare_features(df, target_col)
    except Exception as e:
        print(f"[ANALYSIS] Feature preparation failed: {e}")
        return AnalysisResult(
            data=[],
            columns=["Factor", "Importance"],
            summary=f"Could not prepare data for analysis: {e}",
            chart_type="bar",
            chart_config={"x_axis": "Factor", "y_axis": "Importance", "title": "Factor Impact"}
        )

    if X is None or len(X) == 0 or len(feature_names) == 0:
        return AnalysisResult(
            data=[],
            columns=["Factor", "Importance"],
            summary=f"No usable features found to analyze impact on {target_col}.",
            chart_type="bar",
            chart_config={"x_axis": "Factor", "y_axis": "Importance", "title": "Factor Impact"}
        )

    # Determine if classification or regression
    nunique_target = y.nunique()
    is_classification = nunique_target <= 20 or y.dtype == 'object'

    try:
        if is_classification:
            from sklearn.ensemble import RandomForestClassifier
            # Encode target if needed
            if y.dtype == 'object' or y.dtype.name == 'category':
                y = y.astype('category').cat.codes
            model = RandomForestClassifier(
                n_estimators=100, max_depth=6, random_state=42, n_jobs=-1
            )
        else:
            from sklearn.ensemble import RandomForestRegressor
            model = RandomForestRegressor(
                n_estimators=100, max_depth=6, random_state=42, n_jobs=-1
            )

        model.fit(X, y)
        importances = model.feature_importances_

    except Exception as e:
        print(f"[ANALYSIS] Random Forest failed: {e}")
        return AnalysisResult(
            data=[],
            columns=["Factor", "Importance"],
            summary=f"Analysis failed: {e}",
            chart_type="bar",
            chart_config={"x_axis": "Factor", "y_axis": "Importance", "title": "Factor Impact"}
        )

    # Build results sorted by importance
    results = []
    for name, imp in zip(feature_names, importances):
        results.append({
            "Factor": str(name),
            "Importance": round(float(imp), 4)
        })

    results.sort(key=lambda x: x["Importance"], reverse=True)

    # Build summary
    if results:
        top = results[0]
        summary = (
            f"'{top['Factor']}' is the most important factor for {target_col} "
            f"(importance: {top['Importance']:.3f}). "
        )
        if len(results) > 1:
            others = ", ".join(
                f"{r['Factor']} ({r['Importance']:.3f})"
                for r in results[1:min(4, len(results))]
            )
            summary += f"Other notable factors: {others}."
    else:
        summary = f"No significant factors found affecting {target_col}."

    return AnalysisResult(
        data=results,
        columns=["Factor", "Importance"],
        summary=summary,
        chart_type="bar",
        chart_config={
            "x_axis": "Factor",
            "y_axis": "Importance",
            "title": f"Feature Importance for {target_col} (Random Forest)",
        }
    )


def _is_categorical(series: pd.Series) -> bool:
    """Check if a Series is categorical (object, category, or low-cardinality integer like 0/1)."""
    if series.dtype == 'object' or series.dtype.name == 'category':
        return True
    # Treat integer columns with very few unique values (e.g. binary 0/1) as categorical
    if pd.api.types.is_integer_dtype(series) and series.nunique() <= 2:
        return True
    return False


def correlation_between(df: pd.DataFrame, col_x: str, col_y: str) -> AnalysisResult:
    """
    Compute correlation between two columns, automatically handling categorical data.

    - Both numeric → Pearson correlation + scatter plot
    - One categorical, one numeric → delegates to group_comparison (bar chart)
    - Both categorical → Cramér's V association + bar chart

    Args:
        df: Dataset as DataFrame
        col_x: First column
        col_y: Second column

    Returns:
        AnalysisResult with appropriate chart and correlation metric
    """
    missing = [c for c in [col_x, col_y] if c not in df.columns]
    if missing:
        return AnalysisResult(
            data=[],
            columns=[col_x, col_y],
            summary=f"Column(s) not found: {', '.join(missing)}",
            chart_type="scatter",
            chart_config={"x_axis": col_x, "y_axis": col_y, "title": "Correlation"}
        )

    working_df = df[[col_x, col_y]].dropna()

    if len(working_df) < 2:
        return AnalysisResult(
            data=[],
            columns=[col_x, col_y],
            summary=f"Not enough data to compute correlation between {col_x} and {col_y}.",
            chart_type="scatter",
            chart_config={"x_axis": col_x, "y_axis": col_y, "title": "Correlation"}
        )

    x_cat = _is_categorical(working_df[col_x])
    y_cat = _is_categorical(working_df[col_y])

    # --- Case 1: One categorical, one numeric → group comparison bar chart ---
    if x_cat and not y_cat:
        return _correlation_mixed(df, numeric_col=col_y, categorical_col=col_x)
    if y_cat and not x_cat:
        return _correlation_mixed(df, numeric_col=col_x, categorical_col=col_y)

    # --- Case 2: Both categorical → Cramér's V + bar chart ---
    if x_cat and y_cat:
        return _correlation_both_categorical(working_df, col_x, col_y)

    # --- Case 3: Both numeric → Pearson correlation + scatter (original behavior) ---
    try:
        working_df[col_x] = pd.to_numeric(working_df[col_x], errors='coerce')
        working_df[col_y] = pd.to_numeric(working_df[col_y], errors='coerce')
        working_df = working_df.dropna()
    except Exception:
        pass

    if len(working_df) < 2:
        return AnalysisResult(
            data=[],
            columns=[col_x, col_y],
            summary=f"Not enough numeric data to compute correlation between {col_x} and {col_y}.",
            chart_type="scatter",
            chart_config={"x_axis": col_x, "y_axis": col_y, "title": "Correlation"}
        )

    r_value = float(working_df[col_x].corr(working_df[col_y]))

    sample = working_df.sample(n=min(500, len(working_df)), random_state=42)
    scatter_data = [
        {col_x: round(float(row[col_x]), 4), col_y: round(float(row[col_y]), 4)}
        for _, row in sample.iterrows()
    ]

    abs_r = abs(r_value)
    if abs_r >= 0.7:
        strength = "strong"
    elif abs_r >= 0.4:
        strength = "moderate"
    elif abs_r >= 0.2:
        strength = "weak"
    else:
        strength = "very weak"

    direction = "positive" if r_value > 0 else "negative"
    summary = (
        f"The correlation between {col_x} and {col_y} is r = {r_value:.3f}, "
        f"indicating a {strength} {direction} relationship."
    )

    return AnalysisResult(
        data=scatter_data,
        columns=[col_x, col_y],
        summary=summary,
        chart_type="scatter",
        chart_config={
            "x_axis": col_x,
            "y_axis": col_y,
            "title": f"Correlation: {col_x} vs {col_y} (r = {r_value:.3f})",
            "correlation_r": round(r_value, 4),
        }
    )


def _correlation_mixed(df: pd.DataFrame, numeric_col: str, categorical_col: str) -> AnalysisResult:
    """Handle correlation between one categorical and one numeric column.
    Delegates to group_comparison for the bar chart, and computes point-biserial
    correlation (via label encoding) for the summary."""
    working_df = df[[categorical_col, numeric_col]].dropna()

    # Compute correlation via label encoding for the summary stat
    encoded = working_df[categorical_col].astype('category').cat.codes
    numeric_vals = pd.to_numeric(working_df[numeric_col], errors='coerce')
    pair = pd.DataFrame({'encoded': encoded, 'numeric': numeric_vals}).dropna()
    r_value = float(pair['encoded'].corr(pair['numeric'])) if len(pair) >= 2 else float('nan')

    # Delegate to group_comparison for the actual chart
    result = group_comparison(df, target_col=numeric_col, group_col=categorical_col)

    # Enhance summary with correlation info
    if not np.isnan(r_value):
        abs_r = abs(r_value)
        if abs_r >= 0.7:
            strength = "strong"
        elif abs_r >= 0.4:
            strength = "moderate"
        elif abs_r >= 0.2:
            strength = "weak"
        else:
            strength = "very weak"
        direction = "positive" if r_value > 0 else "negative"
        corr_note = (
            f" Point-biserial correlation: r = {r_value:.3f} "
            f"({strength} {direction} association)."
        )
        result.summary += corr_note

    result.chart_config["title"] = f"{numeric_col} by {categorical_col} (r = {r_value:.3f})"
    result.chart_config["correlation_r"] = round(r_value, 4)

    return result


def _correlation_both_categorical(working_df: pd.DataFrame, col_x: str, col_y: str) -> AnalysisResult:
    """Handle correlation between two categorical columns using Cramér's V."""
    # Compute Cramér's V from a contingency table
    contingency = pd.crosstab(working_df[col_x], working_df[col_y])
    n = contingency.sum().sum()
    # Chi-squared statistic
    expected = np.outer(contingency.sum(axis=1), contingency.sum(axis=0)) / n
    chi2 = float(((contingency.values - expected) ** 2 / expected).sum())
    k = min(contingency.shape) - 1
    cramers_v = float(np.sqrt(chi2 / (n * k))) if (n * k) > 0 else 0.0

    if cramers_v >= 0.5:
        strength = "strong"
    elif cramers_v >= 0.3:
        strength = "moderate"
    elif cramers_v >= 0.1:
        strength = "weak"
    else:
        strength = "very weak"

    # Build bar chart: rate of col_y values per col_x category
    # Use the most common col_y value as the "rate" target
    most_common_y = working_df[col_y].value_counts().index[0]
    rate_label = f"{col_y}={most_common_y} Rate"

    grouped = working_df.groupby(col_x)[col_y].apply(lambda s: (s == most_common_y).mean())
    counts = working_df.groupby(col_x)[col_y].count()

    chart_data = []
    summary_parts = []
    for group_val in grouped.index:
        rate = round(float(grouped[group_val]), 4)
        count = int(counts[group_val])
        chart_data.append({
            str(col_x): str(group_val),
            rate_label: rate,
            "Count": count,
        })
        summary_parts.append(f"{group_val}: {rate:.1%} (n={count})")

    summary = (
        f"Association between {col_x} and {col_y}: Cramér's V = {cramers_v:.3f} "
        f"({strength} association). "
        f"{rate_label} by {col_x}: " + ", ".join(summary_parts) + "."
    )

    return AnalysisResult(
        data=chart_data,
        columns=[str(col_x), rate_label],
        summary=summary,
        chart_type="bar",
        chart_config={
            "x_axis": str(col_x),
            "y_axis": rate_label,
            "title": f"{col_x} vs {col_y} (Cramér's V = {cramers_v:.3f})",
            "correlation_v": round(cramers_v, 4),
        }
    )


def group_comparison(df: pd.DataFrame, target_col: str, group_col: str) -> AnalysisResult:
    """
    Detailed breakdown of target rate for each value in group_col.

    Args:
        df: Dataset as DataFrame
        target_col: Column to measure (e.g., "Survived")
        group_col: Column to group by (e.g., "Pclass")

    Returns:
        AnalysisResult with bar chart data showing target rate per group
    """
    missing = [c for c in [target_col, group_col] if c not in df.columns]
    if missing:
        return AnalysisResult(
            data=[],
            columns=[group_col, f"{target_col} Rate"],
            summary=f"Column(s) not found: {', '.join(missing)}",
            chart_type="bar",
            chart_config={"x_axis": group_col, "y_axis": f"{target_col} Rate", "title": "Group Comparison"}
        )

    working_df = df[[group_col, target_col]].dropna()

    if len(working_df) == 0:
        return AnalysisResult(
            data=[],
            columns=[group_col, f"{target_col} Rate"],
            summary=f"No data available for {target_col} by {group_col}.",
            chart_type="bar",
            chart_config={"x_axis": group_col, "y_axis": f"{target_col} Rate", "title": "Group Comparison"}
        )

    grouped = working_df.groupby(group_col)[target_col].agg(['mean', 'count'])
    grouped = grouped.sort_values('mean', ascending=False)

    rate_label = f"{target_col} Rate"
    chart_data = []
    summary_parts = []

    for group_val, row in grouped.iterrows():
        rate = round(float(row['mean']), 4)
        count = int(row['count'])
        chart_data.append({
            str(group_col): str(group_val),
            rate_label: rate,
            "Count": count,
        })
        summary_parts.append(f"{group_val}: {rate:.1%} (n={count})")

    summary = f"{target_col} rate by {group_col}: " + ", ".join(summary_parts) + "."

    return AnalysisResult(
        data=chart_data,
        columns=[str(group_col), rate_label],
        summary=summary,
        chart_type="bar",
        chart_config={
            "x_axis": str(group_col),
            "y_axis": rate_label,
            "title": f"{target_col} Rate by {group_col}",
        }
    )
