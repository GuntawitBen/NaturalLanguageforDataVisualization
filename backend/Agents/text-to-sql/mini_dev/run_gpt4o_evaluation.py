#!/usr/bin/env python3
"""
GPT-4o Evaluation Script for BIRD Mini-Dev Benchmark
Runs GPT-4o on all 500 benchmark questions and evaluates execution accuracy.
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
import multiprocessing as mp
from func_timeout import func_timeout, FunctionTimedOut

# Rate limiting settings
API_DELAY = 0.5  # seconds between API calls
MAX_RETRIES = 5  # max retries on rate limit

# Load environment variables
load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "bird_mini_dev" / "data" / "mini_dev_sqlite-00000-of-00001.json"
DB_ROOT_PATH = BASE_DIR / "minidev" / "MINIDEV" / "dev_databases"
OUTPUT_DIR = BASE_DIR / "results"
OUTPUT_DIR.mkdir(exist_ok=True)


def get_schema_prompt(db_path: str) -> str:
    """Extract CREATE TABLE statements from SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    schema_parts = []
    for (table_name,) in tables:
        if table_name == "sqlite_sequence":
            continue
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';")
        create_stmt = cursor.fetchone()[0]
        schema_parts.append(create_stmt)

    conn.close()
    return "\n\n".join(schema_parts)


def build_prompt(question: str, evidence: str, db_path: str) -> str:
    """Build the prompt for GPT-4o."""
    schema = get_schema_prompt(db_path)

    prompt = f"""{schema}

-- Using valid SQLite and understanding External Knowledge, answer the following questions for the tables provided above.
-- {question}
-- External Knowledge: {evidence}

Generate the SQLite SQL query for the above question after thinking step by step:

In your response, you do not need to mention your intermediate steps.
Do not include any comments in your response.
Do not need to start with the symbol ```
You only need to return the result SQLite SQL code
start from SELECT"""

    return prompt


