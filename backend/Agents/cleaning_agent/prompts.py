"""
Prompt templates for GPT cleaning recommendation.
"""

from typing import Dict, Any
import json


def generate_recommendation_prompt(context: Dict[str, Any]) -> str:
    """
    Generate prompt for GPT to recommend the best cleaning option.

    Args:
        context: Dictionary containing dataset, problem, and options info

    Returns:
        Formatted prompt string
    """
    dataset = context.get("dataset", {})
    problem = context.get("problem", {})
    options = context.get("options", [])

    # Format options list
    options_text = []
    for i, option in enumerate(options, 1):
        options_text.append(f"### Option {i}: {option.get('option_name', 'Unknown')}\n- ID: `{option.get('option_id', '')}`")

    options_str = "\n".join(options_text)

    # Format metadata
    metadata = problem.get("metadata", {})
    metadata_str = json.dumps(metadata, indent=2)

    prompt = f"""# Data Cleaning Recommendation Request

## Dataset Context
- Dataset: {dataset.get('name', 'Unknown')}
- Total Rows: {dataset.get('total_rows', 'N/A')}
- Total Columns: {dataset.get('total_columns', 'N/A')}

## Problem Details
- Type: {problem.get('type', 'Unknown')}
- Issue: {problem.get('title', 'Unknown')}
- Description: {problem.get('description', 'No description')}
- Affected Columns: {', '.join(problem.get('affected_columns', [])) if problem.get('affected_columns') else 'None'}
- Metrics: {metadata_str}

## Available Options

{options_str}

## Your Task

Based on the dataset size and the specific problem metrics, recommend which option is BEST for this specific situation.

Consider:
1. **PRIORITY ORDER**: Format inconsistencies should be fixed FIRST before other issues
   - Format standardization improves accuracy of missing value and outlier detection
   - Example: "N/A" in date columns won't be detected as missing until format is standardized
   - Numeric strings like "$1,234" can't be analyzed for outliers until format is cleaned
2. Dataset size ({dataset.get('total_rows', 'N/A')} rows) - impact of data loss
3. Specific metrics (e.g., null_percentage, outlier_count, etc. from the metadata above)
4. Trade-offs between data quality and data preservation
5. **DOMAIN ANALYSIS (CRITICAL for outliers)**: Look at the "example_outliers" in metadata and analyze if these values make sense:
   - Check the column name to understand what it represents (Age, Salary, Price, Height, etc.)
   - Look at the actual example_outliers values - are they realistic for this domain?
   - For "Age": values like 85, 90, 95 are valid elderly ages - NOT errors to remove
   - For "Salary/Income": high values ($200k+) may be executives - could be legitimate
   - For "Price": extreme values might be luxury items or bulk orders
   - For measurements: consider realistic ranges (human height 4-7 feet, weight 80-400 lbs)
   - If the example_outliers appear to be REAL VALID VALUES, recommend "Keep outliers" option
   - Only recommend removing if values are clearly impossible (Age=200, negative prices, etc.)
6. **FORMAT INCONSISTENCY (for date/boolean/case problems)**:
   - For DATES: Look at "detected_formats" and "format_examples" in metadata
     * Recommend "YYYY-MM-DD" (ISO format) for databases, APIs, or technical datasets
     * Recommend "DD/MM/YYYY" or "MM/DD/YYYY" based on regional context (check existing data)
     * Recommend "Month DD, YYYY" for human-readable reports
   - For BOOLEANS: Look at the detected formats
     * Recommend "True/False" for programming/technical datasets
     * Recommend "Yes/No" for human-readable surveys or forms
     * Recommend "1/0" for numeric analysis or database storage
   - For TEXT CASE: Consider the column context
     * Recommend "Title Case" for names, titles, categories
     * Recommend "UPPERCASE" for codes, IDs, abbreviations
     * Recommend "lowercase" for emails, usernames, URLs
   - Reference the "format_examples" to explain why your recommendation fits the data

Return ONLY valid JSON (no markdown):
{{
  "recommended_option_id": "<the exact ID value from the option you recommend, e.g., xxx-opt-1>",
  "reason": "Two concise sentences explaining why this option is best. For outliers, explain whether they appear to be valid domain values or errors. Reference actual metrics."
}}

IMPORTANT: Use the exact ID string shown after "ID:" for each option, NOT "Option 1" or similar.

Be specific for this specific problem in this dataset, don't just say how this approach is good but explain why in this specific dataset"""

    return prompt