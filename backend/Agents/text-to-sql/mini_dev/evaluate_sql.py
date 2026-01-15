import json
import sqlite3
from text_to_sql_engine import TextToSQLEngine

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
    """Remove markdown code blocks if present"""
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

# Test first example
example = data[0]
question = example['question']
db_id = example['db_id']
ground_truth_sql = example['SQL']

print(f"Question: {question}")
print(f"Database: {db_id}")
print("\n" + "="*50)

# Generate SQL
engine = TextToSQLEngine()
predicted_sql = engine.generate_sql(question, db_id, example.get('evidence'))
predicted_sql = clean_sql(predicted_sql)

print("Ground Truth SQL:")
print(ground_truth_sql)
print("\n" + "="*50)
print("Predicted SQL:")
print(predicted_sql)
print("\n" + "="*50)

# Execute both
print("Executing Ground Truth...")
gt_result, gt_error = execute_sql(db_id, ground_truth_sql)
if gt_error:
    print(f"Error: {gt_error}")
else:
    print(f"Result: {gt_result}")

print("\n" + "="*50)
print("Executing Predicted SQL...")
pred_result, pred_error = execute_sql(db_id, predicted_sql)
if pred_error:
    print(f"Error: {pred_error}")
else:
    print(f"Result: {pred_result}")

print("\n" + "="*50)
# Compare results
if gt_result is not None and pred_result is not None:
    if gt_result == pred_result:
        print("✓ EXACT MATCH! Results are identical.")
    else:
        print("✗ Results differ.")
        print(f"Ground Truth: {gt_result}")
        print(f"Predicted: {pred_result}")
else:
    print("Could not compare - execution error occurred")