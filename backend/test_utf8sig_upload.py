"""
Test complete UTF-8-SIG CSV upload flow
Simulates uploading a CSV file with UTF-8-SIG encoding
"""
import os
import tempfile
from utils.csv_validator import validate_csv_file
from database import get_db_connection, create_dataset, get_dataset, delete_dataset

def create_utf8_sig_csv() -> str:
    """Create a test CSV file with UTF-8-SIG encoding (with BOM)"""
    # Create a CSV with some special characters to ensure encoding works
    csv_content = """product_name,price,category,description
"Café Latte",4.50,Beverages,"Espresso with steamed milk"
"Crème Brûlée",6.99,Desserts,"Classic French dessert"
"Naïve Wine",15.00,Beverages,"Young fruity wine"
"Jalapeño Burger",8.50,Food,"Spicy burger with jalapeños"
"Piña Colada",7.00,Beverages,"Tropical cocktail"
"""

    temp_file = os.path.join(tempfile.gettempdir(), 'test_utf8sig_upload.csv')

    # Write with UTF-8-SIG encoding (includes BOM)
    with open(temp_file, 'w', encoding='utf-8-sig') as f:
        f.write(csv_content)

    return temp_file

def test_utf8_sig_upload():
    """Test the complete upload flow with UTF-8-SIG encoding"""
    print("="*80)
    print("UTF-8-SIG CSV UPLOAD TEST")
    print("="*80)

    test_file = None
    dataset_id = None

    try:
        # Step 1: Create test file
        print("\n1. Creating UTF-8-SIG CSV file...")
        test_file = create_utf8_sig_csv()
        file_size = os.path.getsize(test_file)
        print(f"   Created: {test_file} ({file_size} bytes)")

        # Verify BOM is present
        with open(test_file, 'rb') as f:
            first_bytes = f.read(3)
            has_bom = first_bytes == b'\xef\xbb\xbf'
            print(f"   BOM present: {has_bom}")
            if not has_bom:
                raise Exception("BOM not present in file!")

        # Step 2: Validate CSV
        print("\n2. Validating CSV file...")
        validation_result = validate_csv_file(test_file)

        if not validation_result['valid']:
            print("   [FAILED] Validation failed!")
            for error in validation_result['errors']:
                print(f"   Error: {error}")
            return False

        print(f"   [PASSED] Validation successful")
        print(f"   Detected encoding: {validation_result['metadata']['encoding']}")
        print(f"   Rows: {validation_result['metadata']['row_count']}")
        print(f"   Columns: {validation_result['metadata']['column_count']}")
        print(f"   Headers: {', '.join(validation_result['metadata']['sanitized_headers'])}")

        # Step 3: Import to DuckDB
        print("\n3. Importing to DuckDB...")
        dataset_id = create_dataset(
            user_id="test@example.com",
            dataset_name="UTF-8-SIG Test Dataset",
            original_filename="test_utf8sig.csv",
            file_path=test_file,
            description="Test dataset with UTF-8-SIG encoding"
        )

        if not dataset_id:
            print("   [FAILED] Dataset creation failed!")
            return False

        print(f"   [PASSED] Dataset created: {dataset_id}")

        # Step 4: Verify data
        print("\n4. Verifying data in database...")
        dataset = get_dataset(dataset_id)

        if not dataset:
            print("   [FAILED] Could not retrieve dataset!")
            return False

        print(f"   Dataset name: {dataset['dataset_name']}")
        print(f"   Table name: {dataset['table_name']}")
        print(f"   Rows: {dataset['row_count']}")
        print(f"   Columns: {dataset['column_count']}")

        # Step 5: Query the data to verify special characters
        print("\n5. Querying data to verify special characters...")
        conn = get_db_connection()
        table_name = dataset['table_name']

        # Query all data
        result = conn.execute(f"SELECT * FROM {table_name}").fetchall()
        columns = [desc[0] for desc in conn.description]

        print(f"   Retrieved {len(result)} rows")
        print(f"   Sample data:")
        for i, row in enumerate(result[:3], 1):
            row_dict = dict(zip(columns, row))
            print(f"   Row {i}: {row_dict['product_name']} - ${row_dict['price']}")

        # Verify special characters are preserved
        all_products = [dict(zip(columns, row))['product_name'] for row in result]
        expected_products = ["Café Latte", "Crème Brûlée", "Naïve Wine", "Jalapeño Burger", "Piña Colada"]

        for expected in expected_products:
            if expected in all_products:
                print(f"   [PASSED] '{expected}' correctly preserved")
            else:
                print(f"   [FAILED] '{expected}' not found or corrupted")
                return False

        print("\n" + "="*80)
        print("TEST RESULT: [PASSED]")
        print("UTF-8-SIG encoding is fully supported!")
        print("="*80)
        return True

    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        print("\n6. Cleaning up...")
        if dataset_id:
            delete_dataset(dataset_id, hard_delete=True)
            print(f"   Deleted dataset: {dataset_id}")

        if test_file and os.path.exists(test_file):
            os.remove(test_file)
            print(f"   Deleted test file: {test_file}")

if __name__ == "__main__":
    success = test_utf8_sig_upload()
    exit(0 if success else 1)
