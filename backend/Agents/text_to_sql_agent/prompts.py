"""
Prompt templates for SQL generation.
"""

from typing import List, Dict, Any
from .models import SchemaContext, Message
from .config import TOKEN_CONFIG


SYSTEM_PROMPT_TEMPLATE = """You are a helpful data analyst assistant for MySQL databases. Your task is to help users explore and understand their data by converting natural language questions into SQL queries.

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

RESPONSE FORMAT:
You MUST respond with a JSON object in one of these formats:

For successful SQL generation:
{{"sql": "SELECT ...", "explanation": "Brief explanation of what the query does and what the results show"}}

If the question is ambiguous or needs clarification:
{{"clarification_needed": "What specific aspect would you like to clarify?"}}

If the question cannot be answered with the available data, provide a specific explanation:
{{"error": "Specific reason why SQL cannot be generated", "error_type": "category"}}

Error types and when to use them:
- "not_a_query": User message is a greeting, casual chat, or not a data question (e.g., "hello", "thanks", "how are you")
- "column_not_found": User references a column that doesn't exist. List the column they asked for and suggest similar existing columns if any.
- "ambiguous_request": Request is too vague to determine what data to retrieve (e.g., "show me something interesting")
- "unsupported_operation": Request requires operations not possible with SQL (e.g., "predict future sales", "why did sales drop")
- "no_relevant_data": The dataset doesn't contain information related to the question

Example error responses:
- {{"error": "Your message appears to be a greeting rather than a data question. Try asking something about your data, like 'How many rows are there?' or 'Show me the top 10 records'.", "error_type": "not_a_query"}}
- {{"error": "Column 'revenue' does not exist in this dataset. Available columns are: sales, quantity, price, discount. Did you mean 'sales'?", "error_type": "column_not_found"}}
- {{"error": "I can only query existing data, not make predictions. Try asking about historical trends instead, like 'What were the sales trends over the past year?'", "error_type": "unsupported_operation"}}

SPECIAL - RECOMMENDATION REQUEST:
When the user asks for recommendations (e.g., "recommend questions", "suggest questions", "what should I explore"):
- Analyze the schema and think about what would be genuinely interesting to explore
- Generate 3-4 specific, actionable questions the user could ask about this data
- Focus on questions that reveal insights: distributions, top/bottom values, correlations, trends, outliers
- Return JSON format: {{"recommendations": ["Question 1?", "Question 2?", "Question 3?"], "explanation": "Brief explanation of why these questions are interesting"}}

IMPORTANT:
- Never include markdown code blocks, just raw JSON
- Always validate that columns exist before using them
- Use double quotes for column names with special characters"""


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
            lines.append(f"  SQL: {msg.sql_query}")

    return "\n".join(lines)


def build_system_prompt(schema: SchemaContext) -> str:
    """Build the system prompt with schema information"""
    columns_desc = format_columns_description(schema)

    return SYSTEM_PROMPT_TEMPLATE.format(
        table_name=schema.table_name,
        columns_description=columns_desc,
        row_count=schema.row_count
    )


def build_user_prompt(
    question: str,
    messages: List[Message] = None
) -> str:
    """Build the user prompt with question and optional history"""
    prompt_parts = []

    # Add conversation history if available
    if messages:
        history = format_conversation_history(messages)
        if history:
            prompt_parts.append(history)

    # Add the current question
    prompt_parts.append(f"\nCurrent question: {question}")
    prompt_parts.append("\nGenerate the SQL query:")

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
2. Dig deeper into interesting patterns from the current results
3. Suggest comparisons or breakdowns not in the original query
4. Propose exploring unused columns that relate to findings
5. Consider trends, outliers, or correlations worth investigating

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
