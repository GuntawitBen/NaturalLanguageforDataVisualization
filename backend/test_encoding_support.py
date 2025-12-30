"""
Test UTF-8-SIG and other encoding support for CSV files
"""
import os
import tempfile
from utils.csv_validator import validate_csv_file, detect_encoding

def create_test_csv_with_encoding(encoding: str, filename: str) -> str:
    """Create a test CSV file with the specified encoding"""
    # Simple test data
    csv_content = "name,age,city\nJohn,30,New York\nJane,25,London\nBob,35,Paris\n"

    # Create temp file with specified encoding
    with open(filename, 'w', encoding=encoding) as f:
        f.write(csv_content)

    return filename

def test_encoding(encoding_name: str, encoding_param: str):
    """Test CSV validation with a specific encoding"""
    print(f"\n{'='*80}")
    print(f"Testing {encoding_name}")
    print('='*80)

    # Create temporary file
    temp_file = os.path.join(tempfile.gettempdir(), f'test_{encoding_name.replace(" ", "_").replace("-", "_")}.csv')

    try:
        # Create test CSV with specified encoding
        create_test_csv_with_encoding(encoding_param, temp_file)

        # Detect encoding
        detected = detect_encoding(temp_file)
        print(f"Detected encoding: {detected}")

        # Validate the CSV
        result = validate_csv_file(temp_file)

        print(f"Validation result: {'[PASSED]' if result['valid'] else '[FAILED]'}")

        if result['errors']:
            print("\nErrors:")
            for error in result['errors']:
                print(f"  - {error}")

        if result['warnings']:
            print("\nWarnings:")
            for warning in result['warnings']:
                print(f"  - {warning}")

        if result['metadata']:
            print("\nMetadata:")
            print(f"  Encoding: {result['metadata'].get('encoding')}")
            print(f"  Rows: {result['metadata'].get('row_count')}")
            print(f"  Columns: {result['metadata'].get('column_count')}")
            print(f"  Headers: {', '.join(result['metadata'].get('sanitized_headers', []))}")

        return result['valid']

    except Exception as e:
        print(f"Error during test: {e}")
        return False

    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.remove(temp_file)

# Run tests
print("\n" + "="*80)
print("CSV ENCODING SUPPORT TESTS")
print("="*80)

test_cases = [
    ("UTF-8", "utf-8"),
    ("UTF-8 with BOM (UTF-8-SIG)", "utf-8-sig"),
    ("UTF-16 LE", "utf-16-le"),
    ("Windows-1252", "windows-1252"),
    ("ISO-8859-1 (Latin-1)", "iso-8859-1"),
]

results = {}
for name, encoding in test_cases:
    results[name] = test_encoding(name, encoding)

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
for name, passed in results.items():
    status = "[PASSED]" if passed else "[FAILED]"
    print(f"{name:40} {status}")

print("\n" + "="*80)
print(f"Total: {len(results)} tests, {sum(results.values())} passed, {len(results) - sum(results.values())} failed")
print("="*80)
