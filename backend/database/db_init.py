"""
Database initialization and connection management for MySQL
"""
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
import os
from pathlib import Path

# Schema path
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Global engine (singleton pattern)
_engine = None

def get_db_engine():
    """
    Get or create a SQLAlchemy engine with connection pooling
    Returns the same engine instance across the application
    """
    global _engine

    if _engine is None:
        mysql_url = (
            f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}"
            f"@{os.getenv('MYSQL_HOST', 'localhost')}:{os.getenv('MYSQL_PORT', '3306')}"
            f"/{os.getenv('MYSQL_DATABASE')}"
        )
        _engine = create_engine(
            mysql_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        print(f"[OK] Created MySQL connection pool")

    return _engine

def get_db_connection():
    """
    Get a database connection from the pool
    Returns a connection that should be used within a context manager or closed manually
    """
    return get_db_engine().connect()

def init_database():
    """
    Initialize the database by executing the schema.sql file
    Creates all tables and indexes if they don't exist
    """
    engine = get_db_engine()

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

        with engine.connect() as conn:
            for i, statement in enumerate(statements):
                if statement:
                    try:
                        print(f"[DEBUG] Executing statement {i+1}/{len(statements)}")
                        conn.execute(text(statement))
                    except Exception as e:
                        print(f"[ERROR] Failed statement: {statement[:150]}...")
                        raise

            conn.commit()

        print("[OK] Database schema initialized successfully")

        # Verify tables were created
        with engine.connect() as conn:
            tables = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
            """)).fetchall()

            print(f"[INFO] Created tables: {[t[0] for t in tables]}")

        return True

    except Exception as e:
        print(f"[ERROR] Error initializing database: {e}")
        raise

def close_connection():
    """Close the database engine and all connections"""
    global _engine
    if _engine:
        _engine.dispose()
        _engine = None
        print("[OK] Database connection pool closed")

def reset_database():
    """
    WARNING: Drops all tables and reinitializes the database
    Use only for development/testing
    """
    engine = get_db_engine()

    with engine.connect() as conn:
        # Get all tables
        tables = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
        """)).fetchall()

        # Disable foreign key checks for dropping
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

        # Drop all tables
        for table in tables:
            table_name = table[0]
            print(f"Dropping table: {table_name}")
            conn.execute(text(f"DROP TABLE IF EXISTS `{table_name}`"))

        # Re-enable foreign key checks
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        conn.commit()

    # Reinitialize
    init_database()
    print("[OK] Database reset complete")

if __name__ == "__main__":
    # Initialize database when run directly
    from dotenv import load_dotenv
    load_dotenv()
    print("Initializing database...")
    init_database()
