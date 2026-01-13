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
1. Dataset size ({dataset.get('total_rows', 'N/A')} rows) - impact of data loss
2. Specific metrics (e.g., null_percentage, outlier_count, etc. from the metadata above)
3. Trade-offs between data quality and data preservation

Return ONLY valid JSON (no markdown):
{{
  "recommended_option_id": "<the exact ID value from the option you recommend, e.g., xxx-opt-1>",
  "reason": "Two concise sentence explaining why this option is best for THIS specific situation. Reference the actual metrics."
}}

IMPORTANT: Use the exact ID string shown after "ID:" for each option, NOT "Option 1" or similar.

Be specific for this specific problem in this dataset, don't just say how this approach is good but explain why in this specific dataset"""

    return prompt