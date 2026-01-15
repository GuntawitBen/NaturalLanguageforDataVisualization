import json
import sqlite3
import time
from text_to_sql_engine import TextToSQLEngine
from tqdm import tqdm

def execute_sql(db_id, sql, db_base_path="minidev/MINIDEV/dev_databases"):
    """Execute SQL and return results"""
    db_path = f"{db_base_path}/{db_id}/{db_id}.sqlite"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(sql)
        result = cursor.fetchall()
        conn.close()
        return result, None
    except Exception as e:
        return None, str(e)

def clean_sql(sql):
    """Remove markdown code blocks"""
    sql = sql.strip()
    if sql.startswith("```sql"):
        sql = sql[6:]
    if sql.startswith("```"):
        sql = sql[3:]
    if sql.endswith("```"):
        sql = sql[:-3]
    return sql.strip()

# Load dataset
with open('data/bird_mini_dev/data/mini_dev_sqlite-00000-of-00001.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Initialize engine
engine = TextToSQLEngine()

# Evaluation metrics
results = {
    'total': 0,
    'correct': 0,
    'execution_errors': 0,
    'wrong_results': 0,
    'examples': []
}

# Evaluate first N examples (start small to save API costs)
NUM_EXAMPLES = 10  # Start with 10, increase later

print(f"Evaluating {NUM_EXAMPLES} examples...")
print("="*60)

for i in tqdm(range(NUM_EXAMPLES)):
    example = data[i]

    question = example['question']
    db_id = example['db_id']
    ground_truth_sql = example['SQL']
    evidence = example.get('evidence')

    # Generate SQL
    try:
        predicted_sql = engine.generate_sql(question, db_id, evidence)
        predicted_sql = clean_sql(predicted_sql)
    except Exception as e:
        results['execution_errors'] += 1
        results['examples'].append({
            'id': i,
            'question': question,
            'error': f"Generation error: {str(e)}",
            'status': 'generation_error'
        })
        results['total'] += 1
        continue

    # Execute both SQLs
    gt_result, gt_error = execute_sql(db_id, ground_truth_sql)
    pred_result, pred_error = execute_sql(db_id, predicted_sql)

    results['total'] += 1

    if pred_error:
        results['execution_errors'] += 1
        results['examples'].append({
            'id': i,
            'question': question,
            'predicted_sql': predicted_sql,
            'error': pred_error,
            'status': 'execution_error'
        })
    elif gt_result == pred_result:
        results['correct'] += 1
        results['examples'].append({
            'id': i,
            'question': question,
            'status': 'correct'
        })
    else:
        results['wrong_results'] += 1
        results['examples'].append({
            'id': i,
            'question': question,
            'predicted_sql': predicted_sql,
            'ground_truth_sql': ground_truth_sql,
            'predicted_result': pred_result,
            'ground_truth_result': gt_result,
            'status': 'wrong_result'
        })

    # Small delay to avoid rate limits
    time.sleep(0.5)

# Print results
print("\n" + "="*60)
print("EVALUATION RESULTS")
print("="*60)
print(f"Total Examples: {results['total']}")
print(f"Correct: {results['correct']} ({results['correct']/results['total']*100:.2f}%)")
print(f"Execution Errors: {results['execution_errors']}")
print(f"Wrong Results: {results['wrong_results']}")
print(f"\nExecution Accuracy (EX): {results['correct']/results['total']*100:.2f}%")

# Save detailed results
with open('evaluation_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("\nDetailed results saved to: evaluation_results.json")