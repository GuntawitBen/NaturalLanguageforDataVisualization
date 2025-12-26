"""
Test Metadata Extraction System
Demonstrates comprehensive metadata extraction and analysis
"""
import os
import csv
from database import create_dataset, get_dataset, delete_dataset
from utils.metadata_extractor import (
    extract_basic_metadata,
    extract_comprehensive_metadata,
    extract_column_statistics,
    compare_metadata,
    save_metadata_snapshot,
    get_metadata_history,
    format_metadata_for_display
)

# ============================================================================
# Generate Test Data
# ============================================================================

def create_sample_csv():
    """Create a sample CSV with mixed data types"""
    file_path = "test_csvs/metadata_test.csv"
    os.makedirs("test_csvs", exist_ok=True)

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Header with different data types
        writer.writerow(['id', 'product_name', 'price', 'stock', 'is_active', 'created_date'])

        # Sample data
        products = [
            (1, 'Widget A', 19.99, 100, True, '2024-01-15'),
            (2, 'Widget B', 29.99, 50, True, '2024-02-20'),
            (3, 'Gadget X', 49.99, 75, True, '2024-03-10'),
            (4, 'Gadget Y', 39.99, 0, False, '2024-03-15'),
            (5, 'Tool Alpha', 99.99, 25, True, '2024-04-01'),
            (6, 'Tool Beta', 149.99, 10, True, '2024-04-15'),
            (7, 'Device Pro', 299.99, 5, True, '2024-05-01'),
            (8, 'Device Lite', 199.99, 15, True, '2024-05-10'),
            (9, 'Service Pack', 9.99, 500, True, '2024-06-01'),
            (10, 'Premium Plan', 499.99, 3, True, '2024-06-15'),
        ]

        for row in products:
            writer.writerow(row)

    print(f"[OK] Created sample CSV: {file_path}")
    return file_path

# ============================================================================
# Test Functions
# ============================================================================

def test_basic_metadata_extraction(table_name: str):
    """Test basic metadata extraction"""
    print("\n" + "="*80)
    print("TEST 1: Basic Metadata Extraction")
    print("="*80)

    metadata = extract_basic_metadata(table_name)

    print(f"\n✓ Row count: {metadata['row_count']}")
    print(f"✓ Column count: {metadata['column_count']}")
    print(f"✓ Table size: {metadata['table_size_bytes']:,} bytes")

    print(f"\n✓ Columns:")
    for col in metadata['columns_info']:
        nullable = "NULL" if col['nullable'] else "NOT NULL"
        print(f"  - {col['name']:<20} {col['type']:<15} {nullable}")

    return metadata

def test_column_statistics(table_name: str, columns_info: list):
    """Test column-level statistics extraction"""
    print("\n" + "="*80)
    print("TEST 2: Column Statistics Extraction")
    print("="*80)

    for col_info in columns_info:
        col_name = col_info['name']
        col_type = col_info['type']

        print(f"\n✓ Extracting statistics for: {col_name} ({col_type})")

        stats = extract_column_statistics(table_name, col_name, col_type)

        print(f"  - Distinct values: {stats.get('distinct_count', 'N/A')}")
        print(f"  - Null values: {stats.get('null_count', 0)}")

        if 'min' in stats:
            print(f"  - Min: {stats['min']}")
            print(f"  - Max: {stats['max']}")
            print(f"  - Mean: {stats.get('mean', 'N/A')}")
            print(f"  - Median: {stats.get('median', 'N/A')}")

        if 'min_length' in stats:
            print(f"  - Min length: {stats['min_length']}")
            print(f"  - Max length: {stats['max_length']}")
            print(f"  - Avg length: {stats.get('avg_length', 'N/A'):.1f}")

        if 'top_values' in stats:
            print(f"  - Top values:")
            for tv in stats['top_values'][:3]:
                print(f"    • {tv['value']}: {tv['count']} times")

        if 'true_count' in stats:
            print(f"  - True: {stats['true_count']}")
            print(f"  - False: {stats['false_count']}")

def test_comprehensive_metadata(table_name: str):
    """Test comprehensive metadata extraction with statistics"""
    print("\n" + "="*80)
    print("TEST 3: Comprehensive Metadata Extraction")
    print("="*80)

    print("\n[INFO] Extracting comprehensive metadata...")
    metadata = extract_comprehensive_metadata(table_name, include_stats=True)

    print("\n✓ Basic Information:")
    print(f"  - Table: {metadata['table_name']}")
    print(f"  - Rows: {metadata['row_count']:,}")
    print(f"  - Columns: {metadata['column_count']}")

    print("\n✓ Data Quality:")
    dq = metadata['data_quality']
    print(f"  - Completeness: {dq['completeness_percentage']:.2f}%")
    print(f"  - Total cells: {dq['total_cells']:,}")
    print(f"  - Null cells: {dq['null_cells']}")

    print("\n✓ Column Statistics Available:")
    for col_stat in metadata['column_statistics']:
        print(f"  - {col_stat['column_name']}: {col_stat['distinct_count']} distinct values")

    return metadata

