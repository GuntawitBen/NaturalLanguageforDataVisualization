"""
CSV File Validation Module
Validates CSV files for format, size, headers, and content
"""
import csv
import os
import re
from typing import Dict, List, Optional, Tuple
from io import StringIO
import chardet

# ============================================================================
# VALIDATION CONFIGURATION
# ============================================================================

class ValidationConfig:
    """Configuration for CSV validation rules"""

    # File size limits
    MAX_FILE_SIZE_MB = 100  # Maximum file size in MB
    MIN_FILE_SIZE_BYTES = 10  # Minimum file size (prevent empty files)

    # Row limits
    MAX_ROWS = 1_000_000  # Maximum number of rows
    MIN_ROWS = 1  # Minimum number of rows (excluding header)

    # Column limits
    MAX_COLUMNS = 100  # Maximum number of columns
    MIN_COLUMNS = 1  # Minimum number of columns

    # Header validation
    MAX_HEADER_LENGTH = 100  # Maximum length for column names
    RESERVED_KEYWORDS = [  # SQL reserved keywords to avoid
        'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE',
        'DROP', 'CREATE', 'ALTER', 'TABLE', 'INDEX', 'VIEW',
        'ORDER', 'GROUP', 'BY', 'HAVING', 'LIMIT', 'OFFSET',
        'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER', 'ON', 'AS',
        'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'LIKE', 'BETWEEN'
    ]

    # Character encoding
    ALLOWED_ENCODINGS = ['utf-8', 'ascii', 'iso-8859-1', 'windows-1252']

    # CSV format
    ALLOWED_DELIMITERS = [',', ';', '\t', '|']
    QUOTE_CHARS = ['"', "'"]


# ============================================================================
# VALIDATION ERRORS
# ============================================================================

class CSVValidationError(Exception):
    """Base exception for CSV validation errors"""
    pass


class FileSizeError(CSVValidationError):
    """File size validation error"""
    pass


class FileFormatError(CSVValidationError):
    """File format validation error"""
    pass


class HeaderValidationError(CSVValidationError):
    """Header validation error"""
    pass


class ContentValidationError(CSVValidationError):
    """Content validation error"""
    pass


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_file_size(file_path: str, config: ValidationConfig = None) -> Tuple[bool, Optional[str]]:
    """
    Validate file size

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    config = config or ValidationConfig()

    file_size = os.path.getsize(file_path)
    max_size_bytes = config.MAX_FILE_SIZE_MB * 1024 * 1024

    if file_size < config.MIN_FILE_SIZE_BYTES:
        return False, f"File is too small ({file_size} bytes). Minimum size is {config.MIN_FILE_SIZE_BYTES} bytes."

    if file_size > max_size_bytes:
        size_mb = file_size / (1024 * 1024)
        return False, f"File is too large ({size_mb:.2f} MB). Maximum size is {config.MAX_FILE_SIZE_MB} MB."

    return True, None


def detect_encoding(file_path: str) -> str:
    """
    Detect file encoding

    Returns:
        str: Detected encoding
    """
    with open(file_path, 'rb') as f:
        raw_data = f.read(10000)  # Read first 10KB
        result = chardet.detect(raw_data)
        return result['encoding']


def validate_encoding(file_path: str, config: ValidationConfig = None) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate file encoding

    Returns:
        Tuple[bool, Optional[str], Optional[str]]: (is_valid, error_message, detected_encoding)
    """
    config = config or ValidationConfig()

    try:
        detected_encoding = detect_encoding(file_path)

        if detected_encoding.lower() not in [enc.lower() for enc in config.ALLOWED_ENCODINGS]:
            return False, f"Unsupported encoding: {detected_encoding}. Allowed: {', '.join(config.ALLOWED_ENCODINGS)}", detected_encoding

        return True, None, detected_encoding

    except Exception as e:
        return False, f"Could not detect encoding: {str(e)}", None


def detect_csv_dialect(file_path: str, encoding: str = 'utf-8') -> csv.Dialect:
    """
    Detect CSV dialect (delimiter, quote char, etc.)

    Returns:
        csv.Dialect: Detected dialect
    """
    with open(file_path, 'r', encoding=encoding, errors='replace') as f:
        sample = f.read(8192)  # Read first 8KB
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample)
        return dialect


