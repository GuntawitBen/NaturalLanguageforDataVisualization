"""
Text-to-SQL Agent package.
Converts natural language questions into SQL queries and executes them.
"""

from .models import (
    SchemaContext,
    ColumnInfo,
    Message,
    ChatRequest,
    ChatResponse,
    StartSessionRequest,
    StartSessionResponse,
    SessionState,
)
from .agent import TextToSQLAgent, text_to_sql_agent
from .sql_validator import (
    SQLValidator,
    ValidationResult,
    ValidationError,
    create_validator,
)

__all__ = [
    "TextToSQLAgent",
    "text_to_sql_agent",
    "SchemaContext",
    "ColumnInfo",
    "Message",
    "ChatRequest",
    "ChatResponse",
    "StartSessionRequest",
    "StartSessionResponse",
    "SessionState",
    "SQLValidator",
    "ValidationResult",
    "ValidationError",
    "create_validator",
]
