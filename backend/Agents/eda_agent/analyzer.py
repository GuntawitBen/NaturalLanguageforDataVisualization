"""
Core EDA analysis orchestrator
"""
import pandas as pd
import time
import uuid
from typing import Dict, List, Any
from pathlib import Path

from .statistics import (
    calculate_column_statistics,
    calculate_dataset_summary,
    get_sample_rows,
    detect_outliers_iqr
)
from .openai_client import OpenAIClient
from .models import (
    EDAReport,
    DataIssue,
    ColumnStatistics,
    DatasetSummary,
    EDAErrorResponse
)
from .config import (
    MAX_SAMPLE_ROWS,
    MISSING_VALUE_WARNING_THRESHOLD,
    MISSING_VALUE_CRITICAL_THRESHOLD,
    SKEWNESS_THRESHOLD,
    KURTOSIS_THRESHOLD,
    LARGE_DATASET_THRESHOLD,
    VISUALIZATION_SAMPLE_SIZE,
    Severity,
    IssueType
)

class EDAAnalyzer:
    """Main EDA analyzer class"""

    def __init__(self, openai_api_key: str = None):
        """
        Initialize EDA analyzer

        Args:
            openai_api_key: Optional OpenAI API key override
        """
        self.openai_client = OpenAIClient(api_key=openai_api_key)

    def analyze_csv(
        self,
        file_path: str,
        include_sample_rows: bool = True,
        max_sample_rows: int = MAX_SAMPLE_ROWS
    ) -> EDAReport:
        """
        Perform comprehensive EDA analysis on a CSV file

        Args:
            file_path: Path to CSV file
            include_sample_rows: Whether to include sample rows in GPT-4 analysis
            max_sample_rows: Maximum number of sample rows to send

        Returns:
            EDAReport with complete analysis
        """
        start_time = time.time()

        # Validate file exists
        if not Path(file_path).exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        # Load CSV into pandas
        df = pd.read_csv(file_path)

        # Get file size
        file_size_bytes = Path(file_path).stat().st_size

        # Step 1: Calculate dataset summary
        dataset_summary_dict = calculate_dataset_summary(df)
        dataset_summary_dict['file_size_bytes'] = file_size_bytes
        dataset_summary = DatasetSummary(**dataset_summary_dict)

        # Step 2: Calculate column-level statistics
        column_stats_list = []
        for column in df.columns:
            col_stats = calculate_column_statistics(df, column)
            column_stats_list.append(ColumnStatistics(**col_stats))

        # Step 3: Detect programmatic issues
        issues = []
        detected_issues_summary = {
            'missing_values_count': 0,
            'outliers_count': 0,
            'high_cardinality_count': 0,
            'duplicate_rows': dataset_summary.duplicate_row_count
        }

        # Issue detection: Missing values
        for col_stat in column_stats_list:
            if col_stat.null_percentage > 0:
                detected_issues_summary['missing_values_count'] += 1

                severity = Severity.INFO
                if col_stat.null_percentage >= MISSING_VALUE_CRITICAL_THRESHOLD * 100:
                    severity = Severity.CRITICAL
                elif col_stat.null_percentage >= MISSING_VALUE_WARNING_THRESHOLD * 100:
                    severity = Severity.WARNING

                issues.append(DataIssue(
                    issue_id=str(uuid.uuid4()),
                    type=IssueType.MISSING_VALUES,
                    severity=severity,
                    title=f"Missing values in '{col_stat.column_name}'",
                    description=f"Column '{col_stat.column_name}' has {col_stat.null_count} missing values ({col_stat.null_percentage:.1f}% of total rows).",
                    affected_columns=[col_stat.column_name],
                    recommendation=self._get_missing_value_recommendation(col_stat.null_percentage),
                    metadata={
                        "null_count": col_stat.null_count,
                        "null_percentage": col_stat.null_percentage
                    }
                ))

        # Issue detection: Outliers
        for col_stat in column_stats_list:
            if col_stat.has_outliers:
                detected_issues_summary['outliers_count'] += 1

                issues.append(DataIssue(
                    issue_id=str(uuid.uuid4()),
                    type=IssueType.OUTLIERS,
                    severity=Severity.WARNING,
                    title=f"Outliers detected in '{col_stat.column_name}'",
                    description=f"Column '{col_stat.column_name}' contains {col_stat.outlier_count} outlier values that may skew visualizations.",
                    affected_columns=[col_stat.column_name],
                    recommendation="Review outliers and consider: (1) removing them if they're errors, (2) capping extreme values, or (3) using log scale for visualization.",
                    metadata={
                        "outlier_count": col_stat.outlier_count,
                        "min": col_stat.min,
                        "max": col_stat.max,
                        "mean": col_stat.mean
                    }
                ))

        # Issue detection: High cardinality
        for col_stat in column_stats_list:
            if col_stat.is_high_cardinality:
                detected_issues_summary['high_cardinality_count'] += 1

                issues.append(DataIssue(
                    issue_id=str(uuid.uuid4()),
                    type=IssueType.HIGH_CARDINALITY,
                    severity=Severity.WARNING,
                    title=f"High cardinality in '{col_stat.column_name}'",
                    description=f"Column '{col_stat.column_name}' has {col_stat.unique_count} unique values, which may cause performance issues or cluttered visualizations.",
                    affected_columns=[col_stat.column_name],
                    recommendation="Consider: (1) grouping values into categories, (2) filtering to top N values, or (3) avoiding this column for categorical charts.",
                    metadata={
                        "unique_count": col_stat.unique_count
                    }
                ))

        # Issue detection: Duplicate rows
        if dataset_summary.duplicate_row_count > 0:
            severity = Severity.WARNING if dataset_summary.duplicate_row_percentage > 5 else Severity.INFO

            issues.append(DataIssue(
                issue_id=str(uuid.uuid4()),
                type=IssueType.DUPLICATE_ROWS,
                severity=severity,
                title="Duplicate rows detected",
                description=f"Found {dataset_summary.duplicate_row_count} duplicate rows ({dataset_summary.duplicate_row_percentage:.1f}% of dataset).",
                affected_columns=[],
                recommendation="Review duplicates to determine if they're intentional. Consider removing duplicates if they represent data entry errors.",
                metadata={
                    "duplicate_count": dataset_summary.duplicate_row_count,
                    "duplicate_percentage": dataset_summary.duplicate_row_percentage
                }
            ))

        # Issue detection: Skewed distributions
        for col_stat in column_stats_list:
            if col_stat.skewness is not None and abs(col_stat.skewness) > SKEWNESS_THRESHOLD:
                issues.append(DataIssue(
                    issue_id=str(uuid.uuid4()),
                    type=IssueType.SKEWED_DISTRIBUTION,
                    severity=Severity.INFO,
                    title=f"Skewed distribution in '{col_stat.column_name}'",
                    description=f"Column '{col_stat.column_name}' has a skewness of {col_stat.skewness:.2f}, indicating {'right' if col_stat.skewness > 0 else 'left'}-skewed data.",
                    affected_columns=[col_stat.column_name],
                    recommendation="Consider: (1) log transformation for right-skewed data, (2) using median instead of mean for summaries, or (3) box plots instead of histograms for visualization.",
                    metadata={
                        "skewness": col_stat.skewness,
                        "direction": "right" if col_stat.skewness > 0 else "left"
                    }
                ))

        # Issue detection: Heavy-tailed distributions
        for col_stat in column_stats_list:
            if col_stat.kurtosis is not None and col_stat.kurtosis > KURTOSIS_THRESHOLD:
                issues.append(DataIssue(
                    issue_id=str(uuid.uuid4()),
                    type=IssueType.HEAVY_TAILS,
                    severity=Severity.INFO,
                    title=f"Heavy-tailed distribution in '{col_stat.column_name}'",
                    description=f"Column '{col_stat.column_name}' has kurtosis of {col_stat.kurtosis:.2f}, indicating heavy tails with potential extreme values.",
                    affected_columns=[col_stat.column_name],
                    recommendation="Consider: (1) checking for data quality issues, (2) using robust statistics (median, IQR), or (3) trimming extreme values for visualization.",
                    metadata={
                        "kurtosis": col_stat.kurtosis
                    }
                ))

        # Issue detection: Large dataset
        if dataset_summary.row_count > LARGE_DATASET_THRESHOLD:
            issues.append(DataIssue(
                issue_id=str(uuid.uuid4()),
                type=IssueType.LARGE_DATASET,
                severity=Severity.INFO,
                title="Large dataset may impact visualization performance",
                description=f"Dataset has {dataset_summary.row_count:,} rows. Visualizations may be slow or cluttered.",
                affected_columns=[],
                recommendation=f"Consider: (1) sampling to ~{VISUALIZATION_SAMPLE_SIZE:,} rows for interactive visualizations, (2) using aggregation (binning, grouping), or (3) using specialized visualization techniques (heatmaps, density plots).",
                metadata={
                    "row_count": dataset_summary.row_count,
                    "recommended_sample_size": VISUALIZATION_SAMPLE_SIZE
                }
            ))

        # Step 4: Get sample rows for GPT-4 analysis
        sample_rows = []
        if include_sample_rows:
            sample_rows = get_sample_rows(df, n=max_sample_rows)

        # Step 5: Send to GPT-4 for deeper analysis
        gpt_result = self.openai_client.analyze_dataset(
            dataset_summary=dataset_summary_dict,
            column_statistics=[col_stat.dict() for col_stat in column_stats_list],
            sample_rows=sample_rows,
            detected_issues_summary=detected_issues_summary
        )

        # Handle GPT-4 response
        gpt_summary = ""
        visualization_concerns = []

        if gpt_result['success']:
            gpt_summary = gpt_result['summary']
            visualization_concerns = gpt_result['visualization_concerns']

            # Add GPT-4 detected issues
            for issue_data in gpt_result.get('additional_issues', []):
                issues.append(DataIssue(
                    issue_id=str(uuid.uuid4()),
                    type=issue_data.get('type', IssueType.VISUALIZATION_CONCERN),
                    severity=issue_data.get('severity', Severity.INFO),
                    title=issue_data.get('title', 'GPT-4 Detected Issue'),
                    description=issue_data.get('description', ''),
                    affected_columns=issue_data.get('affected_columns', []),
                    recommendation=issue_data.get('recommendation', ''),
                    metadata=issue_data.get('metadata')
                ))
        else:
            # Use fallback summary if GPT-4 fails
            gpt_summary = gpt_result.get('fallback_summary', 'Analysis completed with automated checks only.')
            # Log error for debugging
            print(f"[WARNING] GPT-4 analysis failed: {gpt_result.get('error')}")

        # Step 6: Count issues by severity
        critical_count = sum(1 for issue in issues if issue.severity == Severity.CRITICAL)
        warning_count = sum(1 for issue in issues if issue.severity == Severity.WARNING)
        info_count = sum(1 for issue in issues if issue.severity == Severity.INFO)

        # Step 7: Build final report
        analysis_duration = time.time() - start_time

        report = EDAReport(
            success=True,
            dataset_summary=dataset_summary,
            column_statistics=column_stats_list,
            issues=issues,
            critical_issues_count=critical_count,
            warning_issues_count=warning_count,
            info_issues_count=info_count,
            gpt_summary=gpt_summary,
            visualization_concerns=visualization_concerns,
            analysis_duration_seconds=round(analysis_duration, 2)
        )

        return report

    def _get_missing_value_recommendation(self, null_percentage: float) -> str:
        """Generate recommendation based on missing value percentage"""
        if null_percentage >= MISSING_VALUE_CRITICAL_THRESHOLD * 100:
            return "High percentage of missing values. Consider: (1) removing this column if not essential, (2) imputing with domain knowledge, or (3) investigating data collection issues."
        elif null_percentage >= MISSING_VALUE_WARNING_THRESHOLD * 100:
            return "Moderate missing values. Consider: (1) imputation with mean/median/mode, (2) forward/backward fill for time series, or (3) excluding rows with missing values if acceptable."
        else:
            return "Low percentage of missing values. Can likely be handled by: (1) removing affected rows, (2) simple imputation, or (3) marking as 'Unknown' category."
