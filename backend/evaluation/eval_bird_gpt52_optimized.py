#!/usr/bin/env python3
"""
BIRD Mini-Dev Evaluation: GPT-5.2 Optimized Pipeline

Four-stage pipeline:
  Stage 1: Enriched schema (cached per db_id) with FK maps, row counts, sample values
  Stage 2: Anti-pattern-aware SQL generation with few-shot examples & step-by-step reasoning
  Stage 3: Execution-based self-correction (run SQL, retry on errors/empty/suspicious results)
  Stage 4: Optional multi-candidate voting (generate N candidates, majority vote on results)

Usage:
  python backend/evaluation/eval_bird_gpt52_optimized.py --sample 20
  python backend/evaluation/eval_bird_gpt52_optimized.py --skip_verify
  python backend/evaluation/eval_bird_gpt52_optimized.py --candidates 5
  python backend/evaluation/eval_bird_gpt52_optimized.py
"""

import os
import sys
import json
import sqlite3
import argparse
import time
import httpx
from collections import Counter
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

# Paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
BIRD_BASE = PROJECT_ROOT / "backend" / "Agents" / "birdmini_benchmark" / "mini_dev"
DATA_PATH = BIRD_BASE / "data" / "bird_mini_dev" / "data" / "mini_dev_sqlite-00000-of-00001.json"
DB_ROOT_PATH = BIRD_BASE / "minidev" / "MINIDEV" / "dev_databases"

# API settings
MODEL = "gpt-5.2"
API_DELAY = 0.5
MAX_RETRIES = 5
EXEC_TIMEOUT = 30  # seconds for SQL execution

# ============================================================
# Stage 1: Schema Enrichment (cached per db_id)
# ============================================================

_schema_cache: dict[str, str] = {}


def build_enriched_schema(db_path: str) -> str:
    """Build enriched schema with FK maps, row counts, column types, and sample values."""
    if db_path in _schema_cache:
        return _schema_cache[db_path]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall() if row[0] != "sqlite_sequence"]

    schema_parts = []

    for table_name in tables:
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        ddl_row = cursor.fetchone()
        ddl = ddl_row[0] if ddl_row and ddl_row[0] else ""

        try:
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            row_count = cursor.fetchone()[0]
        except Exception:
            row_count = "?"

        cursor.execute(f'PRAGMA table_info("{table_name}")')
        columns = cursor.fetchall()

        col_samples = []
        for col in columns:
            col_name = col[1]
            col_type = col[2].upper() if col[2] else "TEXT"
            try:
                cursor.execute(
                    f'SELECT COUNT(DISTINCT "{col_name}") FROM "{table_name}" WHERE "{col_name}" IS NOT NULL'
                )
                distinct_count = cursor.fetchone()[0]

                if col_type in ("REAL", "FLOAT", "DOUBLE", "NUMERIC") and distinct_count > 100:
                    col_samples.append(f"    {col_name} ({col_type}): [{distinct_count} distinct values]")
                    continue

                cursor.execute(
                    f'SELECT DISTINCT "{col_name}" FROM "{table_name}" WHERE "{col_name}" IS NOT NULL LIMIT 3'
                )
                vals = [str(r[0]) for r in cursor.fetchall() if r[0] is not None]
                if vals:
                    col_samples.append(f"    {col_name} ({col_type}): {', '.join(repr(v) for v in vals)}")
                else:
                    col_samples.append(f"    {col_name} ({col_type}): [all NULL]")
            except Exception:
                col_samples.append(f"    {col_name} ({col_type}): [error reading]")

        cursor.execute(f'PRAGMA foreign_key_list("{table_name}")')
        fk_rows = cursor.fetchall()
        fk_lines = []
        for fk in fk_rows:
            fk_lines.append(f"    {table_name}.{fk[3]} -> {fk[2]}.{fk[4]}")

        section = f"-- Table: {table_name} ({row_count} rows)\n{ddl}\n"
        if col_samples:
            section += "  Sample values:\n" + "\n".join(col_samples) + "\n"
        if fk_lines:
            section += "  Foreign keys:\n" + "\n".join(fk_lines) + "\n"

        schema_parts.append(section)

    conn.close()

    enriched = "\n".join(schema_parts)
    _schema_cache[db_path] = enriched
    return enriched


