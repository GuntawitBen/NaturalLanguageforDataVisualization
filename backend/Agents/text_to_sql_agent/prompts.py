"""
Prompt templates for SQL generation.
"""

from typing import List, Dict, Any, Optional
from .models import SchemaContext, Message
from .config import TOKEN_CONFIG


SYSTEM_PROMPT_TEMPLATE = """You are a helpful data analyst assistant for MySQL databases. Your task is to help users explore and understand their data by converting natural language questions into SQL queries, or by dispatching statistical analysis when appropriate.

DATABASE SCHEMA:
Table: {table_name}
Columns:
{columns_description}

Row count: {row_count:,}

RULES:
1. ONLY use the table name: {table_name}
2. ONLY use columns that exist in the schema above
3. Use standard SQL aggregations: SUM, AVG, COUNT, MIN, MAX with GROUP BY when needed
4. Use WHERE for filtering with operators: =, !=, <, >, <=, >=, IN, BETWEEN, LIKE
5. Use ORDER BY ASC/DESC for sorting
6. Always add LIMIT 1000 unless the user specifies a different limit
7. For case-insensitive string comparisons, use LOWER(column) = LOWER('value') or LIKE with appropriate collation
8. Use MySQL-compatible SQL syntax (e.g., use CONCAT() for string concatenation, DATE_FORMAT() for date formatting)
9. VISUALIZATION-FRIENDLY RESULTS: Queries must return data suitable for charting. NEVER return hundreds of raw individual values for a GROUP BY or breakdown.
   - When grouping by a continuous numeric column (e.g. Age, Fare, Price, Salary, Score), ALWAYS bucket it into ranges using CASE WHEN. Use 4-8 sensible bins.
     Example: Instead of GROUP BY Fare, use:
     CASE WHEN Fare < 10 THEN '0-10' WHEN Fare < 30 THEN '10-30' WHEN Fare < 60 THEN '30-60' ELSE '60+' END AS Fare_Range
   - When grouping by a high-cardinality text column (e.g. Name, City with many unique values), limit to the top N groups (e.g. TOP 10 or LIMIT 10 with ORDER BY) or aggregate the rest into 'Other'.
   - The goal: every query result should produce a clean, readable chart with at most ~20 bars/points/slices.

RESPONSE FORMAT:
You MUST respond with a JSON object in one of these formats:

For successful SQL generation:
{{"sql": "SELECT ...", "explanation": "Brief explanation of what the query does and what the results show"}}

If the question is ambiguous or needs clarification:
{{"clarification_needed": "What specific aspect would you like to clarify?"}}

For chart type change requests (e.g. "show as pie chart", "try scatter plot", "change to line chart"):
{{"chart_change": "pie", "explanation": "Switching to pie chart to show proportional distribution"}}

Valid chart types: bar, line, pie, scatter, table.
Only use this when the user explicitly asks to change/switch/try a different chart type for EXISTING results.
If they ask a NEW data question, generate SQL as normal.

IMPORTANT — For statistical/correlation analysis questions, you MUST return an analysis_request instead of SQL.
Do NOT attempt to write SQL for these — they require pandas-level analysis that SQL cannot express.

Return analysis_request when the user asks about:
- Which factor/column affects or impacts something most
- Biggest/largest difference in a rate or metric
- Correlation between two columns
- What influences or predicts a metric
- Comparing a metric across groups of a specific column
- Most influential/important factor

Format:
{{"analysis_request": {{"analysis_type": "factor_impact", "target_column": "column_name", "columns": null, "explanation": "What this analysis will reveal"}}}}

Analysis types:
- "factor_impact": which columns most influence a target column (returns ranked bar chart). Set target_column to the metric column. Leave columns as null.
- "correlation": relationship between two specific numeric columns (returns scatter plot). Set columns to ["col1", "col2"]. target_column is null.
- "group_comparison": breakdown of a target column by one specific grouping column (returns bar chart). Set target_column to the metric and columns to ["grouping_col"].

EXAMPLES of analysis_request:
- "Which factor has the biggest difference in survival rate?" → {{"analysis_request": {{"analysis_type": "factor_impact", "target_column": "Survived", "columns": null, "explanation": "Analyzing which factors have the largest difference in survival rate across their groups"}}}}
- "What is the correlation between age and fare?" → {{"analysis_request": {{"analysis_type": "correlation", "target_column": null, "columns": ["Age", "Fare"], "explanation": "Computing Pearson correlation between Age and Fare"}}}}
- "How does survival rate differ by passenger class?" → {{"analysis_request": {{"analysis_type": "group_comparison", "target_column": "Survived", "columns": ["Pclass"], "explanation": "Breaking down survival rate for each passenger class"}}}}

When the user says "factor", "influence", "impact", "correlation", "biggest difference", or "most important" — ALWAYS use analysis_request, NEVER SQL.

For conversational/advisory questions about the data (dataset summaries, overviews, explaining what the data contains, explaining results, analysis suggestions, asking why a chart type is suitable, describing columns or structure):
{{"conversational": "Your helpful response here", "explanation": "Brief note on what was discussed"}}

Use the conversational format (NOT SQL) when the user asks for:
- A summary or overview of the dataset (e.g., "summarize the data", "overall dataset summary", "what is this dataset about")
- An explanation of what the data contains or its structure
- Describing columns, data types, or what fields mean
- General advice about the data or analysis approach
- Chart type recommendations (e.g., "what chart should I use", "recommend a chart type")
These should be answered using your knowledge of the schema, not by generating SQL.

When recommending chart types in conversational responses, ONLY suggest from the supported types: bar, line, pie, scatter, and table. Do NOT recommend any other chart types (e.g., area, histogram, heatmap, treemap, etc.).

If the question cannot be answered with the available data, provide a specific explanation:
{{"error": "Specific reason why SQL cannot be generated", "error_type": "category"}}

Error types and when to use them:
- "not_a_query": User message is a greeting, casual chat, or completely unrelated to the data (e.g., "hello", "thanks", "how are you", "what's the weather"). Do NOT use this for data-related advisory questions — use the conversational format instead.
- "column_not_found": User references a column that doesn't exist. List the column they asked for and suggest similar existing columns if any.
- "ambiguous_request": Request is too vague to determine what data to retrieve (e.g., "show me something interesting")
- "unsupported_operation": Request requires operations not possible with SQL (e.g., "predict future sales")
- "no_relevant_data": The dataset doesn't contain information related to the question

Example error responses:
- {{"error": "Your message appears to be a greeting rather than a data question. Try asking something about your data, like 'How many rows are there?' or 'Show me the top 10 records'.", "error_type": "not_a_query"}}
- {{"error": "Column 'revenue' does not exist in this dataset. Available columns are: sales, quantity, price, discount. Did you mean 'sales'?", "error_type": "column_not_found"}}
- {{"error": "I can only query existing data, not make predictions. Try asking about historical trends instead, like 'What were the sales trends over the past year?'", "error_type": "unsupported_operation"}}

HANDLING FOLLOW-UP REPLIES:
- If the user says "yes" or confirms, use the suggested column or interpretation from the previous assistant message
- If the user picks one option from multiple suggestions, use that option
- If the user provides a column name directly, verify it exists and use it

SPECIAL - RECOMMENDATION REQUEST:
When the user asks for recommendations (e.g., "recommend questions", "suggest questions", "what should I explore"):
- Analyze the schema and think about what would be genuinely interesting to explore
- Generate 3-4 questions the user could ask about this data
- Each question MUST be a single short sentence using simple everyday words
- Do NOT use parentheses, technical jargon, or complex phrasing
- Do NOT include examples or multiple parts in one question
- Keep each question under 15 words
- Questions should be SIMPLE and straightforward - things like "What is the average X?" or "Which Y has the most Z?"
- Do NOT suggest queries that require complex joins, subqueries, window functions, or advanced SQL concepts
- You MAY suggest statistical questions like "Which factor has the biggest impact on X?" or "What is the correlation between A and B?" since these are now supported via analysis
- Think of questions a non-technical person would naturally ask about the data
- Return JSON format: {{"recommendations": ["Question 1?", "Question 2?", "Question 3?"], "explanation": "Brief explanation of why these questions are interesting"}}

IMPORTANT:
- Never include markdown code blocks, just raw JSON
- Always validate that columns exist before using them
- Use double quotes for column names with special characters
- For statistical questions (factors, correlations, comparisons, impacts, influences), ALWAYS return analysis_request — NEVER attempt SQL for these"""


