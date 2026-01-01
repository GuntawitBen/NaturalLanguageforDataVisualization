# CSV Validation Guide

Complete guide for CSV file validation requirements and standards.

---

## Overview

All CSV files uploaded to the platform undergo comprehensive validation to ensure data quality, security, and compatibility with the database system.

---

## Validation Rules

### 📏 File Size Limits

| Rule | Value | Description |
|------|-------|-------------|
| Maximum size | 100 MB | Files larger than 100MB will be rejected |
| Minimum size | 10 bytes | Prevents empty file uploads |

**Error Examples:**
```
❌ File is too large (125.50 MB). Maximum size is 100 MB.
❌ File is too small (5 bytes). Minimum size is 10 bytes.
```

---

### 📊 Row Limits

| Rule | Value | Description |
|------|-------|-------------|
| Maximum rows | 1,000,000 | Maximum number of data rows (excluding header) |
| Minimum rows | 1 | At least one data row required |

**Error Examples:**
```
❌ Too few rows (0). Minimum is 1
❌ Too many rows (1,500,000). Maximum is 1,000,000
```

---

### 📋 Column Limits

| Rule | Value | Description |
|------|-------|-------------|
| Maximum columns | 100 | Maximum number of columns |
| Minimum columns | 1 | At least one column required |
| Max header length | 100 characters | Maximum length for column names |

**Error Examples:**
```
❌ Too many columns (150). Maximum is 100
❌ Column name too long at position 2: 'this_is_a_very_long_column_name_that_exceeds...'
```

---

### 🔤 Header Validation

#### Required Rules:
1. **No empty headers**: All columns must have names
2. **No duplicates**: Column names must be unique
3. **Length limits**: Headers ≤ 100 characters
4. **No SQL keywords** (warning): Headers like SELECT, FROM, WHERE will be sanitized

#### Header Sanitization:
- Special characters → underscores
- Spaces → underscores
- Converted to lowercase
- Leading/trailing underscores removed
- Numbers at start → prefixed with "col_"

**Examples:**

| Original Header | Sanitized Header |
|----------------|------------------|
| User Name | user_name |
| Total $$ | total |
| 2024_Sales | col_2024_sales |
| SELECT | select |
| Email Address! | email_address |

**Error Examples:**
```
❌ Empty column names found at positions: [0, 3]
❌ Duplicate column names found: name, email
⚠️  Column names use SQL reserved keywords: SELECT, FROM. These will be sanitized.
```

---

### 🔡 Character Encoding

| Encoding | Supported |
|----------|-----------|
| UTF-8 | ✅ Yes (Recommended) |
| ASCII | ✅ Yes |
| ISO-8859-1 | ✅ Yes |
| Windows-1252 | ✅ Yes |
| Others | ❌ No |

**Error Example:**
```
❌ Unsupported encoding: GB2312. Allowed: utf-8, ascii, iso-8859-1, windows-1252
```

---

### 📝 CSV Format

#### Supported Delimiters:
- `,` (comma) - **Recommended**
- `;` (semicolon)
- `\t` (tab)
- `|` (pipe)

#### Supported Quote Characters:
- `"` (double quote) - **Recommended**
- `'` (single quote)

**Error Examples:**
```
❌ Unsupported delimiter ':'. Allowed: , ; \t |
❌ CSV parsing error: line 5: expected 4 fields, saw 6
```

---

### ✅ Column Consistency

All rows must have the same number of columns as the header.

**Error Example:**
```
❌ Inconsistent column count. Expected 4 columns, but found:
  - Row 2: 2 columns
  - Row 5: 6 columns
```

---

## Validation Flow

```
1. File Size Check
   ↓
2. Encoding Detection & Validation
   ↓
3. CSV Format Validation
   ↓
4. Header Validation
   ↓
5. Row Count Check
   ↓
6. Column Consistency Check
   ↓
7. ✅ Upload Approved
```

If any step fails, the upload is rejected with a detailed error message.

---

## Get Validation Configuration

You can retrieve the current validation rules via the API:

```bash
curl -X GET "http://localhost:8000/datasets/validation/config"
```

**Response:**
```json
{
  "file_size": {
    "max_mb": 100,
    "min_bytes": 10
  },
  "rows": {
    "max": 1000000,
    "min": 1
  },
  "columns": {
    "max": 100,
    "min": 1,
    "max_header_length": 100
  },
  "encoding": {
    "allowed": ["utf-8", "ascii", "iso-8859-1", "windows-1252"]
  },
  "format": {
    "allowed_delimiters": [",", ";", "\t", "|"],
    "quote_chars": ["\"", "'"]
  },
  "reserved_keywords_count": 36
}
```

---

## Valid CSV Example

```csv
name,age,city,salary,department
John Doe,28,New York,75000,Engineering
Jane Smith,34,San Francisco,95000,Marketing
Bob Johnson,45,Chicago,82000,Sales
Alice Williams,29,Boston,78000,Engineering
Charlie Brown,31,Seattle,88000,Product
```

✅ **Valid because:**
- Proper CSV format with comma delimiter
- UTF-8 encoding
- No duplicate headers
- 5 rows, 5 columns
- All rows have same column count
- File size: 238 bytes (within limits)

---

## Invalid CSV Examples

### ❌ Example 1: Duplicate Headers