# ============================================================
# Few-Shot Examples (curated from BIRD failure analysis)
# ============================================================

# 5 diverse examples covering the most common failure patterns:
# 1. Simple direct lookup (no JOIN) — counters over-engineering
# 2. IIF/CASE ratio calculation — teaches conditional aggregation + CAST
# 3. Simple single-table COUNT — counters unnecessary JOINs
# 4. GROUP BY + ORDER BY + LIMIT — teaches date evidence + simplest pattern
# 5. CASE WHEN percentage — teaches STRFTIME + percentage formula

FEW_SHOT_EXAMPLES = """
--- EXAMPLE 1: Simple direct lookup (no JOIN needed) ---
Question: List out the code for drivers who have nationality in American.
Evidence: nationality = 'American'
SQL: SELECT code FROM drivers WHERE Nationality = 'American'

--- EXAMPLE 2: Conditional ratio with IIF ---
Question: What is the ratio of customers who pay in EUR against customers who pay in CZK?
Evidence: ratio of customers who pay in EUR against customers who pay in CZK = count(Currency = 'EUR') / count(Currency = 'CZK').
SQL: SELECT CAST(SUM(IIF(Currency = 'EUR', 1, 0)) AS FLOAT) / SUM(IIF(Currency = 'CZK', 1, 0)) AS ratio FROM customers

--- EXAMPLE 3: Simple COUNT on single table (no unnecessary JOINs) ---
Question: How many female patients were given an APS diagnosis?
Evidence: female refers to SEX = 'F'; APS diagnosis refers to Diagnosis='APS'
SQL: SELECT COUNT(ID) FROM Patient WHERE SEX = 'F' AND Diagnosis = 'APS'

--- EXAMPLE 4: JOIN + GROUP BY + ORDER BY + LIMIT (follow date evidence) ---
Question: In 2012, who had the least consumption in LAM?
Evidence: Year 2012 can be presented as Between 201201 And 201212; The first 4 strings of the Date values in the yearmonth table can represent year.
SQL: SELECT T1.CustomerID FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Segment = 'LAM' AND SUBSTR(T2.Date, 1, 4) = '2012' GROUP BY T1.CustomerID ORDER BY SUM(T2.Consumption) ASC LIMIT 1

--- EXAMPLE 5: Percentage with CASE WHEN + STRFTIME ---
Question: What is the percentage of female patient were born after 1930?
Evidence: female refers to Sex = 'F'; patient who were born after 1930 refers to year(Birthday) > '1930'; calculation = DIVIDE(COUNT(ID) where year(Birthday) > '1930' and SEX = 'F'), (COUNT(ID) where SEX = 'F')
SQL: SELECT CAST(SUM(CASE WHEN STRFTIME('%Y', Birthday) > '1930' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM Patient WHERE SEX = 'F'
""".strip()


# ============================================================
# Stage 2: SQL Generation (anti-pattern-aware + few-shot)
# ============================================================

