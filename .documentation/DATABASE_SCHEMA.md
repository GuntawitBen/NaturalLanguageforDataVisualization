# Database Schema Documentation

## Overview

The application uses **DuckDB** for analytical data storage and querying. The database stores user datasets, conversation history, query logs, and saved visualizations.

**Database File**: `backend/database/nlp_viz.duckdb`

---

## Schema Tables

### 1. **users** Table
Syncs user information from Firebase for quick queries.

| Column | Type | Description |
|--------|------|-------------|
| user_id | VARCHAR (PK) | Unique user identifier |
| email | VARCHAR (UNIQUE) | User email address |
| name | VARCHAR | User's full name |
| picture | VARCHAR | Profile picture URL |
| auth_provider | VARCHAR | 'email' or 'google' |
| created_at | TIMESTAMP | Account creation date |
| last_login | TIMESTAMP | Last login timestamp |
| is_active | BOOLEAN | Account status |

**Indexes**: email, created_at

---

### 2. **datasets** Table
Stores metadata about uploaded CSV files.

| Column | Type | Description |
|--------|------|-------------|
| dataset_id | VARCHAR (PK) | Unique dataset identifier |
| user_id | VARCHAR | Owner's user ID |
| dataset_name | VARCHAR | User-friendly dataset name |
| original_filename | VARCHAR | Original file name |
| file_size_bytes | BIGINT | File size in bytes |
| table_name | VARCHAR | Dynamic table name (user_data_*) |
| row_count | INTEGER | Number of rows |
| column_count | INTEGER | Number of columns |
| columns_info | JSON | Column metadata array |
| upload_date | TIMESTAMP | Upload timestamp |
| last_accessed | TIMESTAMP | Last access timestamp |
| is_deleted | BOOLEAN | Soft delete flag |
| description | TEXT | Dataset description |
| tags | VARCHAR[] | Tags for categorization |

**Indexes**: user_id, upload_date, is_deleted, table_name

**Dynamic Tables**: When a CSV is uploaded, a table named `user_data_{dataset_id}` is created containing the actual data.

---

### 3. **conversations** Table
Stores chat conversations between users and the AI.

| Column | Type | Description |
|--------|------|-------------|
| conversation_id | VARCHAR (PK) | Unique conversation identifier |
| user_id | VARCHAR | User who owns the conversation |
| dataset_id | VARCHAR | Associated dataset (nullable) |
| title | VARCHAR | Conversation title |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |
| is_archived | BOOLEAN | Archive status |

**Indexes**: user_id, dataset_id, created_at, is_archived

---

### 4. **messages** Table
Individual messages within conversations.

| Column | Type | Description |
|--------|------|-------------|
| message_id | VARCHAR (PK) | Unique message identifier |
| conversation_id | VARCHAR | Parent conversation |
| role | VARCHAR | 'user' or 'assistant' |
| content | TEXT | Message text |
| query_sql | TEXT | Generated SQL query |
| query_result | JSON | Query result data |
| visualization_config | JSON | Chart configuration |
| error_message | TEXT | Error if query failed |
| created_at | TIMESTAMP | Message timestamp |
| tokens_used | INTEGER | API tokens used |

**Indexes**: conversation_id, created_at, role

---

### 5. **query_history** Table
Tracks all SQL queries for analytics and debugging.

| Column | Type | Description |
|--------|------|-------------|
| query_id | VARCHAR (PK) | Unique query identifier |
| user_id | VARCHAR | User who ran the query |
| dataset_id | VARCHAR | Dataset queried |
| conversation_id | VARCHAR | Associated conversation |
| natural_language_query | TEXT | User's NL query |
| generated_sql | TEXT | Generated SQL |
| execution_time_ms | DOUBLE | Execution time |
| rows_returned | INTEGER | Number of rows returned |
| success | BOOLEAN | Query success status |
| error_message | TEXT | Error if failed |
| created_at | TIMESTAMP | Query timestamp |

**Indexes**: user_id, dataset_id, created_at, success

---

### 6. **saved_visualizations** Table
User-saved charts and reports.

