"""
Database initialization and connection management for DuckDB
"""
import duckdb
import os
from pathlib import Path

# Database file path
DB_PATH = os.getenv("DUCKDB_PATH", "./database/nlp_viz.duckdb")
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Global connection (singleton pattern)
_connection = None

def get_db_connection():
    """
    Get or create a DuckDB connection (singleton)
    Returns the same connection instance across the application
    """
    global _connection

    if _connection is None:
        # Create database directory if it doesn't exist
        db_dir = os.path.dirname(DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        # Connect to DuckDB (creates file if doesn't exist)
        _connection = duckdb.connect(DB_PATH)
        print(f"[OK] Connected to DuckDB at: {DB_PATH}")

    return _connection

def init_database():
    """
    Initialize the database by executing the schema.sql file
    Creates all tables and indexes if they don't exist
    """
    conn = get_db_connection()

    try:
        # Read and execute schema SQL
        with open(SCHEMA_PATH, 'r') as f:
            schema_sql = f.read()

        # Remove comments and split by semicolons
        lines = []
        for line in schema_sql.split('\n'):
            # Remove inline comments and strip
            line = line.split('--')[0].strip()
            if line:
                lines.append(line)

        cleaned_sql = '\n'.join(lines)
        statements = [s.strip() for s in cleaned_sql.split(';') if s.strip()]

        for i, statement in enumerate(statements):
            if statement:
                try:
                    print(f"[DEBUG] Executing statement {i+1}/{len(statements)}")
                    conn.execute(statement)
                except Exception as e:
                    print(f"[ERROR] Failed statement: {statement[:150]}...")
                    raise

        print("[OK] Database schema initialized successfully")

        # Verify tables were created
        tables = conn.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
        """).fetchall()

        print(f"[INFO] Created tables: {[t[0] for t in tables]}")

        return True

    except Exception as e:
        print(f"[ERROR] Error initializing database: {e}")
        raise

def close_connection():
    """Close the database connection"""
    global _connection
    if _connection:
        _connection.close()
        _connection = None
        print("[OK] Database connection closed")

def reset_database():
    """
    WARNING: Drops all tables and reinitializes the database
    Use only for development/testing
    """
    conn = get_db_connection()

    # Get all tables
    tables = conn.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
    """).fetchall()

    # Drop all tables
    for table in tables:
        table_name = table[0]
        print(f"Dropping table: {table_name}")
        conn.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")

    # Reinitialize
    init_database()
    print("[OK] Database reset complete")

if __name__ == "__main__":
    # Initialize database when run directly
    print("Initializing database...")
    init_database()
