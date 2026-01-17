import os
import json
import sqlite3
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class TextToSQLEngine:
    def __init__(self, db_base_path="minidev/MINIDEV/dev_databases"):
        self.db_base_path = db_base_path

    def get_database_schema(self, db_id):
        """Extract schema from database"""
        db_path = os.path.join(self.db_base_path, db_id, f"{db_id}.sqlite")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        schema_info = []
        for table in tables:
            table_name = table[0]
            # Get columns for each table
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()

            column_info = []
            for col in columns:
                column_info.append(f"{col[1]} {col[2]}")  # name type

            schema_info.append(f"Table {table_name}: {', '.join(column_info)}")

        conn.close()
        return "\n".join(schema_info)

    def generate_sql(self, question, db_id, evidence=None):
        """Generate SQL using GPT-4o"""
        schema = self.get_database_schema(db_id)

        prompt = f"""You are an expert SQL query generator. Generate a SQLite query for the given question.

Database Schema:
{schema}

Question: {question}
"""

        if evidence:
            prompt += f"\nAdditional Context: {evidence}"

        prompt += "\n\nGenerate ONLY the SQL query without any explanation. Use SQLite syntax."

        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "You are an expert SQL generator. Return only valid SQLite queries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=500
        )

        return response.choices[0].message.content.strip()

# Test it
if __name__ == "__main__":
    engine = TextToSQLEngine()

    # Test with first example from dataset
    question = "What is the ratio of customers who pay in EUR against customers who pay in CZK?"
    db_id = "debit_card_specializing"

    print(f"Question: {question}")
    print(f"Database: {db_id}")
    print("\nGenerating SQL...")

    sql = engine.generate_sql(question, db_id)
    print(f"\nGenerated SQL:\n{sql}")