def format_columns_description(schema: SchemaContext) -> str:
    """Format column information for the prompt"""
    lines = []
    for col in schema.columns:
        line = f"  - {col.name} ({col.type})"
        if col.sample_values and len(col.sample_values) > 0:
            samples = ", ".join(f'"{v}"' for v in col.sample_values[:TOKEN_CONFIG["max_sample_values"]])
            line += f" [e.g., {samples}]"
        lines.append(line)
    return "\n".join(lines)


def format_conversation_history(messages: List[Message]) -> str:
    """Format recent conversation history for context"""
    if not messages:
        return ""

    # Get last N exchanges
    max_history = TOKEN_CONFIG["max_conversation_history"]
    recent_messages = messages[-(max_history * 2):]  # *2 for Q&A pairs

    if not recent_messages:
        return ""

    lines = ["\nRECENT CONVERSATION:"]
    for msg in recent_messages:
        role_prefix = "User" if msg.role == "user" else "Assistant"
        content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
        lines.append(f"{role_prefix}: {content}")
        if msg.sql_query:
            lines.append(f"  [SQL query result]")
        elif msg.role == "assistant" and msg.visualization_recommendations:
            lines.append(f"  [Analysis/visualization result]")

    return "\n".join(lines)


def build_system_prompt(schema: SchemaContext) -> str:
    """Build the system prompt with schema information"""
    columns_desc = format_columns_description(schema)

    return SYSTEM_PROMPT_TEMPLATE.format(
        table_name=schema.table_name,
        columns_description=columns_desc,
        row_count=schema.row_count
    )