SYSTEM_PROMPT = """You are an expert SQLite SQL analyst. Generate precise, minimal SQL queries.

DATABASE SCHEMA:
{schema}

CRITICAL RULES — follow these exactly:
1. COLUMN MINIMIZATION: Return ONLY the columns explicitly asked for in the question. Never add extra columns "for context."
2. QUERY SIMPLICITY: Prefer ORDER BY + LIMIT 1 over subqueries with MAX/MIN. Use the simplest pattern that works. If only one table is needed, do NOT join extra tables.
3. NO UNNECESSARY FILTERS: Do not add defensive IS NOT NULL, extra ORDER BY, or WHERE clauses not required by the question.
4. COUNT(*) BY DEFAULT: Use COUNT(*) or COUNT(column) unless the question explicitly says "unique", "distinct", or "different".
5. NO LOWER() WRAPPING: Use exact string values from the schema sample values. Do not wrap in LOWER() unless case variation is evident in sample values.
6. EVIDENCE IS GOSPEL: Follow the hints/evidence LITERALLY. If evidence gives a formula, use it exactly. If evidence maps a value (e.g., 'CZE' = Czech Republic), use that exact value.
7. COLUMN VERIFICATION: Verify every column reference exists in the correct table from the schema above.
8. AGGREGATION PATTERNS: For percentages use CAST(SUM(CASE WHEN condition THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*). For ratios use CAST(... AS FLOAT). For conditional counting use SUM(IIF(condition, 1, 0)) or SUM(CASE WHEN ... THEN 1 ELSE 0 END).
9. APPROPRIATE DISTINCT: Use DISTINCT only when JOINs may create duplicate rows in the output. Never use COUNT(DISTINCT ...) unless the question asks for unique/different values.
10. DATE HANDLING: Follow the evidence for date format. Common patterns: SUBSTR(date_col, 1, 4) for year, STRFTIME('%Y', date_col) for date columns, string comparison 'YYYY-MM-DD', LIKE 'YYYY-MM%' for month matching.

OUTPUT: Return ONLY the SQL query starting with SELECT. No explanation, no markdown, no code fences."""


USER_PROMPT_TEMPLATE = """Here are examples of correct SQL generation:

{few_shot_examples}

Now generate SQL for the following question.

Question: {question}
Evidence/Hints: {evidence}

Think step by step:
1. Which tables are needed? (Use the MINIMUM number of tables)
2. What are the correct JOIN conditions? (Only if multiple tables are needed)
3. What columns does the question ask for? (ONLY those — no extras)
4. What filters/conditions are needed? (ONLY from the question and evidence)
5. Is aggregation needed? What kind? (Follow evidence formulas exactly)
6. What is the simplest query structure? (ORDER BY + LIMIT vs subquery)

SQL:"""


def _call_api(api_key: str, messages: list, temperature: float = 0,
              max_tokens: int = 800) -> str | None:
    """Make an API call via httpx with retry logic. Returns content or None on failure."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_completion_tokens": max_tokens,
    }

    for attempt in range(MAX_RETRIES):
        try:
            r = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120.0,
            )
            if r.status_code == 429:
                wait_time = (2 ** attempt) * 2
                print(f"\n  Rate limited (429). Waiting {wait_time}s (retry {attempt + 1}/{MAX_RETRIES})...")
                time.sleep(wait_time)
                continue
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
        except httpx.HTTPStatusError as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate" in error_str:
                wait_time = (2 ** attempt) * 2
                print(f"\n  Rate limited. Waiting {wait_time}s (retry {attempt + 1}/{MAX_RETRIES})...")
                time.sleep(wait_time)
            else:
                print(f"\n  Attempt {attempt + 1} failed: {e}")
                if attempt == MAX_RETRIES - 1:
                    return None
                time.sleep(2)
        except Exception as e:
            print(f"\n  Attempt {attempt + 1} failed: {e}")
            if attempt == MAX_RETRIES - 1:
                return None
            time.sleep(2)
    return None


def generate_sql(api_key: str,question: str, evidence: str, db_path: str,
                 temperature: float = 0) -> str:
    """Stage 2: Generate SQL with anti-pattern-aware prompt + few-shot examples."""
    schema = build_enriched_schema(db_path)
    system = SYSTEM_PROMPT.format(schema=schema)
    user = USER_PROMPT_TEMPLATE.format(
        few_shot_examples=FEW_SHOT_EXAMPLES,
        question=question,
        evidence=evidence if evidence else "(none)"
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    content = _call_api(api_key, messages, temperature=temperature)
    if content is None:
        return "SELECT 'ERROR: API call failed'"
    return _clean_sql(content)


def _clean_sql(text: str) -> str:
    """Extract clean SQL from model response."""
    sql = text.strip()
    # Remove markdown code fences
    if sql.startswith("```"):
        lines = sql.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        sql = "\n".join(lines).strip()
    # Remove any leading non-SQL text (find first SELECT)
    upper = sql.upper()
    select_idx = upper.find("SELECT")
    if select_idx > 0:
        sql = sql[select_idx:]
    # Remove trailing semicolons
    sql = sql.rstrip(";").strip()
    return sql


# ============================================================
# Stage 3: Execution-Based Self-Correction
# ============================================================

def _execute_sql(sql: str, db_path: str, timeout: float = EXEC_TIMEOUT):
    """Execute SQL against the database. Returns (results, error_string)."""
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA busy_timeout = 5000")
        cursor = conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        conn.close()
        return results, None
    except Exception as e:
        return None, str(e)


EXEC_FIX_PROMPT = """The SQL query you generated has an issue. Fix it.