def test_metadata_snapshot(dataset_id: str, metadata: dict):
    """Test metadata snapshot functionality"""
    print("\n" + "="*80)
    print("TEST 4: Metadata Snapshot System")
    print("="*80)

    # Save snapshot
    print("\n[INFO] Saving metadata snapshot...")
    success = save_metadata_snapshot(dataset_id, metadata)

    if success:
        print("✓ Snapshot saved successfully")
    else:
        print("✗ Failed to save snapshot")
        return

    # Retrieve history
    print("\n[INFO] Retrieving metadata history...")
    history = get_metadata_history(dataset_id)

    print(f"✓ Found {len(history)} snapshot(s):")
    for i, snapshot in enumerate(history, 1):
        print(f"  {i}. Time: {snapshot['snapshot_time']}")
        print(f"     Rows: {snapshot['metadata']['row_count']:,}")
        print(f"     Columns: {snapshot['metadata']['column_count']}")

def test_metadata_comparison(metadata1: dict, metadata2: dict):
    """Test metadata comparison"""
    print("\n" + "="*80)
    print("TEST 5: Metadata Comparison")
    print("="*80)

    differences = compare_metadata(metadata1, metadata2)

    print(f"\n✓ Has changes: {differences['has_changes']}")

    if differences['has_changes']:
        print(f"  - Row count difference: {differences['row_count_diff']}")
        print(f"  - Column count difference: {differences['column_count_diff']}")

        if differences['added_columns']:
            print(f"  - Added columns: {', '.join(differences['added_columns'])}")

        if differences['removed_columns']:
            print(f"  - Removed columns: {', '.join(differences['removed_columns'])}")

        if differences['type_changes']:
            print(f"  - Type changes:")
            for change in differences['type_changes']:
                print(f"    • {change['column']}: {change['old_type']} → {change['new_type']}")
    else:
        print("  No differences detected")

def test_metadata_formatting(metadata: dict):
    """Test metadata formatting for display"""
    print("\n" + "="*80)
    print("TEST 6: Metadata Formatting")
    print("="*80)

    formatted = format_metadata_for_display(metadata)
    print(formatted)

# ============================================================================
# Main Test Runner
# ============================================================================

if __name__ == "__main__":
    print("\n")
    print("="*80)
    print("METADATA EXTRACTION SYSTEM TEST SUITE")
    print("="*80)

    dataset_id = None

    try:
        # 1. Create sample CSV
        print("\n[SETUP] Creating sample dataset...")
        csv_path = create_sample_csv()

        # 2. Upload dataset
        print("\n[SETUP] Uploading dataset to DuckDB...")
        dataset_id = create_dataset(
            user_id="test_user@example.com",
            dataset_name="Metadata Test Dataset",
            original_filename="metadata_test.csv",
            file_path=csv_path,
            description="Test dataset for metadata extraction",
            extract_stats=False  # We'll extract manually for testing
        )

        if not dataset_id:
            print("\n[ERROR] Failed to create dataset")
            exit(1)

        dataset = get_dataset(dataset_id)
        table_name = dataset['table_name']

        print(f"✓ Dataset created: {dataset_id}")
        print(f"✓ Table name: {table_name}")

        # Run tests
        basic_metadata = test_basic_metadata_extraction(table_name)

        test_column_statistics(table_name, basic_metadata['columns_info'])

        comprehensive_metadata = test_comprehensive_metadata(table_name)

        test_metadata_snapshot(dataset_id, comprehensive_metadata)

        # Create a second snapshot with same data (no changes)
        print("\n[INFO] Creating second snapshot (same data)...")
        save_metadata_snapshot(dataset_id, comprehensive_metadata)

        test_metadata_comparison(comprehensive_metadata, comprehensive_metadata)

        test_metadata_formatting(comprehensive_metadata)

        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print("\n✓ All tests completed successfully!")
        print("\nMetadata System Features Tested:")
        print("  1. Basic metadata extraction (fast)")
        print("  2. Column-level statistics (type-specific)")
        print("  3. Comprehensive metadata with quality metrics")
        print("  4. Metadata snapshot storage")
        print("  5. Metadata history retrieval")
        print("  6. Metadata comparison")
        print("  7. Formatted output for display")
        print("\n" + "="*80)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        if dataset_id:
            print("\n[CLEANUP] Removing test dataset...")
            delete_dataset(dataset_id, hard_delete=True)
            print("✓ Cleanup complete")

        # Remove test CSV
        if os.path.exists("test_csvs/metadata_test.csv"):
            os.remove("test_csvs/metadata_test.csv")
            print("✓ Test CSV removed")

    print()