def validate_csv_format(file_path: str, encoding: str = 'utf-8', config: ValidationConfig = None) -> Tuple[bool, Optional[str], Optional[csv.Dialect]]:
    """
    Validate CSV format

    Returns:
        Tuple[bool, Optional[str], Optional[csv.Dialect]]: (is_valid, error_message, dialect)
    """
    config = config or ValidationConfig()

    try:
        # Detect dialect
        dialect = detect_csv_dialect(file_path, encoding)

        # Validate delimiter
        if dialect.delimiter not in config.ALLOWED_DELIMITERS:
            return False, f"Unsupported delimiter '{dialect.delimiter}'. Allowed: {', '.join(config.ALLOWED_DELIMITERS)}", None

        # Try to parse the file
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            reader = csv.reader(f, dialect=dialect)
            try:
                # Read first few rows to validate format
                for i, row in enumerate(reader):
                    if i >= 10:  # Check first 10 rows
                        break
            except csv.Error as e:
                return False, f"CSV parsing error: {str(e)}", None

        return True, None, dialect

    except Exception as e:
        return False, f"Invalid CSV format: {str(e)}", None


def sanitize_column_name(name: str) -> str:
    """
    Sanitize column name to be SQL-safe

    - Remove special characters
    - Replace spaces with underscores
    - Convert to lowercase
    - Remove leading/trailing underscores
    """
    # Convert to string and strip whitespace
    name = str(name).strip()

    # Replace spaces and special characters with underscores
    name = re.sub(r'[^\w\s]', '_', name)
    name = re.sub(r'\s+', '_', name)

    # Convert to lowercase
    name = name.lower()

    # Remove leading/trailing underscores
    name = name.strip('_')

    # If name starts with a number, prefix with 'col_'
    if name and name[0].isdigit():
        name = f"col_{name}"

    # If name is empty or only underscores, generate a generic name
    if not name or name == '_' * len(name):
        name = "column"

    return name


def validate_headers(file_path: str, encoding: str = 'utf-8', dialect: csv.Dialect = None, config: ValidationConfig = None) -> Tuple[bool, Optional[str], Optional[List[str]]]:
    """
    Validate CSV headers

    Returns:
        Tuple[bool, Optional[str], Optional[List[str]]]: (is_valid, error_message, headers)
    """
    config = config or ValidationConfig()

    try:
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            if dialect:
                reader = csv.reader(f, dialect=dialect)
            else:
                reader = csv.reader(f)

            headers = next(reader)

        # Check if headers exist
        if not headers:
            return False, "CSV file has no headers", None

        # Remove whitespace from headers
        headers = [h.strip() for h in headers]

        # Check number of columns
        if len(headers) < config.MIN_COLUMNS:
            return False, f"Too few columns ({len(headers)}). Minimum is {config.MIN_COLUMNS}", None

        if len(headers) > config.MAX_COLUMNS:
            return False, f"Too many columns ({len(headers)}). Maximum is {config.MAX_COLUMNS}", None

        # Check for empty headers
        if any(not h for h in headers):
            empty_indices = [i for i, h in enumerate(headers) if not h]
            return False, f"Empty column names found at positions: {empty_indices}", None

        # Check header length
        long_headers = [(i, h) for i, h in enumerate(headers) if len(h) > config.MAX_HEADER_LENGTH]
        if long_headers:
            return False, f"Column name too long at position {long_headers[0][0]}: '{long_headers[0][1][:50]}...'", None

        # Check for duplicate headers
        duplicates = [h for h in headers if headers.count(h) > 1]
        if duplicates:
            unique_duplicates = list(set(duplicates))
            return False, f"Duplicate column names found: {', '.join(unique_duplicates)}", None

        # Check for SQL reserved keywords
        reserved_found = [h for h in headers if h.upper() in config.RESERVED_KEYWORDS]
        if reserved_found:
            return False, f"Column names use SQL reserved keywords: {', '.join(reserved_found)}. These will be sanitized.", None

        # Sanitize headers
        sanitized_headers = [sanitize_column_name(h) for h in headers]

        # Check for duplicates after sanitization
        duplicates_after = [h for h in sanitized_headers if sanitized_headers.count(h) > 1]
        if duplicates_after:
            unique_dups = list(set(duplicates_after))
            return False, f"Duplicate column names after sanitization: {', '.join(unique_dups)}", None

        return True, None, sanitized_headers

    except Exception as e:
        return False, f"Error validating headers: {str(e)}", None


