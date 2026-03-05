#!/usr/bin/env python3
"""
BIRD Mini-Dev Evaluation: Our Pipeline vs GPT-4o Baseline

Runs BIRD benchmark questions through our adapted prompt pipeline
(structured schema + rules from prompts.py, adapted for SQLite multi-table).
"""

import os
import sys
import json
import sqlite3
import argparse
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

load_dotenv()

# Paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
BIRD_BASE = PROJECT_ROOT / "backend" / "Agents" / "birdmini_benchmark" / "mini_dev"
DATA_PATH = BIRD_BASE / "data" / "bird_mini_dev" / "data" / "mini_dev_sqlite-00000-of-00001.json"
DB_ROOT_PATH = BIRD_BASE / "minidev" / "MINIDEV" / "dev_databases"
GOLD_SQL_PATH = BIRD_BASE / "minidev" / "MINIDEV" / "mini_dev_sqlite_gold.sql"

# API settings
API_DELAY = 0.5
MAX_RETRIES = 5

# --- Schema extraction ---

def get_schema_ddl(db_path: str) -> str:
    """Extract CREATE TABLE statements from SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()

    schema_parts = []
    for (table_name,) in tables:
        if table_name == "sqlite_sequence":
            continue
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        row = cursor.fetchone()
        if row and row[0]:
            schema_parts.append(row[0])

    conn.close()
    return "\n\n".join(schema_parts)


def get_sample_values(db_path: str, max_samples: int = 3) -> str:
    """Get sample values for text columns to help with filtering."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()

    sample_parts = []
    for (table_name,) in tables:
        if table_name == "sqlite_sequence":
            continue
        try:
            cursor.execute(f'PRAGMA table_info("{table_name}")')
            columns = cursor.fetchall()
        except Exception:
            continue

        text_cols = [col[1] for col in columns if col[2].upper() in ("TEXT", "VARCHAR", "CHAR")]
        if not text_cols:
            continue

        col_samples = []
        for col_name in text_cols[:5]:  # limit columns per table
            try:
                cursor.execute(
                    f'SELECT DISTINCT "{col_name}" FROM "{table_name}" WHERE "{col_name}" IS NOT NULL LIMIT ?',
                    (max_samples,)
                )
                vals = [str(r[0]) for r in cursor.fetchall() if r[0]]
                if vals:
                    col_samples.append(f"  {col_name}: {', '.join(repr(v) for v in vals)}")
            except Exception:
                continue

        if col_samples:
            sample_parts.append(f"Table {table_name}:\n" + "\n".join(col_samples))

    conn.close()
    return "\n".join(sample_parts) if sample_parts else ""


# --- Prompt building ---

SYSTEM_PROMPT = """You are an expert SQL analyst. Your task is to convert natural language questions into correct SQLite SQL queries.

DATABASE SCHEMA:
{schema_ddl}

SAMPLE VALUES (for text columns):
{sample_values}

RULES:
1. ONLY use tables and columns that exist in the schema above
2. Use proper JOINs based on foreign key relationships defined in the schema
3. Use standard SQL aggregations: SUM, AVG, COUNT, MIN, MAX with GROUP BY when needed
4. Use WHERE for filtering with operators: =, !=, <, >, <=, >=, IN, BETWEEN, LIKE
5. Use ORDER BY ASC/DESC for sorting
6. For case-insensitive string comparisons, use LOWER(column) = LOWER('value')
7. Use SQLite-compatible syntax:
   - Use || for string concatenation (not CONCAT)
   - Use strftime() for date formatting (not DATE_FORMAT)
   - Use GROUP_CONCAT() for aggregating strings
   - Use CAST(x AS REAL) or CAST(x AS FLOAT) for decimal division
   - Use IIF(condition, true_val, false_val) or CASE WHEN for conditionals
   - Use IFNULL() or COALESCE() for null handling
8. Pay careful attention to the evidence/hints provided — they often contain the exact formulas or definitions needed
9. Always validate that referenced columns exist in the correct table before using them

RESPONSE FORMAT:
Respond with a JSON object:
{{"sql": "SELECT ...", "explanation": "Brief explanation"}}

IMPORTANT:
- Never include markdown code blocks, just raw JSON
- Return only the JSON object, no additional text"""


def build_our_prompt(question: str, evidence: str, db_path: str) -> tuple:
    """Build system + user prompt using our pipeline approach."""
    schema_ddl = get_schema_ddl(db_path)
    sample_values = get_sample_values(db_path)

    system = SYSTEM_PROMPT.format(
        schema_ddl=schema_ddl,
        sample_values=sample_values if sample_values else "(none)"
    )

    user_parts = []
    if evidence:
        user_parts.append(f"External Knowledge / Hints: {evidence}")
    user_parts.append(f"Question: {question}")
    user_parts.append("\nGenerate the SQLite SQL query:")

    return system, "\n".join(user_parts)