| Column | Type | Description |
|--------|------|-------------|
| visualization_id | VARCHAR (PK) | Unique visualization identifier |
| user_id | VARCHAR | Owner's user ID |
| dataset_id | VARCHAR | Source dataset |
| title | VARCHAR | Visualization title |
| description | TEXT | Description |
| chart_type | VARCHAR | Chart type (bar, line, pie, etc.) |
| query_sql | TEXT | SQL query for data |
| visualization_config | JSON | Complete chart configuration |
| is_public | BOOLEAN | Public sharing status |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

**Indexes**: user_id, dataset_id, is_public

---

## Database Functions

### Initialization

```python
from database import init_database, get_db_connection

# Initialize database (creates tables)
init_database()

# Get connection
conn = get_db_connection()
```

### User Management

```python
from database import sync_user_from_firebase

# Sync user from Firebase
sync_user_from_firebase(
    user_id="user123",
    email="user@example.com",
    name="John Doe",
    picture="https://...",
    auth_provider="google"
)
```

### Dataset Management

```python
from database import create_dataset, get_dataset, get_user_datasets, delete_dataset, query_dataset

# Create dataset from CSV
dataset_id = create_dataset(
    user_id="user123",
    dataset_name="Sales Data",
    original_filename="sales.csv",
    file_path="/path/to/sales.csv",
    description="Q4 Sales Data",
    tags=["sales", "2024"]
)

# Get dataset metadata
dataset = get_dataset(dataset_id)

# Get all user datasets
datasets = get_user_datasets("user123")

# Query dataset
result = query_dataset(
    dataset_id=dataset_id,
    sql_query="SELECT * FROM {{table}} LIMIT 10"
)

# Delete dataset (soft delete)
delete_dataset(dataset_id, hard_delete=False)
```

### Conversation Management

```python
from database import create_conversation, add_message, get_conversation_messages

# Create conversation
conv_id = create_conversation(
    user_id="user123",
    dataset_id=dataset_id,
    title="Sales Analysis"
)

# Add message
add_message(
    conversation_id=conv_id,
    role="user",
    content="Show me total sales by region"
)

# Get all messages
messages = get_conversation_messages(conv_id)
```

### Query History

```python
from database import log_query

# Log a query execution
log_query(
    user_id="user123",
    natural_language_query="Show me total sales by region",
    generated_sql="SELECT region, SUM(sales) FROM user_data_abc GROUP BY region",
    dataset_id=dataset_id,
    execution_time_ms=45.2,
    rows_returned=5,
    success=True
)
```

### Saved Visualizations

```python
from database import save_visualization, get_user_visualizations

# Save visualization
viz_id = save_visualization(
    user_id="user123",
    dataset_id=dataset_id,
    title="Sales by Region",
    query_sql="SELECT region, SUM(sales) as total FROM user_data_abc GROUP BY region",
    chart_type="bar",
    visualization_config={
        "xAxis": "region",
        "yAxis": "total",
        "color": "#4299e1"
    },
    description="Bar chart showing total sales by region",
    is_public=False
)

# Get user's visualizations
visualizations = get_user_visualizations("user123")
```

---

## Dynamic User Data Tables

When users upload CSV files, dynamic tables are created:

**Naming Convention**: `user_data_{dataset_id_without_dashes}`

**Example**:
- Dataset ID: `abc123-def456`
- Table Name: `user_data_abc123_def456`

These tables contain the actual CSV data and can be queried directly:

```python
# Query user's uploaded data
result = conn.execute("""
    SELECT * FROM user_data_abc123_def456
    WHERE sales > 1000
    ORDER BY date DESC
    LIMIT 10
""").fetchall()
```

---

## File Structure

```
backend/
└── database/
    ├── __init__.py           # Package exports
    ├── schema.sql            # Database schema definition
    ├── db_init.py            # Database initialization
    ├── db_utils.py           # Utility functions
    └── nlp_viz.duckdb        # DuckDB database file (created automatically)
```

---

## Initialization

To initialize the database:

```bash
cd backend
python -m database.db_init
```

Or from Python:

```python
from database import init_database
init_database()
```

---

## Reset Database (Development Only)

```python
from database import reset_database

# WARNING: This drops all tables and data!
reset_database()
```

---

## Environment Variables

Add to your `.env` file:

```env
DUCKDB_PATH=./database/nlp_viz.duckdb
```

---

## Database Status

✅ **Successfully Initialized**

Tables created:
1. users
2. datasets
3. conversations
4. messages
5. query_history
6. saved_visualizations

All tables have appropriate indexes for optimized queries.
