"""
Pydantic models for the Text-to-SQL agent.
"""

import warnings
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, ConfigDict
from datetime import datetime

# Suppress Pydantic warning about "schema" field name shadowing BaseModel attribute
# This is safe - we intentionally use "schema" for API compatibility
warnings.filterwarnings(
    "ignore",
    message='Field name "schema" in .* shadows an attribute in parent "BaseModel"'
)


class ColumnInfo(BaseModel):
    """Information about a column in the schema"""
    name: str
    type: str
    sample_values: Optional[List[str]] = None  # Only for VARCHAR columns


class SchemaContext(BaseModel):
    """Context about the dataset schema for SQL generation"""
    table_name: str
    columns: List[ColumnInfo]
    row_count: int


class Message(BaseModel):
    """A message in the conversation history"""
    role: str  # "user" or "assistant"
    content: str
    sql_query: Optional[str] = None
    # Can be either:
    # - List[Dict] for chart recommendations (chart_type, x_axis, y_axis, etc.)
    # - Dict with 'recommendations' key for text recommendations (intro suggestions)
    visualization_recommendations: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None
    timestamp: datetime = None

    def __init__(self, **data):
        if data.get('timestamp') is None:
            data['timestamp'] = datetime.now()
        super().__init__(**data)


class SessionState(BaseModel):
    """State of a text-to-SQL session"""
    model_config = ConfigDict(protected_namespaces=())

    session_id: str
    dataset_id: str
    schema: SchemaContext
    messages: List[Message]
    created_at: datetime
    last_activity: datetime


# Request/Response Models for API

class StartSessionRequest(BaseModel):
    """Request to start a text-to-SQL session"""
    dataset_id: str


class StartSessionResponse(BaseModel):
    """Response when starting a text-to-SQL session"""
    model_config = ConfigDict(protected_namespaces=())

    session_id: str
    schema: SchemaContext
    sample_questions: List[str]
    intro_message: Optional[str] = None  # Conversational intro about the dataset


class ChatRequest(BaseModel):
    """Request to send a chat message"""
    session_id: str
    message: str


class ChatResponse(BaseModel):
    """Response from a chat message"""
    status: str  # "success", "error", "clarification_needed", "recommendations"
    message: str
    sql_query: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None
    columns: Optional[List[str]] = None
    row_count: Optional[int] = None
    error_details: Optional[str] = None
    recommendations: Optional[List[str]] = None  # List of recommended questions
    visualization_recommendations: Optional[List[Dict[str, Any]]] = None  # Chart recommendations


class GPTSQLResponse(BaseModel):
    """Parsed response from GPT for SQL generation"""
    sql: Optional[str] = None
    explanation: Optional[str] = None
    clarification_needed: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None  # Category: not_a_query, column_not_found, ambiguous_request, etc.
    recommendations: Optional[List[str]] = None  # List of recommended questions
    conversational: Optional[str] = None  # Free-form conversational response
    chart_change: Optional[str] = None  # Desired chart type: bar, line, pie, scatter, area, histogram