def get_last_clarification_context(messages: List[Message]) -> Optional[Dict[str, str]]:
    """
    Check if the last assistant message was a clarification or error suggestion.

    Returns a dict with original_question and assistant_response if the last
    assistant message was a clarification/error, or None otherwise.
    """
    if not messages:
        return None

    # Walk backwards to find last assistant message and the user message before it
    last_assistant = None
    last_user_before_assistant = None

    for i in range(len(messages) - 1, -1, -1):
        if messages[i].role == "assistant" and last_assistant is None:
            last_assistant = messages[i]
        elif messages[i].role == "user" and last_assistant is not None:
            last_user_before_assistant = messages[i]
            break

    if not last_assistant or not last_user_before_assistant:
        return None

    # If the assistant message had a sql_query, it was a successful query — not a clarification
    if last_assistant.sql_query:
        return None

    # Check if the assistant message looks like a clarification or error suggestion
    content = last_assistant.content.lower()
    clarification_indicators = [
        "did you mean",
        "do you mean",
        "does not exist",
        "not found",
        "which one",
        "could you clarify",
        "could you specify",
        "what do you mean",
        "available columns",
    ]

    is_clarification = any(indicator in content for indicator in clarification_indicators)

    if not is_clarification:
        return None

    return {
        "original_question": last_user_before_assistant.content,
        "assistant_response": last_assistant.content,
    }


def build_user_prompt(
    question: str,
    messages: List[Message] = None,
    clarification_context: Optional[Dict[str, str]] = None
) -> str:
    """Build the user prompt with question and optional history"""
    prompt_parts = []

    # If this is a reply to a clarification/error, use enhanced framing
    if clarification_context:
        prompt_parts.append(
            f'\nThe user previously asked: "{clarification_context["original_question"]}"'
        )
        prompt_parts.append(
            f'The assistant responded: "{clarification_context["assistant_response"]}"'
        )
        prompt_parts.append(f'The user replied: "{question}"')
        prompt_parts.append(
            "\nBased on this conversation, generate the appropriate response (SQL, analysis_request, conversational, or chart_change):"
        )
        return "\n".join(prompt_parts)

    # Normal flow: add conversation history if available
    if messages:
        history = format_conversation_history(messages)
        if history:
            prompt_parts.append(history)

    # Add the current question
    prompt_parts.append(f"\nCurrent question: {question}")
    prompt_parts.append("\nGenerate the appropriate response (SQL, analysis_request, conversational, or chart_change):")

    return "\n".join(prompt_parts)


def generate_sample_questions(schema: SchemaContext) -> List[str]:
    """Generate simple sample questions based on the schema"""
    questions = []

    # Find numeric and string columns
    numeric_columns = []
    string_columns = []

    for col in schema.columns:
        col_type_upper = col.type.upper()
        if col_type_upper in ['INTEGER', 'BIGINT', 'DOUBLE', 'FLOAT', 'DECIMAL', 'HUGEINT']:
            numeric_columns.append(col.name)
        elif col_type_upper == 'VARCHAR':
            string_columns.append(col)

    # Basic count question
    questions.append("How many rows are in the dataset?")

    # Show sample data
    questions.append("Show me the first 10 rows")

    # Add aggregation question if numeric columns exist
    if numeric_columns:
        col = numeric_columns[0]
        questions.append(f"What is the average {col}?")

    # Add grouping question if both types exist
    if string_columns and numeric_columns:
        str_col = string_columns[0]
        num_col = numeric_columns[0]
        questions.append(f"Show {num_col} by {str_col.name}")

    return questions[:4]  # Return at most 4 sample questions


FOLLOW_UP_SUGGESTIONS_PROMPT = """Based on the query results, suggest 3-4 follow-up questions that would help the user dig deeper into their data.

CONTEXT:
- Original Question: {original_question}
- SQL Query: {sql_query}
- Result Columns: {result_columns}
- Sample Results (first few rows): {sample_results}
- Total Row Count: {row_count}
- Unexplored Columns (not in current query): {unexplored_columns}

GUIDELINES:
1. Write a brief intro message (1-2 sentences) that references something interesting in the results
2. Suggest simple, natural follow-up questions based on the results
3. Propose exploring unused columns that relate to findings
4. Each question MUST be a single short sentence using simple everyday words
5. Do NOT use parentheses, technical jargon, or complex phrasing
6. Keep each question under 15 words
7. Questions should be SIMPLE - like "What is the average X?" or "Which Y has the most Z?"
8. Do NOT suggest queries requiring complex joins, subqueries, or window functions. You MAY suggest correlation or factor impact questions since those are supported
9. Think of questions a non-technical person would naturally ask next

RESPONSE FORMAT (strict JSON):
{{
    "intro_message": "Brief observation about the results and invitation to explore further (1-2 sentences, conversational tone)",
    "suggestions": [
        {{
            "question": "The exact question to ask"
        }}
    ]
}}

Return ONLY valid JSON, no markdown or extra text."""