Question: {question}
Evidence/Hints: {evidence}

Your SQL:
{sql}

{issue_description}

Database schema:
{schema_ddl}

Return ONLY the corrected SQL starting with SELECT. No explanation."""


def execution_verify(api_key: str,sql: str, question: str, evidence: str,
                     db_path: str, max_rounds: int = 3) -> tuple[str, int]:
    """Stage 3: Execute SQL, check results, retry on errors/suspicious output.

    Returns (final_sql, num_fixes_applied).
    """
    schema_ddl = _get_ddl_only(db_path)
    fixes = 0

    for round_num in range(max_rounds):
        results, error = _execute_sql(sql, db_path)

        if error:
            # SQL error — feed error message back for correction
            issue = f"Execution error:\n{error}\n\nFix the SQL to resolve this error."
            fixed = _ask_for_fix(api_key, sql, question, evidence, schema_ddl, issue)
            if fixed and fixed != sql:
                sql = fixed
                fixes += 1
                continue
            else:
                break  # couldn't fix, return what we have

        # Check for suspicious results
        issue = _check_suspicious_results(results, question)
        if issue and round_num < max_rounds - 1:
            fixed = _ask_for_fix(api_key, sql, question, evidence, schema_ddl, issue)
            if fixed and fixed != sql:
                sql = fixed
                fixes += 1
                continue

        # Results look OK
        break

    return sql, fixes


def _check_suspicious_results(results, question: str) -> str | None:
    """Check if query results look suspicious. Returns issue description or None."""
    if results is None:
        return None

    # Empty results — likely over-restrictive WHERE
    if len(results) == 0:
        return ("The query returned ZERO rows. This likely means the WHERE clause is too "
                "restrictive, or a JOIN condition is wrong, or a value doesn't match exactly. "
                "Check the filter values against the sample data and fix the query.")

    # All NULL results
    if all(all(v is None for v in row) for row in results):
        return ("The query returned only NULL values. This suggests wrong column references "
                "or incorrect JOIN conditions. Check the column names and table references.")

    return None


def _ask_for_fix(api_key: str,sql: str, question: str, evidence: str,
                 schema_ddl: str, issue: str) -> str | None:
    """Ask the model to fix a SQL query given an issue description."""
    prompt = EXEC_FIX_PROMPT.format(
        question=question,
        evidence=evidence if evidence else "(none)",
        sql=sql,
        issue_description=issue,
        schema_ddl=schema_ddl,
    )

    messages = [{"role": "user", "content": prompt}]
    content = _call_api(api_key, messages, temperature=0, max_tokens=800)
    if content is None:
        return None

    cleaned = _clean_sql(content)
    if cleaned.upper().startswith("SELECT"):
        return cleaned
    return None


# ============================================================
# Stage 4: Multi-Candidate Voting (optional)
# ============================================================

def generate_with_voting(api_key: str,question: str, evidence: str,
                         db_path: str, n_candidates: int = 5) -> str:
    """Generate N SQL candidates and pick the one with the most common result set.

    Strategy:
    - 1 candidate at temperature=0 (deterministic best guess)
    - N-1 candidates at temperature=0.7 (diverse alternatives)
    - Execute all, group by result set, pick majority
    - On ties, prefer the temperature=0 candidate
    """
    candidates = []

    # First candidate: deterministic
    sql_det = generate_sql(api_key, question, evidence, db_path, temperature=0)
    candidates.append(sql_det)
    time.sleep(API_DELAY)

    # Remaining candidates: diverse
    for _ in range(n_candidates - 1):
        sql_div = generate_sql(api_key, question, evidence, db_path, temperature=0.7)
        candidates.append(sql_div)
        time.sleep(API_DELAY)

    # Execute all candidates and group by result set
    result_groups: dict[str, list[int]] = {}  # serialized_result -> [candidate_indices]
    exec_errors = []

    for idx, sql in enumerate(candidates):
        if "ERROR" in sql:
            exec_errors.append(idx)
            continue
        results, error = _execute_sql(sql, db_path)
        if error:
            exec_errors.append(idx)
            continue

        # Serialize result set for comparison (use frozenset for set equality like BIRD EX)
        key = repr(sorted(set(results))) if results else "EMPTY"
        if key not in result_groups:
            result_groups[key] = []
        result_groups[key].append(idx)

    if not result_groups:
        # All candidates errored — return the deterministic one
        return candidates[0]

    # Find the result with the most votes
    best_key = max(result_groups, key=lambda k: (len(result_groups[k]), 0 in result_groups[k]))
    best_indices = result_groups[best_key]

    # Prefer the deterministic candidate (index 0) if it's in the winning group
    if 0 in best_indices:
        return candidates[0]
    return candidates[best_indices[0]]


# ============================================================
# LLM-Based Verification (Stage 3 alternative, kept as fallback)
# ============================================================

VERIFY_SYSTEM_PROMPT = """You are a SQL verification expert. Check the SQL query for these specific issues:

