"""
Pydantic models for the Text-to-SQL agent.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime


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
    timestamp: datetime = None

    def __init__(self, **data):
        if data.get('timestamp') is None:
            data['timestamp'] = datetime.now()
        super().__init__(**data)


class SessionState(BaseModel):
    """State of a text-to-SQL session"""
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
    session_id: str
    schema: SchemaContext
    sample_questions: List[str]


class ChatRequest(BaseModel):
    """Request to send a chat message"""
    session_id: str
    message: str


class ChatResponse(BaseModel):
    """Response from a chat message"""
    status: str  # "success", "error", "clarification_needed"
    message: str
    sql_query: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None
    columns: Optional[List[str]] = None
    row_count: Optional[int] = None
    error_details: Optional[str] = None


class GPTSQLResponse(BaseModel):
    """Parsed response from GPT for SQL generation"""
    sql: Optional[str] = None
    explanation: Optional[str] = None
    clarification_needed: Optional[str] = None
    error: Optional[str] = None
