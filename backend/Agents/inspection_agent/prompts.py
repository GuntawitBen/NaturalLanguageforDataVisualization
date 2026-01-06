"""
Prompt templates for OpenAI GPT-4 analysis
"""
from typing import Dict, List, Any
import json

def build_system_prompt() -> str:
    """
    System prompt that defines GPT-4's role and output format
    """
    return """You are an expert data quality analyst specializing in exploratory data analysis (EDA) for data visualization projects.

Your role is to analyze CSV datasets and identify data quality issues that could impact visualization and analysis. Focus on issues that would affect:
- Chart readability and accuracy
- Statistical validity
- User interpretation
- Performance and rendering

**Analysis Guidelines:**
1. Be specific about which columns are affected
2. Quantify issues with percentages and counts when possible
3. Prioritize issues by impact on visualization
4. Provide actionable recommendations
5. Consider the visualization use case

**Output Format:**
You must respond with a valid JSON object with this structure:
{
  "summary": "2-3 sentence overall assessment of data quality",
  "visualization_concerns": [
    "Specific concern 1 about visualization",
    "Specific concern 2 about visualization"
  ],
  "additional_issues": [
    {
      "type": "issue_type",
      "severity": "critical|warning|info",
      "title": "Brief title",
      "description": "Detailed description",
      "affected_columns": ["col1", "col2"],
      "recommendation": "What to do about it",
      "visualization_impact": "Educational explanation of what this issue is and how it will affect visualizations. Explain the concept clearly and describe the specific impact on charts, graphs, and visual representations."
    }
  ]
}

**Severity Guidelines:**
- CRITICAL: Issues that prevent meaningful visualization or analysis
- WARNING: Issues that may mislead or reduce visualization quality
- INFO: Minor issues or observations worth noting

Be concise but thorough. Focus on actionable insights."""

def build_user_prompt(
    dataset_summary: Dict[str, Any],
    column_statistics: List[Dict[str, Any]],
    sample_rows: List[Dict[str, Any]],
    detected_issues_summary: Dict[str, Any]
) -> str:
    """
    Build user prompt with dataset information

    Args:
        dataset_summary: High-level dataset metrics
        column_statistics: Per-column statistics
        sample_rows: Sample data rows
        detected_issues_summary: Summary of programmatically detected issues
    """

    # Format column statistics for readability
    column_summary = []
    for col_stat in column_statistics:
        col_info = f"- {col_stat['column_name']} ({col_stat['data_type']}): "
        col_info += f"{col_stat['unique_count']} unique values, "
        col_info += f"{col_stat['null_percentage']:.1f}% missing"

        if col_stat.get('has_outliers'):
            col_info += f", {col_stat['outlier_count']} outliers detected"
        if col_stat.get('is_high_cardinality'):
            col_info += ", HIGH CARDINALITY"

        column_summary.append(col_info)

    prompt = f"""Analyze this CSV dataset for data quality issues that could impact visualization:

**Dataset Overview:**
- Total Rows: {dataset_summary['row_count']:,}
- Total Columns: {dataset_summary['column_count']}
- Overall Completeness: {dataset_summary['overall_completeness']:.1f}%
- Duplicate Rows: {dataset_summary['duplicate_row_count']} ({dataset_summary['duplicate_row_percentage']:.1f}%)
- Memory Usage: {dataset_summary.get('memory_usage_mb', 0):.2f} MB

**Column Details:**
{chr(10).join(column_summary)}

**Programmatically Detected Issues:**
- Missing Values: {detected_issues_summary['missing_values_count']} columns affected
- Outliers: {detected_issues_summary['outliers_count']} columns with outliers
- High Cardinality: {detected_issues_summary['high_cardinality_count']} columns
- Duplicate Rows: {detected_issues_summary['duplicate_rows']}

**Sample Data (first {len(sample_rows)} rows):**
```json
{json.dumps(sample_rows, indent=2)}
```

Based on this information, provide your analysis focusing on:
1. Issues not captured by basic statistics
2. Patterns in the sample data that could cause visualization problems
3. Data type mismatches or format inconsistencies
4. Relationships between columns that could cause confusion
5. Recommendations for data cleaning before visualization

Remember to return a valid JSON object as specified in your instructions."""

    return prompt

def build_fallback_summary(detected_issues_count: int) -> str:
    """
    Generate a fallback summary if GPT-4 API fails
    """
    if detected_issues_count == 0:
        return "Automated analysis detected no major data quality issues. The dataset appears ready for visualization."
    elif detected_issues_count <= 3:
        return f"Automated analysis detected {detected_issues_count} data quality issues that should be addressed before visualization."
    else:
        return f"Automated analysis detected {detected_issues_count} data quality issues. Review each issue carefully before proceeding with visualization."

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
        column_details: Statistics and details about affected columns
        sample_values: Optional sample values showing the issue
    """
    prompt = f"""You are a data visualization expert. Generate a clear, educational explanation of how this specific data quality issue will affect data visualizations.

**Issue Details:**
- Title: {issue_title}
- Type: {issue_type}
- Description: {issue_description}
- Affected Columns: {', '.join(affected_columns) if affected_columns else 'N/A'}

**Column Context:**
{json.dumps(column_details, indent=2)}
"""

    if sample_values:
        prompt += f"""
**Sample Values Showing Issue:**
{json.dumps(sample_values[:10], indent=2)}
"""

    prompt += """
**Task:**
Generate a 2-3 sentence explanation that:
1. Explains what this issue is in simple terms
2. Describes the SPECIFIC impact on visualizations (charts, graphs, plots)
3. Uses concrete examples relevant to this data

Focus on the visualization impact, not recommendations. Be educational and specific to this situation.

Return ONLY the explanation text, no JSON, no extra formatting."""

    return prompt