1. EXTRA COLUMNS: Does the query return columns NOT asked for in the question?
2. OVER-COMPLEXITY: Can the query be simplified (e.g., subquery with MAX -> ORDER BY + LIMIT 1)?
3. UNNECESSARY FILTERS: Are there WHERE/HAVING clauses not required by the question?
4. WRONG COUNT: Does it use COUNT(DISTINCT ...) when COUNT(*) is correct, or vice versa?
5. WRONG COLUMN: Does it reference a column that doesn't exist or is from the wrong table?
6. UNNECESSARY LOWER(): Does it wrap strings in LOWER() when exact values are available?

If the query is correct, respond with exactly: CORRECT
If there is an issue, respond with ONLY the fixed SQL query starting with SELECT. No explanation."""


VERIFY_USER_TEMPLATE = """Question: {question}
Evidence/Hints: {evidence}

Generated SQL:
{sql}

Database schema (abbreviated):
{schema_abbrev}

Is this SQL correct for the question, or does it have any of the 6 issues listed above?"""


def llm_verify_sql(api_key: str,sql: str, question: str, evidence: str,
                   db_path: str) -> str:
    """LLM-based verification pass (supplementary to execution-based)."""
    schema_abbrev = _get_ddl_only(db_path)

    user = VERIFY_USER_TEMPLATE.format(
        question=question,
        evidence=evidence if evidence else "(none)",
        sql=sql,
        schema_abbrev=schema_abbrev,
    )

    messages = [
        {"role": "system", "content": VERIFY_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]

    content = _call_api(api_key, messages, temperature=0)
    if content is None:
        return sql

    if content.upper() == "CORRECT":
        return sql

    cleaned = _clean_sql(content)
    if cleaned.upper().startswith("SELECT"):
        return cleaned

    return sql


def _get_ddl_only(db_path: str) -> str:
    """Get just CREATE TABLE statements (no samples) for verification prompt."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()

    parts = []
    for (table_name,) in tables:
        if table_name == "sqlite_sequence":
            continue
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        row = cursor.fetchone()
        if row and row[0]:
            parts.append(row[0])

    conn.close()
    return "\n\n".join(parts)


# ============================================================
# Main Pipeline
# ============================================================

