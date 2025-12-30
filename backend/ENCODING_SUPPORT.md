# CSV File Encoding Support

## Overview
The CSV upload system now supports multiple character encodings to ensure compatibility with files created by various applications worldwide.

## Supported Encodings

### UTF Encodings
- **UTF-8** - Standard Unicode encoding (most common)
- **UTF-8-SIG** - UTF-8 with BOM (Byte Order Mark)
  - Common in files exported from Excel on Windows
  - Automatically detected via BOM marker
- **UTF-16**, **UTF-16-LE**, **UTF-16-BE** - Unicode with 16-bit encoding
- **UTF-32**, **UTF-32-LE**, **UTF-32-BE** - Unicode with 32-bit encoding

### Legacy Encodings
- **ASCII** - Basic 7-bit encoding
- **ISO-8859-1 (Latin-1)** - Western European characters
- **ISO-8859-15 (Latin-9)** - Western European with Euro symbol
- **Windows-1252 (CP1252)** - Windows Western European encoding

## BOM (Byte Order Mark) Detection

The system automatically detects BOM markers at the beginning of files:

| BOM Bytes | Detected Encoding |
|-----------|-------------------|
| `EF BB BF` | UTF-8-SIG |
| `FF FE 00 00` | UTF-32-LE |
| `00 00 FE FF` | UTF-32-BE |
| `FF FE` | UTF-16-LE |
| `FE FF` | UTF-16-BE |

## How It Works

1. **BOM Detection**: First checks for byte order marks at file start
2. **Charset Detection**: Uses `chardet` library for automatic encoding detection
3. **Encoding Normalization**: Normalizes encoding names (e.g., `utf16le` → `utf-16-le`)
4. **Validation**: Ensures detected encoding is in the allowed list
5. **Safe Reading**: Opens files with `errors='replace'` to handle any edge cases

## Testing

Run the encoding support tests:

```bash
# Test various encodings including UTF-8-SIG
python test_encoding_support.py

# Test complete upload flow with UTF-8-SIG
python test_utf8sig_upload.py
```

## Example: UTF-8-SIG File

When you upload a CSV file with UTF-8-SIG encoding (e.g., exported from Excel):

```csv
product_name,price,category
Café Latte,4.50,Beverages
Crème Brûlée,6.99,Desserts
Jalapeño Burger,8.50,Food
```

The system will:
1. Detect the BOM: `EF BB BF` → `utf-8-sig`
2. Validate the encoding is supported ✓
3. Correctly parse the file with special characters preserved
4. Import into DuckDB with all data intact

## Configuration

Encoding settings are defined in `utils/csv_validator.py`:

```python
class ValidationConfig:
    ALLOWED_ENCODINGS = [
        'utf-8', 'utf-8-sig',
        'utf-16', 'utf-16-le', 'utf-16-be',
        'utf-32', 'utf-32-le', 'utf-32-be',
        'ascii',
        'iso-8859-1', 'latin-1',
        'windows-1252', 'cp1252',
        'iso-8859-15', 'latin-9',
    ]
```

## Common Use Cases

### Excel Exports (Windows)
- **Encoding**: UTF-8-SIG
- **Why**: Excel adds BOM to UTF-8 files
- **Status**: ✓ Fully supported

### Excel Exports (Mac)
- **Encoding**: UTF-8 or Windows-1252
- **Status**: ✓ Fully supported

### Google Sheets Exports
- **Encoding**: UTF-8 (no BOM)
- **Status**: ✓ Fully supported

### Legacy Systems
- **Encoding**: ISO-8859-1, Windows-1252
- **Status**: ✓ Fully supported

## Error Handling

If an unsupported encoding is detected, the system returns a clear error message:

```
Unsupported encoding: gb2312.
Allowed: utf-8, utf-8-sig, utf-16, ...
```

Users can then:
1. Re-export the file with a supported encoding
2. Convert the file using a text editor
3. Request support for additional encodings if needed

## Future Enhancements

Potential additions:
- **GB2312, GBK** - Chinese character sets
- **Shift-JIS** - Japanese character set
- **EUC-KR** - Korean character set
- **Custom encoding detection thresholds**

---

**Last Updated**: December 31, 2025
**Tested With**: chardet 5.0.0+, DuckDB 1.4.0+
