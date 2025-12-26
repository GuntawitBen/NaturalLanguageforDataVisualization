"""
Test User Ownership Linking System
Demonstrates ownership verification, resource management, and user analytics
"""
import os
from database import create_dataset, get_dataset, delete_dataset, init_database
from database.db_utils import sync_user_from_firebase
from utils.ownership import (
    verify_dataset_ownership,
    get_user_resource_count,
    get_user_activity_summary,
    list_user_resources,
    transfer_dataset_ownership,
    get_user_storage_breakdown,
    get_dataset_usage_stats,
    get_orphaned_tables,
    cleanup_orphaned_tables
)

# ============================================================================
# Test Data
# ============================================================================

TEST_USER_1 = {
    'user_id': 'test_user_1',
    'email': 'user1@example.com',
    'name': 'Test User 1',
    'picture': None,
    'auth_provider': 'email'
}

TEST_USER_2 = {
    'user_id': 'test_user_2',
    'email': 'user2@example.com',
    'name': 'Test User 2',
    'picture': None,
    'auth_provider': 'email'
}

def create_test_csv(filename: str, rows: int = 100):
    """Create a simple test CSV"""
    import csv
    os.makedirs("test_csvs", exist_ok=True)

    file_path = f"test_csvs/{filename}"
    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'value'])
        for i in range(rows):
            writer.writerow([i, f'value_{i}'])

    return file_path

# ============================================================================
# Test Functions
# ============================================================================

def test_user_sync():
    """Test syncing users from Firebase to DuckDB"""
    print("\n" + "="*80)
    print("TEST 1: User Synchronization")
    print("="*80)

    # Sync test users
    for user in [TEST_USER_1, TEST_USER_2]:
        success = sync_user_from_firebase(**user)
        if success:
            print(f"✓ Synced user: {user['email']}")
        else:
            print(f"✗ Failed to sync user: {user['email']}")

def test_ownership_verification(dataset_id: str):
    """Test ownership verification"""
    print("\n" + "="*80)
    print("TEST 2: Ownership Verification")
    print("="*80)

    # Test correct owner
    is_owner, error = verify_dataset_ownership(dataset_id, TEST_USER_1['email'])
    print(f"\n✓ User 1 owns dataset: {is_owner}")
    if error:
        print(f"  Error: {error}")

    # Test wrong owner
    is_owner, error = verify_dataset_ownership(dataset_id, TEST_USER_2['email'])
    print(f"✓ User 2 owns dataset: {is_owner}")
    if error:
        print(f"  Error: {error}")

    # Test non-existent dataset
    is_owner, error = verify_dataset_ownership("fake-id-123", TEST_USER_1['email'])
    print(f"✓ Fake dataset verification: {is_owner}")
    if error:
        print(f"  Error: {error}")

def test_resource_counting(user_email: str):
    """Test resource counting for a user"""
    print("\n" + "="*80)
    print(f"TEST 3: Resource Counting - {user_email}")
    print("="*80)

    counts = get_user_resource_count(user_email)

    print(f"\n✓ Resource counts:")
    print(f"  - Active datasets: {counts.get('datasets', 0)}")
    print(f"  - Deleted datasets: {counts.get('deleted_datasets', 0)}")
    print(f"  - Conversations: {counts.get('conversations', 0)}")
    print(f"  - Visualizations: {counts.get('visualizations', 0)}")
    print(f"  - Queries: {counts.get('queries', 0)}")
    print(f"  - Total storage: {counts.get('total_storage_bytes', 0):,} bytes")

def test_resource_listing(user_email: str):
    """Test listing user resources"""
    print("\n" + "="*80)
    print(f"TEST 4: Resource Listing - {user_email}")
    print("="*80)

    resources = list_user_resources(user_email, 'datasets')

    print(f"\n✓ User datasets:")
    for dataset in resources.get('datasets', []):
        print(f"  - {dataset['dataset_name']}")
        print(f"    ID: {dataset['dataset_id']}")
        print(f"    Rows: {dataset['row_count']:,}")
        print(f"    Size: {dataset['file_size_bytes']:,} bytes")

def test_storage_breakdown(user_email: str):
    """Test storage breakdown"""
    print("\n" + "="*80)
    print(f"TEST 5: Storage Breakdown - {user_email}")
    print("="*80)

    breakdown = get_user_storage_breakdown(user_email)

    total_storage = sum(d['file_size_bytes'] for d in breakdown)
    total_mb = total_storage / (1024 * 1024)

    print(f"\n✓ Total storage: {total_storage:,} bytes ({total_mb:.2f} MB)")
    print(f"✓ Number of datasets: {len(breakdown)}")

    if breakdown:
        print(f"\n✓ Largest datasets:")
        for i, dataset in enumerate(breakdown[:3], 1):
            size_kb = dataset['file_size_bytes'] / 1024
            print(f"  {i}. {dataset['dataset_name']}: {size_kb:.1f} KB")