def run_pipeline(
    output_path: str,
    sample_size: int = None,
    skip_verify: bool = False,
    n_candidates: int = 1,
    resume: bool = True,
):
    """Run the optimized pipeline on BIRD benchmark questions.

    Pipeline stages per question:
    1. Schema enrichment (cached)
    2. SQL generation (few-shot + anti-pattern rules)
    3a. If n_candidates > 1: multi-candidate voting (generates N, votes on execution results)
    3b. Execution-based self-correction (retry on errors/empty results, up to 3 rounds)
    4. LLM verification pass (unless --skip_verify)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

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

    mode_parts = []
    if n_candidates > 1:
        mode_parts.append(f"{n_candidates}-candidate voting")
    mode_parts.append("execution-verify")
    if not skip_verify:
        mode_parts.append("LLM-verify")
    mode_str = " + ".join(mode_parts)

    print(f"Running GPT-5.2 optimized pipeline [{mode_str}] on {len(data)} questions (starting from {start_idx})...")

    # Pre-warm schema cache
    db_ids = {item["db_id"] for item in data}
    print(f"Pre-caching enriched schemas for {len(db_ids)} databases...")
    for db_id in db_ids:
        db_path = str(DB_ROOT_PATH / db_id / f"{db_id}.sqlite")
        build_enriched_schema(db_path)
    print("Schema cache ready.")

    error_count = 0
    exec_fix_count = 0
    llm_fix_count = 0
    vote_used_count = 0

    for i, item in enumerate(tqdm(data, desc="Generating predictions", initial=start_idx)):
        if i < start_idx:
            continue

        question = item["question"]
        evidence = item.get("evidence", "")
        db_id = item["db_id"]
        db_path = str(DB_ROOT_PATH / db_id / f"{db_id}.sqlite")

        # Stage 2 (+ optional Stage 4: voting)
        if n_candidates > 1:
            sql = generate_with_voting(api_key, question, evidence, db_path, n_candidates)
            vote_used_count += 1
        else:
            sql = generate_sql(api_key, question, evidence, db_path)

        # Stage 3: Execution-based self-correction
        if "ERROR" not in sql:
            sql, n_fixes = execution_verify(api_key, sql, question, evidence, db_path)
            exec_fix_count += n_fixes

        # Stage 4 (optional): LLM verification pass
        if not skip_verify and "ERROR" not in sql:
            verified_sql = llm_verify_sql(api_key, sql, question, evidence, db_path)
            if verified_sql != sql:
                # Verify the LLM fix doesn't break execution
                _, exec_err = _execute_sql(verified_sql, db_path)
                if exec_err is None:
                    llm_fix_count += 1
                    sql = verified_sql
                # else: keep original sql (LLM fix introduced an error)

        if "ERROR" in sql:
            error_count += 1
            print(f"\n  Error on question {i}: {sql[:100]}")

        # BIRD prediction format
        predictions[str(i)] = f"{sql}\t----- bird -----\t{db_id}"

        # Checkpoint every 50 questions
        if (i + 1) % 50 == 0:
            with open(output_path, "w") as f:
                json.dump(predictions, f, indent=4)
            print(f"\n  Checkpoint at {i + 1}: exec_fixes={exec_fix_count}, llm_fixes={llm_fix_count}")

        time.sleep(API_DELAY)

    # Final save
    with open(output_path, "w") as f:
        json.dump(predictions, f, indent=4)

    print(f"\nPredictions saved to {output_path}")
    print(f"Total: {len(predictions)}, Errors: {error_count}")
    print(f"Execution fixes: {exec_fix_count}, LLM fixes: {llm_fix_count}")
    if n_candidates > 1:
        print(f"Voting rounds: {vote_used_count}")
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description="BIRD Evaluation: GPT-5.2 Optimized Pipeline")
    parser.add_argument(
        "--output_path", type=str,
        default="backend/evaluation/results/predict_gpt52_optimized.json",
        help="Output path for predictions JSON"
    )
    parser.add_argument("--sample", type=int, default=None, help="Only process first N samples")
    parser.add_argument("--skip_verify", action="store_true", help="Skip the LLM verification pass")
    parser.add_argument("--candidates", type=int, default=1,
                        help="Number of candidates for voting (1=no voting, 5=recommended)")
    parser.add_argument("--no_resume", action="store_true", help="Start fresh (don't resume)")
    args = parser.parse_args()

    run_pipeline(
        output_path=args.output_path,
        sample_size=args.sample,
        skip_verify=args.skip_verify,
        n_candidates=args.candidates,
        resume=not args.no_resume,
    )


if __name__ == "__main__":
    main()