def call_gpt4o(client: OpenAI, prompt: str, max_retries: int = MAX_RETRIES) -> str:
    """Call GPT-4o API and return the SQL response with rate limit handling."""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=500,
                stop=["--", "\n\n", ";", "#"]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "limit" in error_str or "429" in error_str:
                wait_time = (2 ** attempt) * 2  # Exponential backoff: 2, 4, 8, 16, 32 seconds
                print(f"\n  Rate limited. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait_time)
            else:
                print(f"\n  Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return f"ERROR: {e}"
                time.sleep(2)  # Brief pause before retry
    return "ERROR: Max retries exceeded"


def generate_predictions(sample_size: int = None, resume: bool = True):
    """Generate SQL predictions for all benchmark questions with checkpointing."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file")

    client = OpenAI(api_key=api_key)
    output_path = OUTPUT_DIR / "predict_gpt4o_sqlite.json"

    # Load benchmark data
    with open(DATA_PATH, "r") as f:
        data = json.load(f)

    if sample_size:
        data = data[:sample_size]

    # Resume from checkpoint if exists
    predictions = {}
    start_idx = 0
    if resume and output_path.exists():
        with open(output_path, "r") as f:
            predictions = json.load(f)
        # Convert string keys to int for comparison
        completed = {int(k) for k in predictions.keys()}
        start_idx = max(completed) + 1 if completed else 0
        print(f"Resuming from question {start_idx} ({len(predictions)} already completed)")

    print(f"Running GPT-4o on {len(data)} questions (starting from {start_idx})...")

    error_count = 0
    for i, item in enumerate(tqdm(data, desc="Generating predictions", initial=start_idx)):
        if i < start_idx:
            continue

        question = item["question"]
        evidence = item.get("evidence", "")
        db_id = item["db_id"]
        db_path = str(DB_ROOT_PATH / db_id / f"{db_id}.sqlite")

        prompt = build_prompt(question, evidence, db_path)
        sql = call_gpt4o(client, prompt)

        # Track errors
        if sql.startswith("ERROR:"):
            error_count += 1
            print(f"\n  Error on question {i}: {sql}")

        # Format: SQL\t----- bird -----\tdb_id
        predictions[str(i)] = f"{sql}\t----- bird -----\t{db_id}"

        # Save checkpoint every 50 questions
        if (i + 1) % 50 == 0:
            with open(output_path, "w") as f:
                json.dump(predictions, f, indent=4)
            print(f"\n  Checkpoint saved at question {i + 1}")

        # Rate limiting delay
        time.sleep(API_DELAY)

    # Final save
    with open(output_path, "w") as f:
        json.dump(predictions, f, indent=4)

    print(f"\nPredictions saved to {output_path}")
    print(f"Total: {len(predictions)}, Errors: {error_count}")
    return output_path


def create_ground_truth_file():
    """Create ground truth file in the expected format."""
    with open(DATA_PATH, "r") as f:
        data = json.load(f)

    gt_path = OUTPUT_DIR / "ground_truth.sql"
    with open(gt_path, "w") as f:
        for item in data:
            sql = item["SQL"]
            db_id = item["db_id"]
            f.write(f"{sql}\t{db_id}\n")

    print(f"Ground truth saved to {gt_path}")
    return gt_path


def execute_sql_query(sql: str, db_path: str, timeout: float = 30.0):
    """Execute SQL and return results."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(sql)
    results = cursor.fetchall()
    conn.close()
    return results


def evaluate_single(args):
    """Evaluate a single prediction."""
    idx, pred_sql, gt_sql, db_path, timeout = args
    try:
        pred_result = func_timeout(timeout, execute_sql_query, args=(pred_sql, db_path))
        gt_result = func_timeout(timeout, execute_sql_query, args=(gt_sql, db_path))
        correct = 1 if set(pred_result) == set(gt_result) else 0
        return {"idx": idx, "correct": correct, "error": None}
    except FunctionTimedOut:
        return {"idx": idx, "correct": 0, "error": "timeout"}
    except Exception as e:
        return {"idx": idx, "correct": 0, "error": str(e)}


def run_evaluation(pred_path: Path = None):
    """Run execution-based evaluation."""
    if pred_path is None:
        pred_path = OUTPUT_DIR / "predict_gpt4o_sqlite.json"

    if not pred_path.exists():
        print(f"Predictions file not found: {pred_path}")
        print("Run with --generate first to create predictions.")
        return

    # Load predictions
    with open(pred_path, "r") as f:
        predictions = json.load(f)

    # Load ground truth
    with open(DATA_PATH, "r") as f:
        data = json.load(f)

    print(f"Evaluating {len(predictions)} predictions...")

    # Prepare evaluation tasks
    tasks = []
    for i, item in enumerate(data):
        if str(i) not in predictions:
            continue

        pred_entry = predictions[str(i)]
        if isinstance(pred_entry, str) and "\t----- bird -----\t" in pred_entry:
            pred_sql = pred_entry.split("\t----- bird -----\t")[0].strip()
        else:
            pred_sql = str(pred_entry).strip()

        gt_sql = item["SQL"]
        db_id = item["db_id"]
        db_path = str(DB_ROOT_PATH / db_id / f"{db_id}.sqlite")

        tasks.append((i, pred_sql, gt_sql, db_path, 30.0))

    # Run evaluation
    results = []
    for task in tqdm(tasks, desc="Evaluating"):
        results.append(evaluate_single(task))

    # Calculate accuracy by difficulty
    difficulty_results = {"simple": [], "moderate": [], "challenging": []}
    for i, item in enumerate(data):
        if i < len(results):
            difficulty = item.get("difficulty", "simple")
            difficulty_results[difficulty].append(results[i]["correct"])

    # Print results
    print("\n" + "=" * 70)
    print("GPT-4o BIRD Mini-Dev Benchmark Results")
    print("=" * 70)

    total_correct = sum(r["correct"] for r in results)
    total = len(results)

    print(f"\n{'Difficulty':<15} {'Count':<10} {'Correct':<10} {'Accuracy':<10}")
    print("-" * 45)

    for diff in ["simple", "moderate", "challenging"]:
        count = len(difficulty_results[diff])
        correct = sum(difficulty_results[diff])
        acc = (correct / count * 100) if count > 0 else 0
        print(f"{diff:<15} {count:<10} {correct:<10} {acc:.2f}%")

    print("-" * 45)
    overall_acc = (total_correct / total * 100) if total > 0 else 0
    print(f"{'TOTAL':<15} {total:<10} {total_correct:<10} {overall_acc:.2f}%")
    print("=" * 70)

    # Count errors
    errors = [r for r in results if r["error"]]
    timeouts = [r for r in results if r["error"] == "timeout"]
    print(f"\nErrors: {len(errors)} (Timeouts: {len(timeouts)})")

    # Save results
    results_summary = {
        "model": "gpt-4o",
        "total": total,
        "correct": total_correct,
        "accuracy": overall_acc,
        "by_difficulty": {
            diff: {
                "count": len(difficulty_results[diff]),
                "correct": sum(difficulty_results[diff]),
                "accuracy": (sum(difficulty_results[diff]) / len(difficulty_results[diff]) * 100)
                           if difficulty_results[diff] else 0
            }
            for diff in ["simple", "moderate", "challenging"]
        },
        "errors": len(errors),
        "timeouts": len(timeouts)
    }

    results_path = OUTPUT_DIR / "evaluation_results.json"
    with open(results_path, "w") as f:
        json.dump(results_summary, f, indent=2)

    print(f"\nResults saved to {results_path}")
    return results_summary


def main():
    parser = argparse.ArgumentParser(description="GPT-4o BIRD Benchmark Evaluation")
    parser.add_argument("--generate", action="store_true", help="Generate predictions using GPT-4o")
    parser.add_argument("--evaluate", action="store_true", help="Run evaluation on existing predictions")
    parser.add_argument("--sample", type=int, default=None, help="Only process first N samples (for testing)")
    parser.add_argument("--all", action="store_true", help="Generate predictions and evaluate")

    args = parser.parse_args()

    if args.all or (args.generate and args.evaluate):
        generate_predictions(args.sample)
        create_ground_truth_file()
        run_evaluation()
    elif args.generate:
        generate_predictions(args.sample)
        create_ground_truth_file()
    elif args.evaluate:
        run_evaluation()
    else:
        print("Usage:")
        print("  python run_gpt4o_evaluation.py --generate  # Generate predictions")
        print("  python run_gpt4o_evaluation.py --evaluate  # Evaluate predictions")
        print("  python run_gpt4o_evaluation.py --all       # Generate and evaluate")
        print("  python run_gpt4o_evaluation.py --generate --sample 10  # Test with 10 samples")


if __name__ == "__main__":
    main()
