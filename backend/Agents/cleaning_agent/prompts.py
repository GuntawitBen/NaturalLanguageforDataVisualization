"""
Prompt templates for GPT-4 interactions.
"""

from typing import List, Dict, Any
import json


SYSTEM_PROMPT = """You are a data cleaning expert helping users understand the trade-offs of different data cleaning approaches.

Your role is to:
1. Analyze the specific data quality problem
2. Evaluate each proposed cleaning option
3. Provide clear, specific advantages and disadvantages
4. Consider the impact on data visualization and analysis
5. Be honest about potential risks and limitations

Keep your explanations concise (2-3 sentences each) and focused on practical implications."""


def generate_pros_cons_prompt(
    problem_type: str,
    problem_title: str,
    problem_description: str,
    affected_columns: List[str],
    options: List[Dict[str, Any]],
    column_stats: Dict[str, Any] = None
) -> str:
    """
    Generate a prompt for GPT-4 to analyze cleaning options.

    Args:
        problem_type: Type of problem (missing_values, outliers, etc.)
        problem_title: Title of the problem
        problem_description: Detailed description
        affected_columns: List of affected column names
        options: List of cleaning options with their details
        column_stats: Optional statistics about the columns

    Returns:
        Formatted prompt string
    """
    # Format options list
    options_text = []
    for i, option in enumerate(options, 1):
        options_text.append(
            f"{i}. **{option['name']}** ({option['operation_type']})\n"
            f"   Description: {option['description']}"
        )

    options_str = "\n\n".join(options_text)

    # Format column stats if provided
    stats_str = ""
    if column_stats:
        stats_str = f"\n\n**Column Statistics:**\n```json\n{json.dumps(column_stats, indent=2)}\n```"

    prompt = f"""# Data Quality Problem

**Type:** {problem_type}
**Problem:** {problem_title}
**Description:** {problem_description}
**Affected Columns:** {', '.join(affected_columns) if affected_columns else 'All columns'}{stats_str}

# Cleaning Options

{options_str}

# Your Task

For EACH cleaning option above, provide:

1. **pros**: 2-3 sentences describing the advantages of this approach, specific to this data and problem
2. **cons**: 2-3 sentences describing the disadvantages, risks, or trade-offs of this approach
3. **impact_estimate**: Estimated metrics like rows_affected, data_loss_percentage, or other relevant numbers

Consider:
- How this will affect data visualization (charts, graphs, distributions)
- Impact on statistical analysis and insights
- Data integrity and potential bias introduction
- Practical implications for the user's workflow

Return your response in the following JSON format:

```json
{{
  "options": [
    {{
      "option_number": 1,
      "pros": "Clear explanation of advantages...",
      "cons": "Clear explanation of disadvantages...",
      "impact_estimate": {{
        "rows_affected": <number or null>,
        "data_loss_percentage": <number or null>,
        "notes": "<any additional impact notes>"
      }}
    }},
    {{
      "option_number": 2,
      "pros": "...",
      "cons": "...",
      "impact_estimate": {{...}}
    }}
  ]
}}
```

Be specific, honest, and focus on practical implications. Avoid generic statements."""

    return prompt


def generate_session_summary_prompt(
    dataset_name: str,
    initial_stats: Dict[str, int],
    final_stats: Dict[str, int],
    operations_applied: List[str]
) -> str:
    """
    Generate a prompt for summarizing the cleaning session.

    Args:
        dataset_name: Name of the dataset
        initial_stats: Initial dataset statistics
        final_stats: Final dataset statistics
        operations_applied: List of operations that were applied

    Returns:
        Formatted prompt string
    """
    prompt = f"""# Data Cleaning Session Summary

**Dataset:** {dataset_name}

**Initial State:**
- Rows: {initial_stats.get('row_count', 'N/A')}
- Columns: {initial_stats.get('column_count', 'N/A')}
- Missing Values: {initial_stats.get('missing_value_count', 'N/A')}
- Duplicate Rows: {initial_stats.get('duplicate_row_count', 'N/A')}
- Outliers: {initial_stats.get('outlier_count', 'N/A')}

**Final State:**
- Rows: {final_stats.get('row_count', 'N/A')}
- Columns: {final_stats.get('column_count', 'N/A')}
- Missing Values: {final_stats.get('missing_value_count', 'N/A')}
- Duplicate Rows: {final_stats.get('duplicate_row_count', 'N/A')}
- Outliers: {final_stats.get('outlier_count', 'N/A')}

**Operations Applied:**
{chr(10).join(f'- {op}' for op in operations_applied)}

Please provide a brief summary (3-4 sentences) of the cleaning session, highlighting:
1. The main data quality issues that were addressed
2. The overall impact on the dataset
3. Any important considerations for the user going forward

Keep it concise and user-friendly."""

    return prompt


def generate_visualization_impact_prompt(
    problem_type: str,
    problem_description: str,
    affected_columns: List[str]
) -> str:
    """
    Generate a prompt for explaining visualization impact.

    Args:
        problem_type: Type of problem
        problem_description: Description of the problem
        affected_columns: Affected columns

    Returns:
        Formatted prompt string
    """
    prompt = f"""Explain in 1-2 sentences how this data quality problem will specifically affect data visualizations:

**Problem Type:** {problem_type}
**Description:** {problem_description}
**Affected Columns:** {', '.join(affected_columns) if affected_columns else 'All columns'}

Focus on:
- How charts and graphs will be impacted
- What visual distortions or misleading patterns might appear
- How this affects the ability to see meaningful insights

Keep it concise and specific to visualization impact only."""

    return prompt


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
        options_text.append(f"### Option {i}: {option.get('option_name', 'Unknown')}")

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
  "recommended_option_id": "exact-option-id-from-options-list",
  "reason": "One concise sentence explaining why this option is best for THIS specific situation. Reference the actual metrics."
}}

Be specific and data-driven in your reasoning."""

    return prompt