```csv
name,age,name,salary
John,28,Manager,75000
Jane,34,Director,95000
```

**Error:**
```
❌ Duplicate column names found: name
```

**Fix:** Rename duplicate column to unique name:
```csv
name,age,title,salary
```

---

### ❌ Example 2: Empty Headers

```csv
name,,city,
John,28,NYC,75000
Jane,34,SF,95000
```

**Error:**
```
❌ Empty column names found at positions: [1, 3]
```

**Fix:** Provide names for all columns:
```csv
name,age,city,salary
```

---

### ❌ Example 3: Inconsistent Columns

```csv
name,age,city
John,28,NYC,75000
Jane,34
Bob,45,Chicago,82000,Engineering
```

**Error:**
```
❌ Inconsistent column count. Expected 3 columns, but found:
  - Row 2: 2 columns
  - Row 3: 5 columns
```

**Fix:** Ensure all rows have same number of columns:
```csv
name,age,city,salary,department
John,28,NYC,75000,Engineering
Jane,34,SF,95000,Marketing
Bob,45,Chicago,82000,Sales
```

---

### ⚠️ Example 4: Reserved Keywords (Warning)

```csv
SELECT,FROM,WHERE,age
value1,value2,value3,28
value4,value5,value6,34
```

**Warning:**
```
⚠️ Column names use SQL reserved keywords: SELECT, FROM, WHERE. These will be sanitized.
```

**What happens:**
- File is accepted
- Headers are sanitized: `select, from, where, age`
- You can still upload, but headers are transformed

**Recommended Fix:** Use descriptive column names:
```csv
action,source,filter,age
```

---

## Frontend Validation

### Before Upload

You can validate files client-side before uploading:

```javascript
function validateFile(file) {
    const errors = [];

    // Check file type
    if (!file.name.endsWith('.csv')) {
        errors.push('File must be a CSV (.csv extension)');
    }

    // Check file size (100 MB limit)
    const maxSize = 100 * 1024 * 1024;
    if (file.size > maxSize) {
        errors.push(`File too large (${(file.size / 1024 / 1024).toFixed(2)} MB). Max: 100 MB`);
    }

    if (file.size < 10) {
        errors.push('File is too small or empty');
    }

    return errors;
}

// Usage
const file = fileInput.files[0];
const errors = validateFile(file);

if (errors.length > 0) {
    alert('Validation errors:\n' + errors.join('\n'));
} else {
    // Proceed with upload
    uploadFile(file);
}
```

---

## Error Handling

### Backend Response on Validation Failure

```json
{
  "detail": "CSV validation failed:\nDuplicate column names found: name, email\nEmpty column names found at positions: [3]"
}
```

### Frontend Error Display

```javascript
async function uploadWithValidation(file) {
    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/datasets/upload', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();

            // Display validation errors
            if (error.detail && error.detail.includes('CSV validation failed')) {
                const errors = error.detail.split('\n').slice(1); // Skip first line
                alert('CSV Validation Errors:\n\n' + errors.join('\n'));
            } else {
                alert('Upload failed: ' + error.detail);
            }

            return null;
        }

        return await response.json();

    } catch (error) {
        console.error('Upload error:', error);
        alert('Upload failed: ' + error.message);
        return null;
    }
}
```

---

## Testing Validation

Test files are available in `backend/test_csvs/`:

| File | Purpose |
|------|---------|
| `valid.csv` | ✅ Valid CSV that passes all checks |
| `duplicate_headers.csv` | ❌ Duplicate column names |
| `reserved_keywords.csv` | ⚠️ SQL keywords (warning) |
| `empty_headers.csv` | ❌ Empty column names |
| `inconsistent_columns.csv` | ❌ Different column counts per row |

---

## Best Practices

### ✅ DO:
- Use UTF-8 encoding
- Use comma (`,`) as delimiter
- Use descriptive column names
- Ensure consistent column counts
- Keep file sizes reasonable (<10 MB recommended)
- Test with small sample first

### ❌ DON'T:
- Use special characters in headers
- Leave columns unnamed
- Mix encodings in same file
- Use SQL reserved words as headers
- Upload files >100 MB
- Have inconsistent row lengths

---

## Customizing Validation

You can customize validation rules by modifying `utils/csv_validator.py`:

```python
class ValidationConfig:
    # Increase max file size to 500 MB
    MAX_FILE_SIZE_MB = 500

    # Allow up to 200 columns
    MAX_COLUMNS = 200

    # Allow up to 5 million rows
    MAX_ROWS = 5_000_000
```

After changes, restart the backend server.

---

## Validation Metadata

After successful validation, you receive metadata:

```json
{
  "file_size_bytes": 238,
  "encoding": "utf-8",
  "delimiter": ",",
  "headers": ["name", "age", "city"],
  "sanitized_headers": ["name", "age", "city"],
  "column_count": 3,
  "row_count": 100
}
```

This information is stored in the dataset metadata and can be retrieved via:
```
GET /datasets/{dataset_id}
```

---

## Summary

CSV validation ensures:
1. ✅ Files are properly formatted
2. ✅ Headers are valid and SQL-safe
3. ✅ Data is consistent across rows
4. ✅ File sizes are manageable
5. ✅ Encoding is compatible
6. ✅ No duplicate or empty column names

All validation happens **before** data is loaded into the database, preventing data quality issues.
