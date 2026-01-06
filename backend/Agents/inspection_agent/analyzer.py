"""
Core Inspection Analyzer
"""
import pandas as pd
import time
import uuid
from typing import Dict, List, Any
from pathlib import Path

from .data_quality_checks import (
    detect_missing_values,
    detect_duplicate_rows,
    detect_duplicate_columns,
    detect_outliers_iqr,
    detect_outliers_zscore,
    detect_outliers_isolation_forest,
    detect_mixed_data_types,
    detect_invalid_values,
    analyze_cardinality,
    analyze_distribution
)
from .openai_client import OpenAIClient
from .models import (
    InspectionReport,
    DataIssue,
    ColumnStatistics,
    DatasetSummary
)
from .config import (
    MAX_SAMPLE_ROWS,
    MISSING_VALUE_INFO_THRESHOLD,
    MISSING_VALUE_WARNING_THRESHOLD,
    MISSING_VALUE_CRITICAL_THRESHOLD,
    DUPLICATE_ROW_WARNING_THRESHOLD,
    LARGE_DATASET_THRESHOLD,
    VISUALIZATION_SAMPLE_SIZE,
    Severity,
    IssueType
)

class InspectionAnalyzer:
    """Main inspection analyzer class"""

    def __init__(self, openai_api_key: str = None):
        """Initialize inspection analyzer"""
        self.openai_client = OpenAIClient(api_key=openai_api_key)

    def analyze_csv(
        self,
        file_path: str,
        include_sample_rows: bool = True,
        max_sample_rows: int = MAX_SAMPLE_ROWS
    ) -> InspectionReport:
        """
        Perform comprehensive inspection analysis on a CSV file
        """
        start_time = time.time()

        # Validate file exists
        if not Path(file_path).exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        # Load CSV
        df = pd.read_csv(file_path)
        file_size_bytes = Path(file_path).stat().st_size

        # Step 1: Calculate dataset summary
        dataset_summary = self._calculate_dataset_summary(df, file_size_bytes)

        # Step 2: Calculate column-level statistics
        column_stats_list = self._calculate_column_statistics(df)

        # Step 3: Detect data quality issues
        issues = self._detect_issues(df, dataset_summary, column_stats_list)

        # Step 3.5: Enrich issues with dynamic GPT-4 visualization impacts
        print(f"[INFO] Enriching {len(issues)} issues with GPT-4 visualization impacts...")
        issues = self._enrich_issues_with_impacts(df, issues, column_stats_list)

        # Step 4: Get sample rows for GPT-4
        sample_rows = []
        if include_sample_rows:
            sample_rows = self._get_sample_rows(df, max_sample_rows)

        # Step 5: GPT-4 analysis
        gpt_result = self._get_gpt_analysis(
            dataset_summary=dataset_summary.dict(),
            column_statistics=[col.dict() for col in column_stats_list],
            sample_rows=sample_rows,
            detected_issues_summary=self._get_issues_summary(issues)
        )

        gpt_summary = gpt_result.get('summary', 'Analysis completed.')
        visualization_concerns = gpt_result.get('visualization_concerns', [])

        # Add GPT-4 detected issues
        if gpt_result.get('success') and gpt_result.get('additional_issues'):
            for issue_data in gpt_result['additional_issues']:
                issues.append(self._create_data_issue(
                    issue_type=issue_data.get('type', IssueType.VISUALIZATION_CONCERN),
                    severity=issue_data.get('severity', Severity.INFO),
                    title=issue_data.get('title', 'GPT-4 Detected Issue'),
                    description=issue_data.get('description', ''),
                    affected_columns=issue_data.get('affected_columns', []),
                    recommendation=issue_data.get('recommendation', ''),
                    visualization_impact=issue_data.get('visualization_impact', 'This issue may affect visualization quality.'),
                    metadata=issue_data.get('metadata')
                ))

        # Step 6: Count issues by severity
        critical_count = sum(1 for issue in issues if issue.severity == Severity.CRITICAL)
        warning_count = sum(1 for issue in issues if issue.severity == Severity.WARNING)
        info_count = sum(1 for issue in issues if issue.severity == Severity.INFO)

        # Step 7: Build final report
        analysis_duration = time.time() - start_time

        report = InspectionReport(
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

    def _calculate_dataset_summary(self, df: pd.DataFrame, file_size_bytes: int) -> DatasetSummary:
        """Calculate high-level dataset summary"""
        # Duplicate rows
        dup_result = detect_duplicate_rows(df)

        # Duplicate columns
        dup_columns = detect_duplicate_columns(df)

        # Overall completeness
        total_cells = df.shape[0] * df.shape[1]
        non_null_cells = total_cells - df.isna().sum().sum()
        overall_completeness = (non_null_cells / total_cells * 100) if total_cells > 0 else 100.0

        # Memory usage
        memory_usage_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)

        return DatasetSummary(
            row_count=len(df),
            column_count=len(df.columns),
            file_size_bytes=file_size_bytes,
            duplicate_row_count=dup_result['duplicate_count'],
            duplicate_row_percentage=dup_result['duplicate_percentage'],
            duplicate_column_count=len(dup_columns),
            overall_completeness=overall_completeness,
            memory_usage_mb=memory_usage_mb
        )

    def _calculate_column_statistics(self, df: pd.DataFrame) -> List[ColumnStatistics]:
        """Calculate statistics for each column"""
        stats_list = []

        for column in df.columns:
            col_data = df[column]
            dtype_str = str(col_data.dtype)

            # Basic stats
            null_count = col_data.isna().sum()
            null_percentage = (null_count / len(df)) * 100 if len(df) > 0 else 0
            unique_count = col_data.nunique()

            stat_dict = {
                'column_name': column,
                'data_type': dtype_str,
                'null_count': int(null_count),
                'null_percentage': float(null_percentage),
                'unique_count': int(unique_count)
            }

            # Numeric columns
            if pd.api.types.is_numeric_dtype(col_data):
                non_null = col_data.dropna()
                if len(non_null) > 0:
                    # Run all three outlier detection methods
                    outlier_iqr = detect_outliers_iqr(df, column)
                    outlier_zscore = detect_outliers_zscore(df, column)
                    outlier_iforest = detect_outliers_isolation_forest(df, column)

                    # Use IQR as primary method
                    has_outliers = outlier_iqr['has_outliers']
                    outlier_count = outlier_iqr['outlier_count']

                    # Distribution analysis
                    dist_result = analyze_distribution(df, column)

                    stat_dict.update({
                        'min': float(non_null.min()),
                        'max': float(non_null.max()),
                        'mean': float(non_null.mean()),
                        'median': float(non_null.median()),
                        'std_dev': float(non_null.std()),
                        'skewness': dist_result.get('skewness'),
                        'kurtosis': dist_result.get('kurtosis'),
                        'has_outliers': has_outliers,
                        'outlier_count': outlier_count,
                        'outlier_method': 'iqr'
                    })

            # Categorical/String columns
            if dtype_str == 'object' or pd.api.types.is_categorical_dtype(col_data):
                # Cardinality analysis
                card_result = analyze_cardinality(df, column)

                # Top values
                top_values = []
                value_counts = col_data.value_counts().head(10)
                for value, count in value_counts.items():
                    top_values.append({
                        'value': str(value),
                        'count': int(count),
                        'percentage': float((count / len(df)) * 100)
                    })

                stat_dict.update({
                    'top_values': top_values,
                    'is_high_cardinality': card_result['is_high_cardinality'],
                    'cardinality_level': card_result['cardinality_level']
                })

                # String length analysis
                if dtype_str == 'object':
                    str_lengths = col_data.dropna().astype(str).str.len()
                    if len(str_lengths) > 0:
                        stat_dict.update({
                            'min_length': int(str_lengths.min()),
                            'max_length': int(str_lengths.max()),
                            'avg_length': float(str_lengths.mean())
                        })

            stats_list.append(ColumnStatistics(**stat_dict))

        return stats_list

    def _detect_issues(
        self,
        df: pd.DataFrame,
        dataset_summary: DatasetSummary,
        column_stats_list: List[ColumnStatistics]
    ) -> List[DataIssue]:
        """Detect all data quality issues"""
        issues = []

        # 1. Missing values
        issues.extend(self._detect_missing_value_issues(df))

        # 2. Duplicate rows
        if dataset_summary.duplicate_row_count > 0:
            issues.append(self._create_duplicate_row_issue(dataset_summary))

        # 3. Duplicate columns
        dup_columns = detect_duplicate_columns(df)
        if len(dup_columns) > 0:
            issues.append(self._create_duplicate_column_issue(dup_columns))

        # 4. Outliers
        issues.extend(self._detect_outlier_issues(df, column_stats_list))

        # 5. Mixed data types
        issues.extend(self._detect_mixed_type_issues(df))

        # 6. Large dataset warning
        if dataset_summary.row_count > LARGE_DATASET_THRESHOLD:
            issues.append(self._create_large_dataset_issue(dataset_summary))

        return issues

    def _detect_missing_value_issues(self, df: pd.DataFrame) -> List[DataIssue]:
        """Detect missing value issues"""
        issues = []

        for column in df.columns:
            result = detect_missing_values(df, column)

            if result['total_null_count'] > 0:
                null_pct = result['total_null_percentage']

                # Determine severity
                if null_pct >= MISSING_VALUE_CRITICAL_THRESHOLD * 100:
                    severity = Severity.CRITICAL
                elif null_pct >= MISSING_VALUE_WARNING_THRESHOLD * 100:
                    severity = Severity.WARNING
                elif null_pct >= MISSING_VALUE_INFO_THRESHOLD * 100:
                    severity = Severity.INFO
                else:
                    continue  # Skip very small percentages

                desc = f"Column '{column}' has {result['total_null_count']} missing values ({null_pct:.1f}% of total rows)."
                if result['null_like_count'] > 0:
                    desc += f" This includes {result['null_like_count']} null-like values (empty strings, 'NA', etc.)."

                issues.append(self._create_data_issue(
                    issue_type=IssueType.MISSING_VALUES,
                    severity=severity,
                    title=f"Missing values in '{column}'",
                    description=desc,
                    affected_columns=[column],
                    recommendation=self._get_missing_value_recommendation(null_pct),
                    visualization_impact="[GPT-4 will generate dynamic impact]",  # Placeholder
                    metadata=result
                ))

        return issues

    def _create_duplicate_row_issue(self, dataset_summary: DatasetSummary) -> DataIssue:
        """Create duplicate row issue"""
        severity = (Severity.WARNING if dataset_summary.duplicate_row_percentage > DUPLICATE_ROW_WARNING_THRESHOLD * 100
                   else Severity.INFO)

        return self._create_data_issue(
            issue_type=IssueType.DUPLICATE_ROWS,
            severity=severity,
            title="Duplicate rows detected",
            description=f"Found {dataset_summary.duplicate_row_count} duplicate rows ({dataset_summary.duplicate_row_percentage:.1f}% of dataset).",
            affected_columns=[],
            recommendation="Review duplicates to determine if they're intentional. Consider removing duplicates if they represent data entry errors.",
            visualization_impact="[GPT-4 will generate dynamic impact]",  # Placeholder
            metadata={
                'duplicate_count': dataset_summary.duplicate_row_count,
                'duplicate_percentage': dataset_summary.duplicate_row_percentage
            }
        )

    def _create_duplicate_column_issue(self, dup_columns: List[tuple]) -> DataIssue:
        """Create duplicate column issue"""
        affected = list(set([col for pair in dup_columns for col in pair]))

        desc = f"Found {len(dup_columns)} pair(s) of duplicate columns: "
        desc += ", ".join([f"'{col1}' = '{col2}'" for col1, col2 in dup_columns[:5]])
        if len(dup_columns) > 5:
            desc += f" and {len(dup_columns) - 5} more..."

        return self._create_data_issue(
            issue_type=IssueType.DUPLICATE_COLUMNS,
            severity=Severity.WARNING,
            title="Duplicate columns detected",
            description=desc,
            affected_columns=affected,
            recommendation="Remove duplicate columns to reduce dataset size and avoid confusion. Keep only one column from each duplicate pair.",
            visualization_impact="[GPT-4 will generate dynamic impact]",  # Placeholder
            metadata={
                'duplicate_pairs': dup_columns,
                'pair_count': len(dup_columns)
            }
        )

    def _detect_outlier_issues(self, df: pd.DataFrame, column_stats_list: List[ColumnStatistics]) -> List[DataIssue]:
        """Detect outlier issues using multiple methods"""
        issues = []

        for col_stat in column_stats_list:
            if col_stat.has_outliers:
                column = col_stat.column_name

                # Run all three methods
                iqr_result = detect_outliers_iqr(df, column)
                zscore_result = detect_outliers_zscore(df, column)
                iforest_result = detect_outliers_isolation_forest(df, column)

                # Use the method that found outliers
                methods_with_outliers = []
                if iqr_result['has_outliers']:
                    methods_with_outliers.append(f"IQR ({iqr_result['outlier_count']} outliers)")
                if zscore_result['has_outliers']:
                    methods_with_outliers.append(f"Z-score ({zscore_result['outlier_count']} outliers)")
                if iforest_result['has_outliers']:
                    methods_with_outliers.append(f"Isolation Forest ({iforest_result['outlier_count']} outliers)")

                desc = f"Column '{column}' contains outliers detected by multiple methods: {', '.join(methods_with_outliers)}."

                issues.append(self._create_data_issue(
                    issue_type=IssueType.OUTLIERS_IQR,
                    severity=Severity.WARNING,
                    title=f"Outliers detected in '{column}'",
                    description=desc,
                    affected_columns=[column],
                    recommendation="Review outliers and consider: (1) removing them if they're errors, (2) capping extreme values, or (3) using log scale for visualization.",
                    visualization_impact="[GPT-4 will generate dynamic impact]",  # Placeholder
                    metadata={
                        'iqr_result': iqr_result,
                        'zscore_result': zscore_result,
                        'iforest_result': iforest_result,
                        'methods_count': len(methods_with_outliers)
                    }
                ))

        return issues

    def _detect_mixed_type_issues(self, df: pd.DataFrame) -> List[DataIssue]:
        """Detect mixed data type issues"""
        issues = []

        for column in df.columns:
            result = detect_mixed_data_types(df, column)

            if result['has_mixed_types'] and result['total_types'] > 1:
                type_info = ", ".join([
                    f"{type_name}: {info['percentage']:.1f}%"
                    for type_name, info in result['type_distribution'].items()
                ])

                issues.append(self._create_data_issue(
                    issue_type=IssueType.MIXED_DATA_TYPES,
                    severity=Severity.WARNING,
                    title=f"Mixed data types in '{column}'",
                    description=f"Column '{column}' contains multiple data types: {type_info}.",
                    affected_columns=[column],
                    recommendation="Standardize the column to a single data type. Convert or clean inconsistent values.",
                    visualization_impact="[GPT-4 will generate dynamic impact]",  # Placeholder
                    metadata=result
                ))

        return issues

    def _create_large_dataset_issue(self, dataset_summary: DatasetSummary) -> DataIssue:
        """Create large dataset issue"""
        return self._create_data_issue(
            issue_type=IssueType.LARGE_DATASET,
            severity=Severity.INFO,
            title="Large dataset may impact visualization performance",
            description=f"Dataset has {dataset_summary.row_count:,} rows. Visualizations may be slow or cluttered.",
            affected_columns=[],
            recommendation=f"Consider sampling to ~{VISUALIZATION_SAMPLE_SIZE:,} rows for interactive visualizations, using aggregation (binning, grouping), or specialized visualization techniques (heatmaps, density plots).",
            visualization_impact="[GPT-4 will generate dynamic impact]",  # Placeholder
            metadata={
                'row_count': dataset_summary.row_count,
                'recommended_sample_size': VISUALIZATION_SAMPLE_SIZE
            }
        )

    def _create_data_issue(
        self,
        issue_type: str,
        severity: str,
        title: str,
        description: str,
        affected_columns: List[str],
        recommendation: str,
        visualization_impact: str,
        metadata: Dict[str, Any] = None
    ) -> DataIssue:
        """Helper to create DataIssue"""
        return DataIssue(
            issue_id=str(uuid.uuid4()),
            type=issue_type,
            severity=severity,
            title=title,
            description=description,
            affected_columns=affected_columns,
            recommendation=recommendation,
            visualization_impact=visualization_impact,
            metadata=metadata
        )

    def _enrich_issues_with_impacts(
        self,
        df: pd.DataFrame,
        issues: List[DataIssue],
        column_stats_list: List[ColumnStatistics]
    ) -> List[DataIssue]:
        """
        Enrich detected issues with dynamic GPT-4 visualization impact explanations
        """
        enriched_issues = []

        for issue in issues:
            try:
                # Get column details for affected columns
                column_details = {}
                for col_name in issue.affected_columns:
                    col_stat = next((c for c in column_stats_list if c.column_name == col_name), None)
                    if col_stat:
                        column_details[col_name] = col_stat.dict()

                # Get sample values if applicable
                sample_values = None
                if issue.affected_columns and len(issue.affected_columns) > 0:
                    col_name = issue.affected_columns[0]
                    if col_name in df.columns:
                        sample_values = df[col_name].dropna().head(10).tolist()

                # Generate dynamic visualization impact
                visualization_impact = self.openai_client.generate_visualization_impact(
                    issue_title=issue.title,
                    issue_type=issue.type,
                    issue_description=issue.description,
                    affected_columns=issue.affected_columns,
                    column_details=column_details,
                    sample_values=sample_values
                )

                # Update issue with generated impact
                issue.visualization_impact = visualization_impact
                enriched_issues.append(issue)

                print(f"  ✓ Generated impact for: {issue.title}")

            except Exception as e:
                # If GPT-4 fails, keep the original issue
                print(f"  ✗ Failed to generate impact for {issue.title}: {str(e)}")
                enriched_issues.append(issue)

        return enriched_issues

    def _get_missing_value_recommendation(self, null_percentage: float) -> str:
        """Generate recommendation based on missing value percentage"""
        if null_percentage >= MISSING_VALUE_CRITICAL_THRESHOLD * 100:
            return "High percentage of missing values. Consider: (1) removing this column if not essential, (2) imputing with domain knowledge, or (3) investigating data collection issues."
        elif null_percentage >= MISSING_VALUE_WARNING_THRESHOLD * 100:
            return "Moderate missing values. Consider: (1) imputation with mean/median/mode, (2) forward/backward fill for time series, or (3) excluding rows with missing values if acceptable."
        else:
            return "Low percentage of missing values. Can likely be handled by: (1) removing affected rows, (2) simple imputation, or (3) marking as 'Unknown' category."

    def _get_sample_rows(self, df: pd.DataFrame, n: int = 20) -> List[Dict[str, Any]]:
        """Get sample rows from dataframe"""
        sample_df = df.head(n)
        return sample_df.to_dict('records')

    def _get_issues_summary(self, issues: List[DataIssue]) -> Dict[str, int]:
        """Get summary of detected issues"""
        return {
            'missing_values_count': sum(1 for i in issues if i.type == IssueType.MISSING_VALUES),
            'outliers_count': sum(1 for i in issues if 'outlier' in i.type.lower()),
            'duplicate_rows': sum(1 for i in issues if i.type == IssueType.DUPLICATE_ROWS),
            'duplicate_columns': sum(1 for i in issues if i.type == IssueType.DUPLICATE_COLUMNS),
            'mixed_types_count': sum(1 for i in issues if i.type == IssueType.MIXED_DATA_TYPES),
            'total_issues': len(issues)
        }

    def _get_gpt_analysis(
        self,
        dataset_summary: Dict[str, Any],
        column_statistics: List[Dict[str, Any]],
        sample_rows: List[Dict[str, Any]],
        detected_issues_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get GPT-4 analysis"""
        try:
            return self.openai_client.analyze_dataset(
                dataset_summary=dataset_summary,
                column_statistics=column_statistics,
                sample_rows=sample_rows,
                detected_issues_summary=detected_issues_summary
            )
        except Exception as e:
            print(f"[WARNING] GPT-4 analysis failed: {str(e)}")
            return {
                'success': False,
                'summary': 'Analysis completed with automated checks only.',
                'visualization_concerns': [],
                'additional_issues': []
            }