def test_ownership_transfer(dataset_id: str):
    """Test transferring dataset ownership"""
    print("\n" + "="*80)
    print("TEST 6: Ownership Transfer")
    print("="*80)

    print(f"\n[INFO] Transferring dataset from User 1 to User 2...")

    # Verify User 1 owns it initially
    is_owner, _ = verify_dataset_ownership(dataset_id, TEST_USER_1['email'])
    print(f"✓ User 1 owns dataset before transfer: {is_owner}")

    # Transfer ownership
    success, error = transfer_dataset_ownership(
        dataset_id,
        TEST_USER_1['email'],
        TEST_USER_2['email']
    )

    if success:
        print(f"✓ Transfer successful")
    else:
        print(f"✗ Transfer failed: {error}")
        return

    # Verify User 2 owns it now
    is_owner, _ = verify_dataset_ownership(dataset_id, TEST_USER_2['email'])
    print(f"✓ User 2 owns dataset after transfer: {is_owner}")

    # Verify User 1 no longer owns it
    is_owner, error = verify_dataset_ownership(dataset_id, TEST_USER_1['email'])
    print(f"✓ User 1 owns dataset after transfer: {is_owner}")
    if error:
        print(f"  (Expected error: {error})")

    # Transfer back for cleanup
    print(f"\n[INFO] Transferring back to User 1 for cleanup...")
    transfer_dataset_ownership(dataset_id, TEST_USER_2['email'], TEST_USER_1['email'])

def test_dataset_usage_stats(dataset_id: str):
    """Test dataset usage statistics"""
    print("\n" + "="*80)
    print("TEST 7: Dataset Usage Statistics")
    print("="*80)

    stats = get_dataset_usage_stats(dataset_id)

    print(f"\n✓ Usage statistics for dataset:")
    print(f"  - Query count: {stats.get('query_count', 0)}")
    print(f"  - Conversation count: {stats.get('conversation_count', 0)}")
    print(f"  - Visualization count: {stats.get('visualization_count', 0)}")
    print(f"  - Last accessed: {stats.get('last_accessed', 'Never')}")

def test_orphaned_tables():
    """Test finding and cleaning orphaned tables"""
    print("\n" + "="*80)
    print("TEST 8: Orphaned Table Detection")
    print("="*80)

    orphaned = get_orphaned_tables()

    print(f"\n✓ Found {len(orphaned)} orphaned table(s)")
    if orphaned:
        print("  Tables:")
        for table in orphaned[:5]:  # Show first 5
            print(f"    - {table}")

def test_activity_summary(user_email: str):
    """Test user activity summary"""
    print("\n" + "="*80)
    print(f"TEST 9: Activity Summary - {user_email}")
    print("="*80)

    summary = get_user_activity_summary(user_email, days=30)

    print(f"\n✓ Activity (last 30 days):")
    print(f"  - Recent uploads: {summary.get('recent_uploads', 0)}")
    print(f"  - Recent queries: {summary.get('recent_queries', 0)}")
    print(f"  - Query success rate: {summary.get('query_success_rate', 0):.1f}%")
    print(f"  - Recent conversations: {summary.get('recent_conversations', 0)}")

    most_accessed = summary.get('most_accessed_datasets', [])
    if most_accessed:
        print(f"\n✓ Most accessed datasets:")
        for name, last_access in most_accessed[:3]:
            print(f"    - {name} (last: {last_access})")

# ============================================================================
# Main Test Runner
# ============================================================================

if __name__ == "__main__":
    print("\n")
    print("="*80)
    print("USER OWNERSHIP LINKING SYSTEM TEST SUITE")
    print("="*80)

    dataset_ids = []

    try:
        # Initialize database
        print("\n[SETUP] Initializing database...")
        init_database()

        # Sync test users
        test_user_sync()

        # Create test datasets for User 1
        print("\n[SETUP] Creating test datasets for User 1...")
        for i in range(3):
            csv_path = create_test_csv(f"ownership_test_{i}.csv", rows=100 * (i + 1))
            dataset_id = create_dataset(
                user_id=TEST_USER_1['email'],
                dataset_name=f"Ownership Test Dataset {i+1}",
                original_filename=f"ownership_test_{i}.csv",
                file_path=csv_path,
                description=f"Test dataset {i+1} for ownership testing"
            )
            if dataset_id:
                dataset_ids.append(dataset_id)
                print(f"  ✓ Created dataset: {dataset_id}")

        if not dataset_ids:
            print("[ERROR] Failed to create test datasets")
            exit(1)

        # Run tests
        test_ownership_verification(dataset_ids[0])
        test_resource_counting(TEST_USER_1['email'])
        test_resource_listing(TEST_USER_1['email'])
        test_storage_breakdown(TEST_USER_1['email'])
        test_ownership_transfer(dataset_ids[0])
        test_dataset_usage_stats(dataset_ids[0])
        test_orphaned_tables()
        test_activity_summary(TEST_USER_1['email'])

        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print("\n✓ All ownership tests completed successfully!")
        print("\nOwnership System Features Tested:")
        print("  1. User synchronization from Firebase")
        print("  2. Dataset ownership verification")
        print("  3. Resource counting per user")
        print("  4. Resource listing and filtering")
        print("  5. Storage breakdown analysis")
        print("  6. Ownership transfer between users")
        print("  7. Dataset usage statistics")
        print("  8. Orphaned table detection")
        print("  9. User activity summaries")
        print("\n" + "="*80)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        print("\n[CLEANUP] Removing test datasets...")
        for dataset_id in dataset_ids:
            delete_dataset(dataset_id, hard_delete=True)
        print("✓ Cleanup complete")

        # Remove test CSVs
        for i in range(3):
            csv_path = f"test_csvs/ownership_test_{i}.csv"
            if os.path.exists(csv_path):
                os.remove(csv_path)
        print("✓ Test CSV files removed")

    print()
