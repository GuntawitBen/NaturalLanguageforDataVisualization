# Text-to-SQL Agent Documentation

## Overview

The Text-to-SQL Agent is a conversational AI system that converts natural language questions into SQL queries and executes them against user datasets stored in DuckDB. It provides an intuitive chat interface for data exploration without requiring SQL knowledge.

---

## Table of Contents

1. [Architecture](#architecture)
2. [File Structure](#file-structure)
3. [Core Components](#core-components)
4. [API Endpoints](#api-endpoints)
5. [Conversation Flow](#conversation-flow)
6. [Configuration](#configuration)
7. [Error Handling](#error-handling)
8. [Token Optimization](#token-optimization)
9. [Usage Examples](#usage-examples)
10. [Integration Guide](#integration-guide)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Frontend (React)                                │
│                         Chat UI / Question Input                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Routes                                     │
│                      /agents/text-to-sql/*                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TextToSQLAgent                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ OpenAI       │  │ Session      │  │ Prompt       │  │ Schema       │     │
│  │ Client       │  │ Manager      │  │ Builder      │  │ Context      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
           ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
           │   GPT-4o     │  │   DuckDB     │  │   Dataset    │
           │   API        │  │   Database   │  │   Metadata   │
           └──────────────┘  └──────────────┘  └──────────────┘
```

---

## File Structure

```
backend/Agents/text_to_sql_agent/
├── __init__.py          # Package exports and public API
├── config.py            # Configuration constants
├── models.py            # Pydantic data models
├── prompts.py           # GPT prompt templates
├── openai_client.py     # OpenAI API integration
├── state_manager.py     # Session management
├── agent.py             # Main orchestrator
└── README.md            # This documentation

backend/routes/
└── text_to_sql.py       # FastAPI endpoint definitions
```

---

## Core Components

### 1. Models (`models.py`)

Defines all data structures used throughout the agent.

#### `ColumnInfo`
Information about a single column in the dataset schema.

```python
class ColumnInfo(BaseModel):
    name: str                              # Column name
    type: str                              # Data type (VARCHAR, INTEGER, etc.)
    sample_values: Optional[List[str]]     # Sample values (VARCHAR only)
```

#### `SchemaContext`
Complete schema information passed to GPT for SQL generation.

```python
class SchemaContext(BaseModel):
    table_name: str           # DuckDB table name (e.g., "user_data_abc123")
    columns: List[ColumnInfo] # List of all columns
    row_count: int            # Total rows in dataset
```

#### `Message`
A single message in the conversation history.

```python
class Message(BaseModel):
    role: str                    # "user" or "assistant"
    content: str                 # Message text
    sql_query: Optional[str]     # SQL query (if generated)
    timestamp: datetime          # When message was created
```

#### `SessionState`
Complete state of an active chat session.

```python
class SessionState(BaseModel):
    session_id: str              # Unique session identifier
    dataset_id: str              # Associated dataset
    schema: SchemaContext        # Cached schema information
    messages: List[Message]      # Conversation history
    created_at: datetime         # Session creation time
    last_activity: datetime      # Last interaction time
```

#### `ChatRequest` / `ChatResponse`
API request and response models.

```python
class ChatRequest(BaseModel):
    session_id: str    # Active session ID
    message: str       # User's natural language question

class ChatResponse(BaseModel):
    status: str                              # "success", "error", "clarification_needed"
    message: str                             # Response message
    sql_query: Optional[str]                 # Generated SQL
    results: Optional[List[Dict[str, Any]]]  # Query results as list of dicts
    columns: Optional[List[str]]             # Column names
    row_count: Optional[int]                 # Number of rows returned
    error_details: Optional[str]             # Error information (if any)
```

---

### 2. Configuration (`config.py`)

Central configuration for all agent settings.

#### OpenAI Settings
```python
OPENAI_CONFIG = {
    "model": "gpt-4o",        # Model to use
    "temperature": 0.3,       # Low for consistent SQL
    "max_tokens": 500,        # SQL queries are short
    "timeout": 15,            # Request timeout (seconds)
}
```

#### SQL Settings
```python
SQL_CONFIG = {
    "max_retries": 1,           # Retry once on SQL error
    "default_row_limit": 1000,  # Default LIMIT clause
    "max_row_limit": 10000,     # Maximum allowed LIMIT
}
```

#### Token Optimization
```python
TOKEN_CONFIG = {
    "max_sample_values": 3,         # Sample values per VARCHAR column
    "max_conversation_history": 3,  # Q&A pairs to keep in context
    "max_column_name_length": 50,   # Truncate long column names
}
```

#### Session Settings
```python
SESSION_CONFIG = {
    "session_timeout_seconds": 3600,  # 1 hour timeout
    "max_messages_per_session": 10,   # Message history limit
    "cleanup_interval_seconds": 300,  # Cleanup every 5 minutes
}
```

---

### 3. Prompts (`prompts.py`)

Handles prompt construction for GPT-4o.

#### System Prompt Structure
The system prompt provides GPT with:
- Database schema (table name, columns, types)
- Sample values for categorical columns
- SQL generation rules (DuckDB syntax)
- Response format requirements (JSON)

```
You are a SQL query generator for DuckDB databases.

DATABASE SCHEMA:
Table: user_data_abc123
Columns:
  - id (INTEGER)
  - name (VARCHAR) [e.g., "John", "Jane", "Bob"]
  - amount (DOUBLE)
  - category (VARCHAR) [e.g., "Electronics", "Clothing"]

Row count: 10,000

RULES:
1. ONLY use the table name: user_data_abc123
2. ONLY use columns that exist in the schema above
3. Use standard SQL aggregations: SUM, AVG, COUNT, MIN, MAX
4. Always add LIMIT 1000 unless specified
...

RESPONSE FORMAT:
{"sql": "SELECT ...", "explanation": "..."}
```

#### User Prompt Structure
Includes conversation history for context:
```
RECENT CONVERSATION:
User: How many rows are there?
Assistant: There are 10,000 rows in the dataset.
  SQL: SELECT COUNT(*) FROM user_data_abc123

Current question: What is the average amount by category?
Generate the SQL query:
```

#### Sample Question Generation
Automatically generates relevant questions based on schema:
```python
def generate_sample_questions(schema: SchemaContext) -> List[str]:
    # Analyzes column types to suggest:
    # - Count queries
    # - Aggregation queries (for numeric columns)
    # - Group by queries (for categorical + numeric)
    # - Filter queries (using sample values)
```

---

### 4. OpenAI Client (`openai_client.py`)

Handles all GPT-4o API interactions.

#### Key Methods

**`generate_sql(question, schema, messages)`**
Main SQL generation method:
1. Builds system prompt with schema
2. Builds user prompt with history + question
3. Calls GPT-4o API
4. Parses JSON response
5. Returns `GPTSQLResponse`

**`fix_sql_error(original_sql, error_message, schema)`**
Error recovery method:
1. Sends failed SQL + error to GPT
2. Asks GPT to fix the query
3. Returns corrected SQL

**`_call_with_retry(func, *args, **kwargs)`**
Retry logic with exponential backoff:
- Handles `RateLimitError`
- Parses retry-after from error message
- Exponential backoff: 2s → 4s → 8s
- Maximum 3 retries

#### Response Parsing
Handles multiple response formats:
```python
def _parse_gpt_response(content: str) -> GPTSQLResponse:
    # 1. Try JSON parsing
    # 2. Handle markdown code blocks
    # 3. Extract SQL from plain text (fallback)
```

---

### 5. State Manager (`state_manager.py`)

Thread-safe session management.

#### SessionManager Class

**`create_session(dataset_id, schema)`**
- Generates unique session ID
- Caches schema context
- Initializes empty message history

**`get_session(session_id)`**
- Returns session if exists and not expired
- Automatically removes expired sessions

**`add_message(session_id, role, content, sql_query)`**
- Appends message to history
- Trims history if exceeding limit (10 messages)
- Updates last activity timestamp

**`cleanup_expired_sessions()`**
- Removes sessions older than timeout (1 hour)
- Called periodically or manually

#### Schema Building
```python
def build_schema_context(dataset_id: str) -> SchemaContext:
    # 1. Get dataset metadata from db_utils
    # 2. Query sample values for VARCHAR columns
    # 3. Build SchemaContext object
```

---

### 6. Agent Orchestrator (`agent.py`)

Main entry point coordinating all components.

#### `TextToSQLAgent` Class

**`start_session(dataset_id)`**
```python
def start_session(self, dataset_id: str) -> StartSessionResponse:
    # 1. Verify dataset exists
    # 2. Build schema context
    # 3. Create session
    # 4. Generate sample questions
    # 5. Return session info
```

**`chat(session_id, message)`**
```python
def chat(self, session_id: str, message: str) -> ChatResponse:
    # 1. Validate session
    # 2. Get conversation history
    # 3. Generate SQL via OpenAI
    # 4. Handle clarification requests
    # 5. Execute SQL on DuckDB
    # 6. Handle errors with retry
    # 7. Format and return results
```

**`_handle_sql_error(session, original_sql, error_message)`**
```python
def _handle_sql_error(...) -> Optional[ChatResponse]:
    # 1. Ask GPT to fix the SQL
    # 2. Execute fixed SQL
    # 3. Return results or None if retry failed
```

---

## API Endpoints

### POST `/agents/text-to-sql/start-session`

Start a new chat session for a dataset.

**Request:**
```json
{
  "dataset_id": "abc123-def456-..."
}
```

**Response:**
```json
{
  "session_id": "sess-789xyz-...",
  "schema": {
    "table_name": "user_data_abc123",
    "columns": [
      {"name": "id", "type": "INTEGER", "sample_values": null},
      {"name": "category", "type": "VARCHAR", "sample_values": ["Electronics", "Clothing", "Food"]}
    ],
    "row_count": 10000
  },
  "sample_questions": [
    "How many rows are in the dataset?",
    "What is the average amount?",
    "Show the sum of amount grouped by category"
  ]
}
```

---

### POST `/agents/text-to-sql/chat`

Send a question and receive SQL + results.

**Request:**
```json
{
  "session_id": "sess-789xyz-...",
  "message": "What are the top 5 categories by total sales?"
}
```

**Success Response:**
```json
{
  "status": "success",
  "message": "Query executed successfully. Found 5 rows.",
  "sql_query": "SELECT category, SUM(amount) as total_sales FROM user_data_abc123 GROUP BY category ORDER BY total_sales DESC LIMIT 5",
  "results": [
    {"category": "Electronics", "total_sales": 150000.00},
    {"category": "Clothing", "total_sales": 95000.00}
  ],
  "columns": ["category", "total_sales"],
  "row_count": 5
}
```

**Clarification Response:**
```json
{
  "status": "clarification_needed",
  "message": "Which date range would you like to filter by? The dataset contains dates from 2020-01-01 to 2024-12-31."
}
```

**Error Response:**
```json
{
  "status": "error",
  "message": "The generated query failed to execute.",
  "sql_query": "SELECT invalid_column FROM ...",
  "error_details": "Column 'invalid_column' does not exist"
}
```

---

### GET `/agents/text-to-sql/session/{session_id}`

Get current session state and conversation history.

**Response:**
```json
{
  "session_id": "sess-789xyz-...",
  "dataset_id": "abc123-...",
  "schema": { ... },
  "messages": [
    {"role": "user", "content": "How many rows?", "sql_query": null, "timestamp": "..."},
    {"role": "assistant", "content": "10,000 rows", "sql_query": "SELECT COUNT(*) ...", "timestamp": "..."}
  ],
  "created_at": "2024-01-15T10:30:00",
  "last_activity": "2024-01-15T10:35:00"
}
```

---

### DELETE `/agents/text-to-sql/session/{session_id}`

End a session and cleanup resources.

**Response:**
```json
{
  "status": "success",
  "message": "Session sess-789xyz-... ended successfully"
}
```

---

### GET `/agents/text-to-sql/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "text_to_sql_agent",
  "version": "1.0.0",
  "active_sessions": 3
}
```

---

## Conversation Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           START SESSION                                      │
│  User provides dataset_id                                                    │
│  → Validate dataset exists                                                   │
│  → Build schema context (columns, types, sample values)                      │
│  → Create session with unique ID                                             │
│  → Generate sample questions                                                 │
│  → Return session info to frontend                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CHAT LOOP                                          │
│                                                                              │
│  User sends question                                                         │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Build Prompt                                                         │    │
│  │  • System prompt with schema                                         │    │
│  │  • Last 3 Q&A exchanges for context                                  │    │
│  │  • Current question                                                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ GPT-4o generates response                                            │    │
│  │  • SQL query                                                         │    │
│  │  • OR clarification request                                          │    │
│  │  • OR error explanation                                              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                      │
│       ▼                                                                      │
│  ┌───────────────────────┐                                                  │
│  │ Clarification needed? │──Yes──► Return clarification to user             │
│  └───────────────────────┘                                                  │
│       │ No                                                                   │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Execute SQL on DuckDB                                                │    │
│  │  • query_dataset(dataset_id, sql)                                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                      │
│       ▼                                                                      │
│  ┌───────────────────────┐                                                  │
│  │ Execution successful? │──No──► Retry with GPT fix (1 attempt)            │
│  └───────────────────────┘              │                                   │
│       │ Yes                             │                                   │
│       ▼                                 ▼                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Return results                                                       │    │
│  │  • SQL query                                                         │    │
│  │  • Result rows as JSON                                               │    │
│  │  • Column names                                                      │    │
│  │  • Row count                                                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Error Handling

### Error Types and Responses

| Error Type | Handling Strategy | User Message |
|------------|-------------------|--------------|
| Invalid SQL syntax | GPT retry (1 attempt) | "The query was corrected and executed." |
| Column not found | GPT retry | "Column X doesn't exist. Did you mean Y?" |
| Ambiguous question | Clarification request | "Which date range would you like?" |
| Rate limit | Exponential backoff | Transparent retry, no user message |
| Session expired | 404 error | "Session not found or expired" |
| Dataset not found | 404 error | "Dataset not found" |

### SQL Error Recovery Flow

```
SQL Execution Failed
       │
       ▼
┌─────────────────────────────────────┐
│ Send to GPT:                        │
│  • Original SQL                     │
│  • Error message                    │
│  • Schema context                   │
│                                     │
│ "Please fix this SQL query"         │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ GPT returns fixed SQL               │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ Execute fixed SQL                   │
│  • Success → Return results         │
│  • Failure → Return original error  │
└─────────────────────────────────────┘
```

---

## Token Optimization

To minimize API costs and stay within context limits:

### 1. Schema Compression
- Only include column names and types (not full metadata)
- Sample values only for VARCHAR columns (top 3 unique values)
- Truncate column names longer than 50 characters

### 2. Conversation History Pruning
- Keep only last 3 Q&A exchanges in context
- Truncate message content to 200 characters in prompt
- Full history maintained in session (for UI display)

### 3. Response Limits
- `max_tokens: 500` - SQL queries are typically short
- Structured JSON response format reduces verbosity

### Estimated Token Usage Per Request

| Component | Tokens |
|-----------|--------|
| System prompt (base) | ~200 |
| Schema (10 columns) | ~150 |
| Sample values (5 VARCHAR cols × 3 samples) | ~100 |
| Conversation history (3 exchanges) | ~300 |
| User question | ~50 |
| **Total Input** | **~800** |
| Response | ~100-200 |
| **Total per request** | **~900-1000** |

---

## Usage Examples

### Example 1: Basic Count Query

**User:** "How many products are in the dataset?"

**Generated SQL:**
```sql
SELECT COUNT(*) as product_count
FROM user_data_abc123
```

**Response:**
```json
{
  "status": "success",
  "message": "Query executed successfully. Found 1 row.",
  "sql_query": "SELECT COUNT(*) as product_count FROM user_data_abc123",
  "results": [{"product_count": 15000}],
  "columns": ["product_count"],
  "row_count": 1
}
```

---

### Example 2: Aggregation with Grouping

**User:** "Show me total sales by category, sorted by highest first"

**Generated SQL:**
```sql
SELECT category, SUM(amount) as total_sales
FROM user_data_abc123
GROUP BY category
ORDER BY total_sales DESC
LIMIT 1000
```

---

### Example 3: Filtering with Conditions

**User:** "Find all orders from California with amount greater than 500"

**Generated SQL:**
```sql
SELECT *
FROM user_data_abc123
WHERE state = 'California' AND amount > 500
LIMIT 1000
```

---

### Example 4: Clarification Request

**User:** "Show me recent orders"

**Response:**
```json
{
  "status": "clarification_needed",
  "message": "What time period would you consider 'recent'? The dataset contains orders from 2020-01-01 to 2024-12-31. Would you like orders from the last 30 days, 90 days, or a specific date range?"
}
```

---

### Example 5: Error Recovery

**User:** "What's the average of the price column?"

**First attempt (fails):**
```sql
SELECT AVG(price) FROM user_data_abc123
-- Error: Column 'price' does not exist
```

**GPT retry (succeeds):**
```sql
SELECT AVG(amount) FROM user_data_abc123
-- GPT recognized 'price' might mean 'amount' column
```

---

## Integration Guide

### Frontend Integration

```javascript
// 1. Start Session
const startSession = async (datasetId) => {
  const response = await fetch('/agents/text-to-sql/start-session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dataset_id: datasetId })
  });
  return response.json();
  // Returns: { session_id, schema, sample_questions }
};

// 2. Send Chat Message
const sendMessage = async (sessionId, message) => {
  const response = await fetch('/agents/text-to-sql/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message })
  });
  return response.json();
  // Returns: { status, message, sql_query, results, columns, row_count }
};

// 3. Handle Response
const handleResponse = (response) => {
  switch (response.status) {
    case 'success':
      displayResults(response.results, response.columns);
      showSQL(response.sql_query);
      break;
    case 'clarification_needed':
      showClarificationPrompt(response.message);
      break;
    case 'error':
      showError(response.message, response.error_details);
      break;
  }
};

// 4. End Session (on component unmount)
const endSession = async (sessionId) => {
  await fetch(`/agents/text-to-sql/session/${sessionId}`, {
    method: 'DELETE'
  });
};
```

### Backend Customization

```python
# Custom configuration
from Agents.text_to_sql_agent.config import OPENAI_CONFIG, SQL_CONFIG

# Modify settings before starting
OPENAI_CONFIG["model"] = "gpt-4o-mini"  # Use cheaper model
SQL_CONFIG["default_row_limit"] = 500   # Smaller result sets

# Custom schema building
from Agents.text_to_sql_agent.state_manager import build_schema_context

schema = build_schema_context(dataset_id)
# Modify schema before session creation if needed
```

---

## Security Considerations

1. **SQL Injection Prevention**
   - Queries are generated by GPT, not from raw user input
   - Table names come from trusted database metadata
   - Column validation against known schema

2. **Session Isolation**
   - Each session tied to specific dataset
   - Sessions expire after 1 hour of inactivity
   - No cross-session data access

3. **Rate Limiting**
   - OpenAI API rate limits handled with backoff
   - Consider adding per-user rate limits at API level

4. **Data Access**
   - Users can only query their own datasets
   - Authentication required via `get_current_user` dependency

---

## Future Enhancements (Phase 3)

- **Visualization Recommendations**: Suggest chart types based on query results
- **Query Caching**: Cache frequently asked questions
- **Query Explanation**: Natural language explanation of SQL logic
- **Multi-table Joins**: Support for related datasets
- **Saved Queries**: Allow users to save and reuse queries
