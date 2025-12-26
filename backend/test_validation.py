"""
Test CSV validation with different test files
"""
from utils.csv_validator import validate_csv_file
import os

test_files = [
    ("test_csvs/valid.csv", "Valid CSV file"),
    ("test_csvs/duplicate_headers.csv", "Duplicate column names"),
    ("test_csvs/reserved_keywords.csv", "SQL reserved keywords"),
    ("test_csvs/empty_headers.csv", "Empty column names"),
    ("test_csvs/inconsistent_columns.csv", "Inconsistent column count"),
]

print("="*80)
print("CSV VALIDATION TESTS")
print("="*80)

for file_path, description in test_files:
    print(f"\n\nTest: {description}")
    print(f"File: {file_path}")
    print("-"*80)

    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}")
        continue

    result = validate_csv_file(file_path)

    print(f"Valid: {result['valid']}")

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
        for key, value in result['metadata'].items():
            if key == 'sanitized_headers':
                print(f"  {key}: {', '.join(value)}")
            else:
                print(f"  {key}: {value}")

print("\n" + "="*80)
print("TESTS COMPLETE")
print("="*80)