def build_baseline_prompt(question: str, evidence: str, db_path: str) -> tuple:
    """Build the simple baseline prompt (same style as GPT-4o evaluation)."""
    schema = get_schema_ddl(db_path)

    user_prompt = f"""{schema}

-- Using valid SQLite and understanding External Knowledge, answer the following questions for the tables provided above.
-- {question}
-- External Knowledge: {evidence}

Generate the SQLite SQL query for the above question after thinking step by step:

In your response, you do not need to mention your intermediate steps.
Do not include any comments in your response.
Do not need to start with the symbol ```
You only need to return the result SQLite SQL code
start from SELECT"""

    return None, user_prompt


# --- API call ---

def call_openai(client: OpenAI, system_prompt: str, user_prompt: str,
                model: str = "gpt-4.1", max_retries: int = MAX_RETRIES) -> str:
    """Call OpenAI API and extract SQL from response."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0,
                max_completion_tokens=600,
            )
            content = response.choices[0].message.content.strip()
            return extract_sql(content)
        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "limit" in error_str or "429" in error_str:
                wait_time = (2 ** attempt) * 2
                print(f"\n  Rate limited. Waiting {wait_time}s (retry {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
            else:
                print(f"\n  Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return f"SELECT 'ERROR: {e}'"
                time.sleep(2)
    return "SELECT 'ERROR: Max retries exceeded'"


def extract_sql(response_text: str) -> str:
    """Extract SQL from JSON response or raw text."""
    # Try JSON parse first
    try:
        data = json.loads(response_text)
        if isinstance(data, dict) and "sql" in data:
            return data["sql"].strip()
    except json.JSONDecodeError:
        pass

    # Try to find JSON within the text
    for start_char in ['{', '```']:
        if start_char == '{':
            start = response_text.find('{')
            end = response_text.rfind('}')
            if start != -1 and end != -1:
                try:
                    data = json.loads(response_text[start:end+1])
                    if isinstance(data, dict) and "sql" in data:
                        return data["sql"].strip()
                except json.JSONDecodeError:
                    pass

    # Fallback: treat as raw SQL
    sql = response_text.strip()
    # Remove markdown code fences if present
    if sql.startswith("```"):
        lines = sql.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        sql = "\n".join(lines).strip()
    return sql


# --- Main runner ---

def generate_predictions(
    output_path: str,
    model: str = "gpt-4.1",
    sample_size: int = None,
    resume: bool = True,
    baseline_prompt: bool = False
):
    """Generate SQL predictions for BIRD benchmark questions."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment")

    client = OpenAI(api_key=api_key)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load benchmark data
    with open(DATA_PATH, "r") as f:
        data = json.load(f)

    if sample_size:
        data = data[:sample_size]

    # Resume from checkpoint
    predictions = {}
    start_idx = 0
    if resume and output_path.exists():
        with open(output_path, "r") as f:
            predictions = json.load(f)
        completed = {int(k) for k in predictions.keys()}
        start_idx = max(completed) + 1 if completed else 0
        print(f"Resuming from question {start_idx} ({len(predictions)} already completed)")

    prompt_style = "baseline" if baseline_prompt else "our pipeline"
    print(f"Running {prompt_style} ({model}) on {len(data)} questions (starting from {start_idx})...")

    error_count = 0
    for i, item in enumerate(tqdm(data, desc="Generating predictions", initial=start_idx)):
        if i < start_idx:
            continue

        question = item["question"]
        evidence = item.get("evidence", "")
        db_id = item["db_id"]
        db_path = str(DB_ROOT_PATH / db_id / f"{db_id}.sqlite")

        if baseline_prompt:
            system_prompt, user_prompt = build_baseline_prompt(question, evidence, db_path)
        else:
            system_prompt, user_prompt = build_our_prompt(question, evidence, db_path)
        sql = call_openai(client, system_prompt, user_prompt, model=model)

        if "ERROR" in sql:
            error_count += 1
            print(f"\n  Error on question {i}: {sql[:100]}")

        # BIRD prediction format
        predictions[str(i)] = f"{sql}\t----- bird -----\t{db_id}"

        # Checkpoint every 50 questions
        if (i + 1) % 50 == 0:
            with open(output_path, "w") as f:
                json.dump(predictions, f, indent=4)
            print(f"\n  Checkpoint saved at question {i + 1}")

        time.sleep(API_DELAY)

    # Final save
    with open(output_path, "w") as f:
        json.dump(predictions, f, indent=4)

    print(f"\nPredictions saved to {output_path}")
    print(f"Total: {len(predictions)}, Errors: {error_count}")
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description="BIRD Evaluation: Our Pipeline")
    parser.add_argument(
        "--output_path", type=str,
        default="backend/evaluation/results/predict_our_pipeline.json",
        help="Output path for predictions JSON"
    )
    parser.add_argument("--model", type=str, default="gpt-4.1", help="OpenAI model to use")
    parser.add_argument("--sample", type=int, default=None, help="Only process first N samples")
    parser.add_argument("--no_resume", action="store_true", help="Start fresh (don't resume)")
    parser.add_argument("--baseline_prompt", action="store_true", help="Use simple baseline prompt instead of our pipeline")
    args = parser.parse_args()

    generate_predictions(
        output_path=args.output_path,
        model=args.model,
        sample_size=args.sample,
        resume=not args.no_resume,
        baseline_prompt=args.baseline_prompt
    )


if __name__ == "__main__":
    main()
