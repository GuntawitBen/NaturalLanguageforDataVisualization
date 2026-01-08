"""
Prompt templates for summary and visualization impact generation
"""
from typing import Dict, List, Any

def build_summary_prompt(
    dataset_summary: Dict[str, Any],
    issues: List[Dict[str, Any]]
) -> str:
    """
    Build prompt for generating summary from detected issues

    Args:
        dataset_summary: Dataset metrics (rows, columns, completeness, etc.)
        issues: List of detected issues with type, severity, title
    """
    # Summarize issues by severity
    critical = [i for i in issues if i.get('severity') == 'critical']
    warnings = [i for i in issues if i.get('severity') == 'warning']
    info = [i for i in issues if i.get('severity') == 'info']

    # Format issue list concisely
    issue_list = []
    for issue in issues[:10]:  # Limit to 10 issues for token efficiency
        issue_list.append(f"- {issue.get('severity', 'info').upper()}: {issue.get('title', 'Unknown')}")

    prompt = f"""Dataset: {dataset_summary.get('row_count', 0):,} rows, {dataset_summary.get('column_count', 0)} cols, {dataset_summary.get('overall_completeness', 100):.0f}% complete

Issues found: {len(critical)} critical, {len(warnings)} warnings, {len(info)} info

{chr(10).join(issue_list) if issue_list else 'No issues detected'}

Generate:
1. "summary": 2-3 sentence overall data quality assessment
2. "visualization_concerns": list of 2-4 specific concerns about how these issues affect charts/graphs

Return JSON only."""

    return prompt

def build_visualization_impact_prompt(
    issue_title: str,
    issue_type: str,
    issue_description: str,
    affected_columns: List[str],
    column_details: Dict[str, Any],
    sample_values: List[Any] = None
) -> str:
    """
    Build prompt for generating dynamic visualization impact explanation

    Args:
        issue_title: Title of the issue
        issue_type: Type of issue (missing_values, outliers, etc.)
        issue_description: Detailed description
        affected_columns: List of affected columns
        column_details: Minimal column context (type, nulls, outliers)
        sample_values: Optional sample values showing the issue
    """
    # Format column context concisely
    col_context = ""
    if column_details:
        col_context = "; ".join([
            f"{col}: {details.get('data_type', 'unknown')} ({details.get('null_percentage', 0):.0f}% null)"
            for col, details in column_details.items()
        ])

    prompt = f"""Issue: {issue_title} ({issue_type})
Detail: {issue_description}
Columns: {', '.join(affected_columns) if affected_columns else 'N/A'} - {col_context}"""

    if sample_values:
        # Show only 3 sample values
        samples = sample_values[:3]
        prompt += f"\nSamples: {samples}"

    prompt += "\n\nExplain in 2 sentences max how this affects visualizations. Be specific and educational."

    return prompt
