"""
Prompt templates for the proactive agent LLM calls.
"""

OBSERVATION_GENERATION_PROMPT = """You are a data analyst generating natural language observations from detected data patterns.

Given the following signal detected in the data, generate a clear, concise observation that a business user would understand.

SIGNAL DETAILS:
- Type: {signal_type}
- Columns involved: {columns}
- Strength: {strength:.2f} (0-1 scale, higher = stronger pattern)
- Additional details:
{metadata_formatted}

DATASET CONTEXT:
- Table name: {table_name}
- Total rows: {row_count}
- Columns: {column_names}

Generate a response in the following JSON format:
{{
    "observation_text": "A clear, specific statement about what this signal means (1-2 sentences)",
    "importance": "high|medium|low",
    "key_insight": "The single most important thing to know about this finding"
}}

Guidelines:
- Be specific with numbers (e.g., "23% increase" not "significant increase")
- Use plain business language, avoid technical jargon
- Focus on what matters for decision-making
- For trends: mention direction, magnitude, and time period
- For outliers: mention how many and how extreme
- For dominance: mention the dominant category and its share
- For seasonality: mention the pattern period
- For imbalance: mention the degree of inequality

Respond with valid JSON only."""


EXPLORATION_CHOICES_PROMPT = """You are a data analyst suggesting follow-up exploration options.

Given the following observation about the data, suggest 2-3 natural follow-up questions or exploration paths.

OBSERVATION:
{observation_text}

SIGNAL DETAILS:
- Type: {signal_type}
- Columns: {columns}
{metadata_formatted}

AVAILABLE COLUMNS IN DATA:
{available_columns}

Generate a response in the following JSON format:
{{
    "choices": [
        {{
            "text": "A natural language question the user might want to answer",
            "intent": "explore_trend|drill_down|compare_periods|investigate|see_distribution|compare_context|see_breakdown|compare_over_time|view_pattern|see_decomposition|compare_distribution|pareto_analysis",
            "suggested_groupby": "column_name or null",
            "suggested_filter": "filter description or null"
        }}
    ]
}}

Guidelines:
- Each choice should lead to actionable insights
- Use natural, conversational language
- Make choices progressively deeper (first surface-level, then detailed)
- Consider what columns could provide useful breakdowns
- Suggest relevant comparisons when applicable

Respond with valid JSON only."""


FOLLOW_UP_PROMPT = """You are a data analyst reviewing query results and suggesting next steps.

The user explored the data with this question: "{choice_text}"

QUERY RESULTS SUMMARY:
- Rows returned: {result_count}
- Columns: {result_columns}
- Sample data:
{sample_data}

ORIGINAL SIGNAL:
- Type: {signal_type}
- Observation: {observation_text}

Based on these results, generate:
1. A brief interpretation of what the results show
2. 2-3 follow-up questions for deeper exploration

Generate a response in the following JSON format:
{{
    "interpretation": "What the results reveal (1-2 sentences)",
    "follow_up_observation": "A new observation based on the results",
    "follow_up_choices": [
        {{
            "text": "A follow-up question",
            "intent": "appropriate_intent",
            "suggested_groupby": "column_name or null",
            "suggested_filter": "filter description or null"
        }}
    ]
}}

Respond with valid JSON only."""


def format_metadata(metadata: dict) -> str:
    """Format metadata dictionary for prompt insertion."""
    lines = []
    for key, value in metadata.items():
        if key == "table_name":
            continue  # Skip table name, shown separately
        if isinstance(value, float):
            lines.append(f"  - {key}: {value:.4f}")
        elif isinstance(value, dict):
            lines.append(f"  - {key}:")
            for k, v in list(value.items())[:5]:  # Limit nested items
                lines.append(f"      {k}: {v}")
        elif isinstance(value, list):
            lines.append(f"  - {key}: {value[:5]}")  # Limit list items
        else:
            lines.append(f"  - {key}: {value}")
    return "\n".join(lines)


def generate_observation_prompt(
    signal_type: str,
    columns: list,
    strength: float,
    metadata: dict,
    table_name: str,
    row_count: int,
    column_names: list
) -> str:
    """Generate prompt for observation creation."""
    return OBSERVATION_GENERATION_PROMPT.format(
        signal_type=signal_type,
        columns=", ".join(columns),
        strength=strength,
        metadata_formatted=format_metadata(metadata),
        table_name=table_name,
        row_count=row_count,
        column_names=", ".join(column_names)
    )


def generate_choices_prompt(
    observation_text: str,
    signal_type: str,
    columns: list,
    metadata: dict,
    available_columns: list
) -> str:
    """Generate prompt for exploration choices."""
    return EXPLORATION_CHOICES_PROMPT.format(
        observation_text=observation_text,
        signal_type=signal_type,
        columns=", ".join(columns),
        metadata_formatted=format_metadata(metadata),
        available_columns=", ".join(available_columns)
    )


def generate_follow_up_prompt(
    choice_text: str,
    result_count: int,
    result_columns: list,
    sample_data: str,
    signal_type: str,
    observation_text: str
) -> str:
    """Generate prompt for follow-up suggestions."""
    return FOLLOW_UP_PROMPT.format(
        choice_text=choice_text,
        result_count=result_count,
        result_columns=", ".join(result_columns),
        sample_data=sample_data,
        signal_type=signal_type,
        observation_text=observation_text
    )