def validate_row_count(file_path: str, encoding: str = 'utf-8', dialect: csv.Dialect = None, config: ValidationConfig = None) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Validate row count

    Returns:
        Tuple[bool, Optional[str], Optional[int]]: (is_valid, error_message, row_count)
    """
    config = config or ValidationConfig()

    try:
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            if dialect:
                reader = csv.reader(f, dialect=dialect)
            else:
                reader = csv.reader(f)

            # Skip header
            next(reader)

            # Count rows
            row_count = sum(1 for row in reader)

        if row_count < config.MIN_ROWS:
            return False, f"Too few rows ({row_count}). Minimum is {config.MIN_ROWS}", None

        if row_count > config.MAX_ROWS:
            return False, f"Too many rows ({row_count}). Maximum is {config.MAX_ROWS:,}", None

        return True, None, row_count

    except Exception as e:
        return False, f"Error counting rows: {str(e)}", None


def validate_column_consistency(file_path: str, encoding: str = 'utf-8', dialect: csv.Dialect = None, expected_columns: int = None) -> Tuple[bool, Optional[str]]:
    """
    Validate that all rows have the same number of columns

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    try:
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            if dialect:
                reader = csv.reader(f, dialect=dialect)
            else:
                reader = csv.reader(f)

            # Get header column count
            headers = next(reader)
            expected_cols = expected_columns or len(headers)

            # Check each row
            inconsistent_rows = []
            for i, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                if len(row) != expected_cols:
                    inconsistent_rows.append((i, len(row)))
                    if len(inconsistent_rows) >= 5:  # Stop after finding 5 errors
                        break

            if inconsistent_rows:
                error_msg = f"Inconsistent column count. Expected {expected_cols} columns, but found:\n"
                for row_num, col_count in inconsistent_rows:
                    error_msg += f"  - Row {row_num}: {col_count} columns\n"
                return False, error_msg

        return True, None

    except Exception as e:
        return False, f"Error validating column consistency: {str(e)}"


# ============================================================================
# MAIN VALIDATION FUNCTION
# ============================================================================

def validate_csv_file(file_path: str, config: ValidationConfig = None) -> Dict:
    """
    Comprehensive CSV validation

    Returns:
        Dict with validation results:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str],
            "metadata": {
                "file_size_bytes": int,
                "encoding": str,
                "row_count": int,
                "column_count": int,
                "headers": List[str],
                "sanitized_headers": List[str],
                "delimiter": str
            }
        }
    """
    config = config or ValidationConfig()
    errors = []
    warnings = []
    metadata = {}

    try:
        # 1. Validate file size
        valid, error = validate_file_size(file_path, config)
        if not valid:
            errors.append(error)
            return {"valid": False, "errors": errors, "warnings": warnings, "metadata": metadata}

        metadata["file_size_bytes"] = os.path.getsize(file_path)

        # 2. Validate encoding
        valid, error, encoding = validate_encoding(file_path, config)
        if not valid:
            errors.append(error)
            return {"valid": False, "errors": errors, "warnings": warnings, "metadata": metadata}

        metadata["encoding"] = encoding

        # 3. Validate CSV format
        valid, error, dialect = validate_csv_format(file_path, encoding, config)
        if not valid:
            errors.append(error)
            return {"valid": False, "errors": errors, "warnings": warnings, "metadata": metadata}

        metadata["delimiter"] = dialect.delimiter

        # 4. Validate headers
        valid, error, sanitized_headers = validate_headers(file_path, encoding, dialect, config)
        if not valid:
            # Check if it's a reserved keyword warning
            if "reserved keywords" in error.lower():
                warnings.append(error)
                # Extract headers manually for sanitization
                with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                    reader = csv.reader(f, dialect=dialect)
                    original_headers = next(reader)
                    sanitized_headers = [sanitize_column_name(h.strip()) for h in original_headers]
            else:
                errors.append(error)
                return {"valid": False, "errors": errors, "warnings": warnings, "metadata": metadata}

        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            reader = csv.reader(f, dialect=dialect)
            original_headers = next(reader)

        metadata["headers"] = [h.strip() for h in original_headers]
        metadata["sanitized_headers"] = sanitized_headers
        metadata["column_count"] = len(sanitized_headers)

        # 5. Validate row count
        valid, error, row_count = validate_row_count(file_path, encoding, dialect, config)
        if not valid:
            errors.append(error)
            return {"valid": False, "errors": errors, "warnings": warnings, "metadata": metadata}

        metadata["row_count"] = row_count

        # 6. Validate column consistency
        valid, error = validate_column_consistency(file_path, encoding, dialect, len(sanitized_headers))
        if not valid:
            errors.append(error)
            return {"valid": False, "errors": errors, "warnings": warnings, "metadata": metadata}

        # All validations passed
        return {
            "valid": True,
            "errors": [],
            "warnings": warnings,
            "metadata": metadata
        }

    except Exception as e:
        errors.append(f"Unexpected validation error: {str(e)}")
        return {"valid": False, "errors": errors, "warnings": warnings, "metadata": metadata}
