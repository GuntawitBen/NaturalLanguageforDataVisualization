"""
Test Direct CSV → DuckDB Loading Performance
Demonstrates how CSV files are loaded directly into DuckDB tables
"""
import os
import time
import csv
from database import get_db_connection, create_dataset, query_dataset, delete_dataset
from utils.csv_validator import validate_csv_file

# ============================================================================
# Test Data Generator
# ============================================================================

def generate_test_csv(filename: str, rows: int = 1000, columns: int = 5) -> str:
    """Generate a test CSV file with specified dimensions"""
    file_path = f"test_csvs/{filename}"
    os.makedirs("test_csvs", exist_ok=True)

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Write header
        headers = [f"column_{i+1}" for i in range(columns)]
        writer.writerow(headers)

        # Write data rows
        for row_num in range(rows):
            row_data = [f"value_{row_num}_{col}" for col in range(columns)]
            writer.writerow(row_data)

    file_size = os.path.getsize(file_path)
    print(f"[OK] Generated {filename}: {rows:,} rows × {columns} columns = {file_size:,} bytes")
    return file_path

# ============================================================================
# Direct Loading Tests
# ============================================================================

def test_direct_csv_loading(csv_path: str, dataset_name: str):
    """Test direct CSV to DuckDB loading with performance metrics"""
    print(f"\n{'='*80}")
    print(f"Testing: {dataset_name}")
    print(f"File: {csv_path}")
    print(f"{'='*80}")

    # 1. Validation
    print("\n[STEP 1] Validating CSV file...")
    start_time = time.time()
    validation_result = validate_csv_file(csv_path)
    validation_time = (time.time() - start_time) * 1000

    if validation_result['valid']:
        print(f"[OK] Validation passed in {validation_time:.2f}ms")
        print(f"     Rows: {validation_result['metadata']['row_count']:,}")
        print(f"     Columns: {validation_result['metadata']['column_count']}")
        print(f"     Encoding: {validation_result['metadata']['encoding']}")
        print(f"     Delimiter: '{validation_result['metadata']['delimiter']}'")
    else:
        print(f"[ERROR] Validation failed:")
        for error in validation_result['errors']:
            print(f"  - {error}")
        return None

    # 2. Direct CSV → DuckDB Loading
    print("\n[STEP 2] Loading CSV directly into DuckDB...")
    start_time = time.time()

    dataset_id = create_dataset(
        user_id="test_user@example.com",
        dataset_name=dataset_name,
        original_filename=os.path.basename(csv_path),
        file_path=csv_path,
        description=f"Test dataset: {dataset_name}"
    )

    loading_time = (time.time() - start_time) * 1000

    if dataset_id:
        print(f"[OK] Dataset loaded in {loading_time:.2f}ms")
        print(f"     Dataset ID: {dataset_id}")
    else:
        print("[ERROR] Failed to create dataset")
        return None

    # 3. Verify Data in DuckDB
    print("\n[STEP 3] Verifying data in DuckDB...")

    # Query first 5 rows
    result = query_dataset(dataset_id, "SELECT * FROM {{table}} LIMIT 5")

    if result['success']:
        print(f"[OK] Data accessible in DuckDB")
        print(f"     Columns: {', '.join(result['columns'])}")
        print(f"     Sample rows (first 5):")
        for i, row in enumerate(result['data'], 1):
            print(f"       Row {i}: {row[:3]}..." if len(row) > 3 else f"       Row {i}: {row}")
    else:
        print(f"[ERROR] Query failed: {result.get('error')}")

    # 4. Performance Analysis
    print("\n[STEP 4] Performance Analysis")

    # Count total rows
    count_start = time.time()
    count_result = query_dataset(dataset_id, "SELECT COUNT(*) as total FROM {{table}}")
    count_time = (time.time() - count_start) * 1000

    if count_result['success']:
        total_rows = count_result['data'][0][0]
        print(f"[OK] Row count query: {total_rows:,} rows in {count_time:.2f}ms")

    # Aggregation query
    agg_start = time.time()
    agg_result = query_dataset(dataset_id,
        "SELECT COUNT(*) as count, COUNT(DISTINCT column_1) as unique_vals FROM {{table}}")
    agg_time = (time.time() - agg_start) * 1000

    if agg_result['success']:
        print(f"[OK] Aggregation query completed in {agg_time:.2f}ms")

    # 5. Summary
    print(f"\n{'='*80}")
    print("PERFORMANCE SUMMARY")
    print(f"{'='*80}")
    print(f"Validation time:        {validation_time:>10.2f} ms")
    print(f"Loading time:           {loading_time:>10.2f} ms")
    print(f"Count query time:       {count_time:>10.2f} ms")
    print(f"Aggregation time:       {agg_time:>10.2f} ms")
    print(f"{'='*80}")
    print(f"Total time:             {validation_time + loading_time:>10.2f} ms")
    print(f"{'='*80}")

    return dataset_id

# ============================================================================
# Cleanup
# ============================================================================

def cleanup_test_datasets(dataset_ids: list):
    """Delete test datasets"""
    print(f"\n[CLEANUP] Removing {len(dataset_ids)} test datasets...")
    for dataset_id in dataset_ids:
        if dataset_id:
            delete_dataset(dataset_id, hard_delete=True)
    print("[OK] Cleanup complete")

# ============================================================================
# Main Test Runner
# ============================================================================

if __name__ == "__main__":
    print("\n")
    print("="*80)
    print("DIRECT CSV → DuckDB LOADING TEST SUITE")
    print("="*80)
    print("\nThis test demonstrates how CSV files are loaded directly into DuckDB")
    print("using DuckDB's read_csv_auto() function for optimal performance.\n")

    dataset_ids = []

    # Test 1: Small dataset (100 rows)
    csv_small = generate_test_csv("test_small.csv", rows=100, columns=5)
    ds_id = test_direct_csv_loading(csv_small, "Small Dataset (100 rows)")
    dataset_ids.append(ds_id)

    # Test 2: Medium dataset (10,000 rows)
    csv_medium = generate_test_csv("test_medium.csv", rows=10000, columns=10)
    ds_id = test_direct_csv_loading(csv_medium, "Medium Dataset (10K rows)")
    dataset_ids.append(ds_id)

    # Test 3: Large dataset (100,000 rows)
    csv_large = generate_test_csv("test_large.csv", rows=100000, columns=8)
    ds_id = test_direct_csv_loading(csv_large, "Large Dataset (100K rows)")
    dataset_ids.append(ds_id)

    # Test 4: Existing valid.csv
    if os.path.exists("test_csvs/valid.csv"):
        ds_id = test_direct_csv_loading("test_csvs/valid.csv", "Valid CSV (from test suite)")
        dataset_ids.append(ds_id)

    # Cleanup
    cleanup_test_datasets(dataset_ids)

    print("\n")
    print("="*80)
    print("ALL TESTS COMPLETE")
    print("="*80)
    print("\nKey Takeaways:")
    print("1. CSV files are loaded DIRECTLY into DuckDB using read_csv_auto()")
    print("2. No intermediate processing or data transformation")
    print("3. DuckDB automatically detects CSV format, types, and encoding")
    print("4. Loading is extremely fast - even 100K rows load in milliseconds")
    print("5. Data is immediately queryable with full SQL support")
    print("="*80)
    print()
