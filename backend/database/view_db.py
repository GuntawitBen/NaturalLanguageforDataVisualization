"""
Utility script to view MySQL database information
"""
from database import get_db_engine
from sqlalchemy import text
import sys

def show_tables():
    """Show all tables in the database"""
    engine = get_db_engine()

    with engine.connect() as conn:
        tables = conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = DATABASE()
        """)).fetchall()

        print("\n" + "="*50)
        print("TABLES IN DATABASE")
        print("="*50)

        for table in tables:
            table_name = table[0]
            count = conn.execute(text(f"SELECT COUNT(*) FROM `{table_name}`")).fetchone()[0]
            print(f"  {table_name:<30} ({count} rows)")

        print()

def show_schema(table_name):
    """Show schema for a specific table"""
    engine = get_db_engine()

    try:
        with engine.connect() as conn:
            schema = conn.execute(text(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = DATABASE() AND table_name = :table_name
                ORDER BY ordinal_position
            """), {"table_name": table_name}).fetchall()

            print("\n" + "="*70)
            print(f"SCHEMA FOR: {table_name}")
            print("="*70)
            print(f"{'Column':<25} {'Type':<20} {'Nullable':<10}")
            print("-"*70)

            for row in schema:
                nullable = "YES" if row[2] == "YES" else "NO"
                print(f"{row[0]:<25} {row[1]:<20} {nullable:<10}")

            # Show row count
            count = conn.execute(text(f"SELECT COUNT(*) FROM `{table_name}`")).fetchone()[0]
            print(f"\nTotal rows: {count}")
            print()

    except Exception as e:
        print(f"Error: {e}")

def show_all_schemas():
    """Show schemas for all tables"""
    engine = get_db_engine()

    with engine.connect() as conn:
        tables = conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = DATABASE()
        """)).fetchall()

        for table in tables:
            show_schema(table[0])

def query_table(table_name, limit=10):
    """Show sample data from a table"""
    engine = get_db_engine()

    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM `{table_name}` LIMIT :limit"),
                                  {"limit": limit}).fetchall()

            print("\n" + "="*70)
            print(f"SAMPLE DATA FROM: {table_name} (showing {len(result)} rows)")
            print("="*70)

            if result:
                # Print column headers
                columns = result[0]._fields
                header = " | ".join([f"{col[:15]:<15}" for col in columns])
                print(header)
                print("-" * len(header))

                # Print rows
                for row in result:
                    row_str = " | ".join([f"{str(val)[:15]:<15}" for val in row])
                    print(row_str)
            else:
                print("(No data)")

            print()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "tables":
            show_tables()
        elif command == "schema":
            if len(sys.argv) > 2:
                show_schema(sys.argv[2])
            else:
                show_all_schemas()
        elif command == "query":
            if len(sys.argv) > 2:
                table_name = sys.argv[2]
                limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
                query_table(table_name, limit)
            else:
                print("Usage: python view_db.py query <table_name> [limit]")
        else:
            print("Unknown command. Use: tables, schema, or query")
    else:
        # Default: show tables
        show_tables()
        print("\nUsage:")
        print("  python view_db.py tables              - List all tables")
        print("  python view_db.py schema [table]      - Show schema(s)")
        print("  python view_db.py query <table> [N]   - Show N rows from table")
