#!/usr/bin/env python3
"""
BIRD Mini-Dev: Compare Our Pipeline vs GPT-4o Baseline

Runs EX (execution accuracy) evaluation on our predictions and produces
a comparison table against the existing GPT-4o baseline results.
"""

import json
import sqlite3
import argparse
import sys
from pathlib import Path
from tqdm import tqdm
from func_timeout import func_timeout, FunctionTimedOut

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
BIRD_BASE = PROJECT_ROOT / "backend" / "Agents" / "birdmini_benchmark" / "mini_dev"
DATA_PATH = BIRD_BASE / "data" / "bird_mini_dev" / "data" / "mini_dev_sqlite-00000-of-00001.json"
DB_ROOT_PATH = BIRD_BASE / "minidev" / "MINIDEV" / "dev_databases"
BASELINE_RESULTS_PATH = BIRD_BASE / "results" / "evaluation_results.json"
BASELINE_PRED_PATH = BIRD_BASE / "results" / "predict_gpt4o_sqlite.json"


# --- EX Evaluation (adapted from evaluation_ex.py) ---

def execute_sql_query(sql: str, db_path: str):
    """Execute SQL and return result set."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(sql)
    results = cursor.fetchall()
    conn.close()
    return results


def evaluate_single(pred_sql: str, gt_sql: str, db_path: str, timeout: float = 30.0):
    """Evaluate a single prediction using EX metric (set equality)."""
    try:
        pred_result = func_timeout(timeout, execute_sql_query, args=(pred_sql, db_path))
        gt_result = func_timeout(timeout, execute_sql_query, args=(gt_sql, db_path))
        correct = 1 if set(pred_result) == set(gt_result) else 0
        return {"correct": correct, "error": None}
    except FunctionTimedOut:
        return {"correct": 0, "error": "timeout"}
    except Exception as e:
        return {"correct": 0, "error": str(e)}


def run_ex_evaluation(pred_path: str) -> dict:
    """Run EX evaluation on a predictions file. Returns per-item results + summary."""
    with open(pred_path, "r") as f:
        predictions = json.load(f)

    with open(DATA_PATH, "r") as f:
        data = json.load(f)

    print(f"Evaluating {len(predictions)} predictions...")

    results = []
    difficulty_results = {"simple": [], "moderate": [], "challenging": []}

    for i, item in enumerate(tqdm(data, desc="Evaluating EX")):
        if str(i) not in predictions:
            results.append({"idx": i, "correct": 0, "error": "missing_prediction"})
            continue

        pred_entry = predictions[str(i)]
        if isinstance(pred_entry, str) and "\t----- bird -----\t" in pred_entry:
            pred_sql = pred_entry.split("\t----- bird -----\t")[0].strip()
        else:
            pred_sql = str(pred_entry).strip()

        gt_sql = item["SQL"]
        db_id = item["db_id"]
        db_path = str(DB_ROOT_PATH / db_id / f"{db_id}.sqlite")

        result = evaluate_single(pred_sql, gt_sql, db_path)
        result["idx"] = i
        result["pred_sql"] = pred_sql
        result["gt_sql"] = gt_sql
        result["db_id"] = db_id
        result["difficulty"] = item.get("difficulty", "simple")
        result["question"] = item["question"]
        results.append(result)

        difficulty = item.get("difficulty", "simple")
        difficulty_results[difficulty].append(result["correct"])

    # Build summary
    total = len(results)
    total_correct = sum(r["correct"] for r in results)
    summary = {
        "total": total,
        "correct": total_correct,
        "accuracy": (total_correct / total * 100) if total > 0 else 0,
        "by_difficulty": {},
        "errors": sum(1 for r in results if r["error"]),
        "timeouts": sum(1 for r in results if r.get("error") == "timeout"),
    }
    for diff in ["simple", "moderate", "challenging"]:
        count = len(difficulty_results[diff])
        correct = sum(difficulty_results[diff])
        summary["by_difficulty"][diff] = {
            "count": count,
            "correct": correct,
            "accuracy": (correct / count * 100) if count > 0 else 0
        }

    return {"results": results, "summary": summary}


# --- Comparison ---

def load_baseline() -> dict:
    """Load existing GPT-4o baseline results."""
    with open(BASELINE_RESULTS_PATH, "r") as f:
        return json.load(f)


def print_comparison(our_summary: dict, baseline: dict, model: str = "our pipeline"):
    """Print markdown comparison table."""
    print("\n## EX Accuracy Comparison: Our Pipeline vs GPT-4o Baseline\n")
    print(f"| Difficulty | GPT-4o Baseline | {model} | Delta |")
    print("|------------|----------------:|----------------:|------:|")

    for diff in ["simple", "moderate", "challenging"]:
        base_acc = baseline["by_difficulty"][diff]["accuracy"]
        our_acc = our_summary["by_difficulty"][diff]["accuracy"]
        delta = our_acc - base_acc
        sign = "+" if delta >= 0 else ""
        count = our_summary["by_difficulty"][diff]["count"]
        print(f"| {diff:<10} | {base_acc:>14.1f}% | {our_acc:>14.1f}% | {sign}{delta:>4.1f}% |")

    base_total = baseline["accuracy"]
    our_total = our_summary["accuracy"]
    delta_total = our_total - base_total
    sign = "+" if delta_total >= 0 else ""
    print(f"| **TOTAL**  | **{base_total:>12.1f}%** | **{our_total:>12.1f}%** | **{sign}{delta_total:.1f}%** |")
    print(f"\nOur pipeline: {our_summary['correct']}/{our_summary['total']} correct")
    print(f"GPT-4o baseline: {baseline['correct']}/{baseline['total']} correct")
    print(f"Errors: {our_summary['errors']} (Timeouts: {our_summary['timeouts']})")


def find_disagreements(our_results: list, baseline_pred_path: str = None) -> list:
    """Find questions where our pipeline and baseline disagree."""
    if not baseline_pred_path or not Path(baseline_pred_path).exists():
        return []

    with open(baseline_pred_path, "r") as f:
        baseline_preds = json.load(f)

    with open(DATA_PATH, "r") as f:
        data = json.load(f)

    disagreements = []
    for r in our_results:
        idx = r["idx"]
        baseline_entry = baseline_preds.get(str(idx))
        if not baseline_entry:
            continue

        if isinstance(baseline_entry, str) and "\t----- bird -----\t" in baseline_entry:
            baseline_sql = baseline_entry.split("\t----- bird -----\t")[0].strip()
        else:
            baseline_sql = str(baseline_entry).strip()

        # Evaluate baseline on the same question
        db_path = str(DB_ROOT_PATH / r["db_id"] / f"{r['db_id']}.sqlite")
        baseline_result = evaluate_single(baseline_sql, r["gt_sql"], db_path)

        ours_correct = r["correct"]
        base_correct = baseline_result["correct"]

        if ours_correct != base_correct:
            disagreements.append({
                "idx": idx,
                "question": r["question"],
                "db_id": r["db_id"],
                "difficulty": r["difficulty"],
                "ours_correct": bool(ours_correct),
                "baseline_correct": bool(base_correct),
                "our_sql": r["pred_sql"][:200],
                "baseline_sql": baseline_sql[:200],
                "gold_sql": r["gt_sql"][:200],
            })

    return disagreements


def categorize_errors(results: list) -> dict:
    """Categorize errors from our pipeline."""
    categories = {
        "timeout": [],
        "syntax_error": [],
        "no_such_table": [],
        "no_such_column": [],
        "wrong_result": [],
        "other_error": [],
    }

    for r in results:
        if r["correct"]:
            continue
        error = r.get("error", "")
        if error == "timeout":
            categories["timeout"].append(r["idx"])
        elif error and "syntax" in error.lower():
            categories["syntax_error"].append(r["idx"])
        elif error and "no such table" in error.lower():
            categories["no_such_table"].append(r["idx"])
        elif error and "no such column" in error.lower():
            categories["no_such_column"].append(r["idx"])
        elif error:
            categories["other_error"].append(r["idx"])
        else:
            categories["wrong_result"].append(r["idx"])

    return categories


def print_error_summary(categories: dict):
    """Print error categorization summary."""
    print("\n## Error Categorization\n")
    print(f"| Category | Count | Example Indices |")
    print(f"|----------|------:|-----------------|")
    for cat, indices in categories.items():
        examples = ", ".join(str(i) for i in indices[:5])
        if len(indices) > 5:
            examples += "..."
        print(f"| {cat:<16} | {len(indices):>5} | {examples} |")

    total_errors = sum(len(v) for v in categories.values())
    print(f"| **Total Errors** | **{total_errors:>3}** | |")


def main():
    parser = argparse.ArgumentParser(description="Compare BIRD evaluation results")
    parser.add_argument(
        "--pred_path", type=str,
        default="backend/evaluation/results/predict_our_pipeline.json",
        help="Path to our predictions JSON"
    )
    parser.add_argument(
        "--baseline_pred_path", type=str,
        default=str(BASELINE_PRED_PATH),
        help="Path to baseline predictions JSON (for per-instance comparison)"
    )
    parser.add_argument(
        "--output_path", type=str,
        default="backend/evaluation/results/comparison_report.json",
        help="Output path for detailed comparison JSON"
    )
    args = parser.parse_args()

    pred_path = Path(args.pred_path)
    if not pred_path.exists():
        print(f"Predictions file not found: {pred_path}")
        print("Run eval_bird_pipeline.py first to generate predictions.")
        sys.exit(1)

    # Run EX evaluation
    eval_data = run_ex_evaluation(str(pred_path))
    our_summary = eval_data["summary"]
    our_results = eval_data["results"]

    # Load baseline
    baseline = load_baseline()

    # Print comparison
    print_comparison(our_summary, baseline)

    # Error categorization
    categories = categorize_errors(our_results)
    print_error_summary(categories)

    # Per-instance disagreements
    disagreements = find_disagreements(our_results, args.baseline_pred_path)
    if disagreements:
        wins = [d for d in disagreements if d["ours_correct"]]
        losses = [d for d in disagreements if d["baseline_correct"]]
        print(f"\n## Disagreements: {len(disagreements)} total")
        print(f"  Our wins (we got right, baseline wrong): {len(wins)}")
        print(f"  Our losses (baseline got right, we wrong): {len(losses)}")

        if wins:
            print(f"\n### Sample Wins (first 5):")
            for d in wins[:5]:
                print(f"  [{d['idx']}] ({d['difficulty']}) {d['question'][:80]}")

        if losses:
            print(f"\n### Sample Losses (first 5):")
            for d in losses[:5]:
                print(f"  [{d['idx']}] ({d['difficulty']}) {d['question'][:80]}")

    # Save full report
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "our_summary": our_summary,
        "baseline_summary": baseline,
        "error_categories": {k: len(v) for k, v in categories.items()},
        "disagreements_count": len(disagreements),
        "our_wins": len([d for d in disagreements if d["ours_correct"]]),
        "our_losses": len([d for d in disagreements if d["baseline_correct"]]),
        "disagreements": disagreements[:50],  # save first 50 for review
    }
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nDetailed report saved to {output_path}")


if __name__ == "__main__":
    main()
