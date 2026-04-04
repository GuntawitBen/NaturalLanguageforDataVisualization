"""
Dataset management API endpoints
Handles CSV upload, dataset queries, and dataset management
"""
import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
import os
import tempfile
import shutil
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)

from Auth.firebase_auth import verify_firebase_token, get_firebase_user_email
from Auth.Auth_utils import get_current_user
from database import (
    create_dataset,
    get_dataset,
    get_user_datasets,
    delete_dataset,
    query_dataset,
    save_visualization,
    get_dataset_visualizations,
    delete_visualization,
    update_visualization,
    update_dataset_description,
)
from utils.csv_validator import validate_csv_file as validate_csv_structure, ValidationConfig, sanitize_column_name, detect_encoding

router = APIRouter(prefix="/datasets", tags=["Datasets"])

# ============================================================================
# Request/Response Models
# ============================================================================

class DatasetResponse(BaseModel):
    dataset_id: str
    dataset_name: str
    original_filename: str
    row_count: int
    column_count: int
    columns_info: List[dict]
    upload_date: str
    file_size_bytes: int
    table_name: str
    description: Optional[str] = None

class UpdateDescriptionRequest(BaseModel):
    description: str

class QueryRequest(BaseModel):
    sql_query: str

class SaveVisualizationRequest(BaseModel):
    title: str
    chart_type: str
    query_sql: str = ""
    visualization_config: dict
    description: Optional[str] = None

class QueryResponse(BaseModel):
    success: bool
    data: Optional[List] = None
    columns: Optional[List[str]] = None
    row_count: Optional[int] = None
    execution_time_ms: Optional[float] = None
    error: Optional[str] = None

# ============================================================================
# Helper Functions
# ============================================================================

async def scan_csv_for_injection(file_path: str) -> None:
    """
    Scan CSV content for indirect prompt injection.
    Raises HTTPException if suspicious content is found.
    Fails open (logs warning) if the check itself errors.
    """
    try:
        from safety import check_data_content
        df_sample = pd.read_csv(file_path, nrows=50)
        content_to_scan = " ".join(df_sample.columns.tolist())
        for col in df_sample.columns:
            content_to_scan += " " + " ".join(df_sample[col].astype(str).tolist())
        guard_result = await check_data_content(content_to_scan)
        if not guard_result.is_safe:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=400,
                detail=guard_result.message or "Suspicious content detected in your CSV data."
            )
    except HTTPException:
        raise
    except Exception as guard_err:
        logger.warning(f"Data content check failed (proceeding): {guard_err}")


def validate_upload_file(file: UploadFile) -> bool:
    """Validate uploaded file is a CSV"""
    # Check file extension
    if not file.filename.endswith('.csv'):
        return False

    # Check content type
    if file.content_type and 'csv' not in file.content_type.lower():
        # Some browsers don't set content_type correctly, so we're lenient
        pass

    return True

def save_uploaded_file(upload_file: UploadFile) -> str:
    """Save uploaded file to temporary location and return path"""
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = "./uploads"
        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{upload_file.filename}"
        file_path = os.path.join(upload_dir, filename)

        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

        return file_path

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/upload", response_model=DatasetResponse)
async def upload_csv(
    file: UploadFile = File(...),
    dataset_name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    current_user_email: str = Depends(get_current_user)
):
    """
    Upload a CSV file and create a dataset

    - **file**: CSV file to upload
    - **dataset_name**: Optional custom name (defaults to filename)
    - **description**: Optional dataset description
    - **tags**: Optional comma-separated tags
    """
    # Validate file
    if not validate_upload_file(file):
        raise HTTPException(
            status_code=400,
            detail="Invalid file. Please upload a CSV file."
        )

    # Use filename as dataset name if not provided
    if not dataset_name:
        dataset_name = file.filename.replace('.csv', '')

    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(',')] if tags else []

    file_path = None
    try:
        # Save uploaded file
        file_path = save_uploaded_file(file)

        # Validate CSV file structure
        validation_result = validate_csv_structure(file_path)

        if not validation_result["valid"]:
            # Clean up file
            if os.path.exists(file_path):
                os.remove(file_path)

            # Return validation errors
            error_message = "CSV validation failed:\n" + "\n".join(validation_result["errors"])
            raise HTTPException(status_code=400, detail=error_message)

        # Log warnings if any
        if validation_result["warnings"]:
            logger.warning(f"CSV validation warnings for {file.filename}:")
            for warning in validation_result["warnings"]:
                logger.warning(f"  - {warning}")

        # --- Indirect Injection Guard (scan CSV content) ---
        await scan_csv_for_injection(file_path)

        # Create dataset in database
        dataset_id = create_dataset(
            user_id=current_user_email,
            dataset_name=dataset_name,
            original_filename=file.filename,
            file_path=file_path,
            description=description,
            tags=tag_list
        )

        if not dataset_id:
            raise HTTPException(
                status_code=500,
                detail="Failed to create dataset. Please check the CSV file format."
            )

        # Get dataset metadata
        dataset = get_dataset(dataset_id)

        # Clean up uploaded file (data is now in MySQL)
        if os.path.exists(file_path):
            os.remove(file_path)

        return DatasetResponse(
            dataset_id=dataset['dataset_id'],
            dataset_name=dataset['dataset_name'],
            original_filename=dataset['original_filename'],
            row_count=dataset['row_count'],
            column_count=dataset['column_count'],
            columns_info=dataset['columns_info'],
            upload_date=dataset['upload_date'].isoformat() if dataset['upload_date'] else None,
            file_size_bytes=dataset['file_size_bytes'],
            table_name=dataset['table_name'],
            description=dataset.get('description')
        )

    except HTTPException:
        raise
    except Exception as e:
        # Clean up file on error
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[DatasetResponse])
async def list_datasets(
    current_user_email: str = Depends(get_current_user)
):
    """Get all datasets for the current user"""
    try:
        datasets = get_user_datasets(current_user_email)

        return [
            DatasetResponse(
                dataset_id=ds['dataset_id'],
                dataset_name=ds['dataset_name'],
                original_filename=ds['original_filename'],
                row_count=ds['row_count'],
                column_count=ds['column_count'],
                columns_info=ds['columns_info'],
                upload_date=ds['upload_date'].isoformat() if ds['upload_date'] else None,
                file_size_bytes=ds['file_size_bytes'],
                table_name=ds['table_name'],
                description=ds.get('description')
            )
            for ds in datasets
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# NOTE: Specific routes must come BEFORE path parameter routes like /{dataset_id}
# Otherwise FastAPI will match the path parameter first

@router.get("/test-endpoint")
async def test_endpoint():
    """Simple test endpoint"""
    return {"message": "Test endpoint works!"}

@router.post("/test-post")
async def test_post_endpoint():
    """Simple POST test endpoint"""
    return {"message": "POST works!"}

@router.post("/upload-temp")
async def upload_csv_temp(
    file: UploadFile = File(...),
    dataset_name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user_email: str = Depends(get_current_user)
):
    """
    Upload and validate a CSV file temporarily without storing in database.
    Returns file info and temp file ID for later processing.
    """
    # Validate file
    if not validate_upload_file(file):
        raise HTTPException(
            status_code=400,
            detail="Invalid file. Please upload a CSV file."
        )

    # Use filename as dataset name if not provided
    if not dataset_name:
        dataset_name = file.filename.replace('.csv', '')

    file_path = None
    try:
        # Save uploaded file
        file_path = save_uploaded_file(file)

        # Validate CSV file structure
        validation_result = validate_csv_structure(file_path)

        if not validation_result["valid"]:
            # Clean up file
            if os.path.exists(file_path):
                os.remove(file_path)

            # Return validation errors
            error_message = "CSV validation failed:\n" + "\n".join(validation_result["errors"])
            raise HTTPException(status_code=400, detail=error_message)

        # --- Indirect Injection Guard (scan CSV content) ---
        await scan_csv_for_injection(file_path)

        # Get file size
        file_size = os.path.getsize(file_path)

        # Return temp file info without creating dataset
        return {
            "success": True,
            "temp_file_path": file_path,
            "dataset_name": dataset_name,
            "original_filename": file.filename,
            "file_size_bytes": file_size,
            "validation": validation_result,
            "has_header": validation_result["metadata"].get("has_header", True),
            "headers_auto_generated": validation_result["metadata"].get("headers_auto_generated", False),
            "description": description,
            "message": "File uploaded and validated successfully. Complete the cleaning process to finalize."
        }

    except HTTPException:
        raise
    except Exception as e:
        # Clean up file on error
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cleanup-temp")
async def cleanup_temp_file(
    temp_file_path: str = Form(...),
    current_user_email: str = Depends(get_current_user)
):
    """
    Delete a temporary uploaded file.
    Used when user leaves the upload/cleaning page without finalizing.
    """
    try:
        # Verify file exists and is in uploads directory
        if not temp_file_path or not temp_file_path.startswith("./uploads"):
            raise HTTPException(
                status_code=400,
                detail="Invalid file path"
            )

        # Delete file if it exists
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        # Also delete sidecar types file if it exists
        sidecar_path = f"{temp_file_path}.types.json"
        if os.path.exists(sidecar_path):
            os.remove(sidecar_path)

        return {
            "success": True,
            "message": "Temporary file deleted successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting temp file: {str(e)}")

@router.post("/preview-temp")
async def preview_temp_csv(
    temp_file_path: str = Form(...),
    limit: int = Form(1000),  # Increased for virtualization support
    has_header: bool = Form(True),
    current_user_email: str = Depends(get_current_user)
):
    """
    Preview a temporary CSV file (used in cleaning workflow).
    Returns columns, sample data, and metadata without creating a dataset.
    """
    try:
        # Validate path is in uploads directory
        if not temp_file_path or not temp_file_path.startswith("./uploads"):
            raise HTTPException(
                status_code=400,
                detail="Invalid file path"
            )

        # Verify file exists
        if not os.path.exists(temp_file_path):
            raise HTTPException(
                status_code=404,
                detail="Temporary file not found"
            )

        # Read CSV with pandas
        import pandas as pd

        if has_header:
            df = pd.read_csv(temp_file_path)
        else:
            df = pd.read_csv(temp_file_path, header=None)
            df.columns = [f"Column {i+1}" for i in range(len(df.columns))]

        # Get column info with data types
        columns_info = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            null_count = int(df[col].isnull().sum())
            columns_info.append({
                "name": col,
                "type": dtype,
                "null_count": null_count
            })

        # Get preview data (convert to list of lists for JSON serialization)
        preview_df = df.head(limit)
        data_rows = preview_df.values.tolist()

        # Convert NaN and inf values to None for JSON serialization
        import math
        for row in data_rows:
            for i in range(len(row)):
                val = row[i]
                if pd.isna(val):
                    row[i] = None
                elif isinstance(val, float) and (math.isinf(val) or math.isnan(val)):
                    row[i] = None

        return {
            "success": True,
            "columns": df.columns.tolist(),
            "columns_info": columns_info,
            "data": data_rows,
            "row_count": len(df),
            "column_count": len(df.columns),
            "showing_rows": len(data_rows)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error previewing CSV: {str(e)}"
        )

@router.post("/confirm-headers")
async def confirm_headers(
    temp_file_path: str = Form(...),
    headers: str = Form(...),       # JSON array of header names
    has_header: bool = Form(True),
    column_types: Optional[str] = Form(None),  # JSON dict {col_name: dtype}
    current_user_email: str = Depends(get_current_user)
):
    """
    Confirm or update CSV headers before proceeding to cleaning.
    If has_header=False, rewrites the CSV with the provided header row.
    If has_header=True and headers changed, renames columns accordingly.
    """
    import json
    import pandas as pd

    # Validate path is in uploads directory
    if not temp_file_path or not temp_file_path.startswith("./uploads"):
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not os.path.exists(temp_file_path):
        raise HTTPException(status_code=404, detail="Temporary file not found")

    try:
        # Parse headers JSON
        header_list = json.loads(headers)
        if not isinstance(header_list, list) or len(header_list) == 0:
            raise HTTPException(status_code=400, detail="Headers must be a non-empty JSON array")

        # Sanitize each header
        sanitized = [sanitize_column_name(h) for h in header_list]

        # Check for duplicates after sanitization
        if len(set(sanitized)) != len(sanitized):
            duplicates = [h for h in sanitized if sanitized.count(h) > 1]
            raise HTTPException(
                status_code=400,
                detail=f"Duplicate column names after sanitization: {', '.join(set(duplicates))}"
            )

        # Detect encoding to preserve it
        encoding = detect_encoding(temp_file_path)

        if not has_header:
            # No header row — read without header, assign columns, write back with header
            df = pd.read_csv(temp_file_path, header=None, encoding=encoding)
            if len(sanitized) != len(df.columns):
                raise HTTPException(
                    status_code=400,
                    detail=f"Header count ({len(sanitized)}) doesn't match column count ({len(df.columns)})"
                )
            df.columns = sanitized
            df.to_csv(temp_file_path, index=False, encoding='utf-8')
        else:
            # Has header — read CSV, check if headers changed, rename if needed
            df = pd.read_csv(temp_file_path, encoding=encoding)
            original_cols = list(df.columns)
            if len(sanitized) != len(original_cols):
                raise HTTPException(
                    status_code=400,
                    detail=f"Header count ({len(sanitized)}) doesn't match column count ({len(original_cols)})"
                )
            # Only rewrite if headers actually changed
            if sanitized != original_cols:
                df.columns = sanitized
                df.to_csv(temp_file_path, index=False, encoding='utf-8')

        # Save column type overrides as sidecar JSON file
        if column_types:
            try:
                types_dict = json.loads(column_types)
                if isinstance(types_dict, dict) and types_dict:
                    # Re-key using sanitized column names to stay in sync
                    sanitized_types = {}
                    for orig_name, dtype in types_dict.items():
                        sanitized_types[sanitize_column_name(orig_name)] = dtype
                    sidecar_path = f"{temp_file_path}.types.json"
                    with open(sidecar_path, 'w') as f:
                        json.dump(sanitized_types, f)
            except (json.JSONDecodeError, TypeError):
                pass  # Non-critical — ignore malformed column_types

        return {
            "success": True,
            "sanitized_headers": sanitized
        }

    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in headers parameter")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error confirming headers: {str(e)}")


@router.post("/finalize", response_model=DatasetResponse)
async def finalize_dataset(
    temp_file_path: str = Form(...),
    dataset_name: str = Form(...),
    original_filename: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    current_user_email: str = Depends(get_current_user)
):
    """
    Finalize dataset creation after cleaning process is complete.
    Takes the temp file and creates the dataset in the database.
    """
    # Verify temp file exists
    if not os.path.exists(temp_file_path):
        raise HTTPException(
            status_code=404,
            detail="Temporary file not found. Please upload the file again."
        )

    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(',')] if tags else []

    sidecar_path = f"{temp_file_path}.types.json"

    try:
        # --- Indirect Injection Guard (scan CSV content before saving) ---
        await scan_csv_for_injection(temp_file_path)

        # Load column type overrides from sidecar file if present
        import json as _json
        column_types = None
        if os.path.exists(sidecar_path):
            try:
                with open(sidecar_path, 'r') as f:
                    column_types = _json.load(f)
            except Exception:
                column_types = None

        # Create dataset in database
        dataset_id = create_dataset(
            user_id=current_user_email,
            dataset_name=dataset_name,
            original_filename=original_filename,
            file_path=temp_file_path,
            description=description,
            tags=tag_list,
            column_types=column_types
        )

        if not dataset_id:
            raise HTTPException(
                status_code=500,
                detail="Failed to create dataset. Please check the CSV file format."
            )

        # Get dataset metadata
        dataset = get_dataset(dataset_id)

        # Clean up temp file and sidecar (data is now in MySQL)
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(sidecar_path):
            os.remove(sidecar_path)

        return DatasetResponse(
            dataset_id=dataset['dataset_id'],
            dataset_name=dataset['dataset_name'],
            original_filename=dataset['original_filename'],
            row_count=dataset['row_count'],
            column_count=dataset['column_count'],
            columns_info=dataset['columns_info'],
            upload_date=dataset['upload_date'].isoformat() if dataset['upload_date'] else None,
            file_size_bytes=dataset['file_size_bytes'],
            table_name=dataset['table_name'],
            description=dataset.get('description')
        )

    except HTTPException:
        raise
    except Exception as e:
        # Clean up file and sidecar on error
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(sidecar_path):
            os.remove(sidecar_path)
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{dataset_id}/description")
async def update_dataset_description_endpoint(
    dataset_id: str,
    request: UpdateDescriptionRequest,
    current_user_email: str = Depends(get_current_user)
):
    """Update a dataset's description"""
    try:
        dataset = get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        if dataset['user_id'] != current_user_email:
            raise HTTPException(status_code=403, detail="Access denied")

        success = update_dataset_description(dataset_id, request.description)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update description")

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset_info(
    dataset_id: str,
    current_user_email: str = Depends(get_current_user)
):
    """Get information about a specific dataset"""
    try:
        dataset = get_dataset(dataset_id)

        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        # Verify ownership
        if dataset['user_id'] != current_user_email:
            raise HTTPException(status_code=403, detail="Access denied")

        return DatasetResponse(
            dataset_id=dataset['dataset_id'],
            dataset_name=dataset['dataset_name'],
            original_filename=dataset['original_filename'],
            row_count=dataset['row_count'],
            column_count=dataset['column_count'],
            columns_info=dataset['columns_info'],
            upload_date=dataset['upload_date'].isoformat() if dataset['upload_date'] else None,
            file_size_bytes=dataset['file_size_bytes'],
            table_name=dataset['table_name'],
            description=dataset.get('description')
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{dataset_id}/query", response_model=QueryResponse)
async def query_dataset_endpoint(
    dataset_id: str,
    request: QueryRequest,
    current_user_email: str = Depends(get_current_user)
):
    """
    Execute a SQL query on a dataset

    The query should use {{table}} as a placeholder for the table name
    Example: SELECT * FROM {{table}} LIMIT 10
    """
    try:
        # Verify dataset exists and user has access
        dataset = get_dataset(dataset_id)

        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        if dataset['user_id'] != current_user_email:
            raise HTTPException(status_code=403, detail="Access denied")

        # Execute query
        result = query_dataset(dataset_id, request.sql_query)

        return QueryResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{dataset_id}")
async def delete_dataset_endpoint(
    dataset_id: str,
    hard_delete: bool = True,
    current_user_email: str = Depends(get_current_user)
):
    """
    Delete a dataset (hard delete by default)

    - **hard_delete**: If false, only marks as deleted without removing data
    """
    try:
        # Verify dataset exists and user has access
        dataset = get_dataset(dataset_id)

        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        if dataset['user_id'] != current_user_email:
            raise HTTPException(status_code=403, detail="Access denied")

        # Delete dataset
        success = delete_dataset(dataset_id, hard_delete=hard_delete)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete dataset")

        return {
            "message": "Dataset deleted successfully",
            "dataset_id": dataset_id,
            "hard_delete": hard_delete
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{dataset_id}/preview")
async def preview_dataset(
    dataset_id: str,
    limit: int = 1000,  # Increased for virtualization support
    current_user_email: str = Depends(get_current_user)
):
    """Get a preview of the dataset (first N rows)"""
    try:
        # Verify dataset exists and user has access
        dataset = get_dataset(dataset_id)

        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        if dataset['user_id'] != current_user_email:
            raise HTTPException(status_code=403, detail="Access denied")

        # Query first N rows
        result = query_dataset(dataset_id, f"SELECT * FROM {{{{table}}}} LIMIT {limit}")

        if result['success']:
            return {
                "dataset_id": dataset_id,
                "dataset_name": dataset['dataset_name'],
                "columns": result['columns'],
                "data": result['data'],
                "total_rows": dataset['row_count'],
                "showing_rows": result['row_count']
            }
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Query failed'))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{dataset_id}/stats")
async def get_dataset_stats(
    dataset_id: str,
    current_user_email: str = Depends(get_current_user)
):
    """Get statistical information about the dataset"""
    try:
        # Verify dataset exists and user has access
        dataset = get_dataset(dataset_id)

        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        if dataset['user_id'] != current_user_email:
            raise HTTPException(status_code=403, detail="Access denied")

        return {
            "dataset_id": dataset_id,
            "dataset_name": dataset['dataset_name'],
            "row_count": dataset['row_count'],
            "column_count": dataset['column_count'],
            "columns": dataset['columns_info'],
            "file_size_bytes": dataset['file_size_bytes'],
            "upload_date": dataset['upload_date'].isoformat() if dataset['upload_date'] else None,
            "last_accessed": dataset['last_accessed'].isoformat() if dataset['last_accessed'] else None
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/validation/config")
async def get_validation_config():
    """Get CSV validation configuration"""
    config = ValidationConfig()
    return {
        "file_size": {
            "max_mb": config.MAX_FILE_SIZE_MB,
            "min_bytes": config.MIN_FILE_SIZE_BYTES
        },
        "rows": {
            "max": config.MAX_ROWS,
            "min": config.MIN_ROWS
        },
        "columns": {
            "max": config.MAX_COLUMNS,
            "min": config.MIN_COLUMNS,
            "max_header_length": config.MAX_HEADER_LENGTH
        },
        "encoding": {
            "allowed": config.ALLOWED_ENCODINGS
        },
        "format": {
            "allowed_delimiters": config.ALLOWED_DELIMITERS,
            "quote_chars": config.QUOTE_CHARS
        },
        "reserved_keywords_count": len(config.RESERVED_KEYWORDS)
    }

# ============================================================================
# Dashboard / Saved Visualizations Endpoints
# ============================================================================

@router.get("/{dataset_id}/dashboard")
async def get_dataset_dashboard(
    dataset_id: str,
    current_user_email: str = Depends(get_current_user)
):
    """Get all pinned visualizations (dashboard) for a dataset"""
    try:
        # Verify dataset exists and user has access
        dataset = get_dataset(dataset_id)

        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        if dataset['user_id'] != current_user_email:
            raise HTTPException(status_code=403, detail="Access denied")

        # Get visualizations for this dataset
        visualizations = get_dataset_visualizations(dataset_id, current_user_email)

        return {
            "dataset_id": dataset_id,
            "visualizations": visualizations
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{dataset_id}/dashboard")
async def add_to_dashboard(
    dataset_id: str,
    request: SaveVisualizationRequest,
    current_user_email: str = Depends(get_current_user)
):
    """Add a visualization to the dataset's dashboard"""
    try:
        # Verify dataset exists and user has access
        dataset = get_dataset(dataset_id)

        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        if dataset['user_id'] != current_user_email:
            raise HTTPException(status_code=403, detail="Access denied")

        # Save the visualization
        viz_id = save_visualization(
            user_id=current_user_email,
            dataset_id=dataset_id,
            title=request.title,
            query_sql=request.query_sql,
            chart_type=request.chart_type,
            visualization_config=request.visualization_config,
            description=request.description
        )

        if not viz_id:
            raise HTTPException(status_code=500, detail="Failed to save visualization")

        return {
            "success": True,
            "visualization_id": viz_id,
            "message": "Visualization added to dashboard"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{dataset_id}/dashboard/{visualization_id}")
async def remove_from_dashboard(
    dataset_id: str,
    visualization_id: str,
    current_user_email: str = Depends(get_current_user)
):
    """Remove a visualization from the dataset's dashboard"""
    try:
        # Verify dataset exists and user has access
        dataset = get_dataset(dataset_id)

        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        if dataset['user_id'] != current_user_email:
            raise HTTPException(status_code=403, detail="Access denied")

        # Delete the visualization
        success = delete_visualization(visualization_id, current_user_email)

        if not success:
            raise HTTPException(status_code=404, detail="Visualization not found")

        return {
            "success": True,
            "message": "Visualization removed from dashboard"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{dataset_id}/dashboard/{visualization_id}")
async def update_dashboard_visualization(
    dataset_id: str,
    visualization_id: str,
    request: SaveVisualizationRequest,
    current_user_email: str = Depends(get_current_user)
):
    """Update a visualization on the dashboard"""
    try:
        # Verify dataset exists and user has access
        dataset = get_dataset(dataset_id)

        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        if dataset['user_id'] != current_user_email:
            raise HTTPException(status_code=403, detail="Access denied")

        # Update the visualization
        success = update_visualization(
            visualization_id=visualization_id,
            user_id=current_user_email,
            visualization_config=request.visualization_config
        )

        if not success:
            raise HTTPException(status_code=404, detail="Visualization not found")

        return {
            "success": True,
            "message": "Visualization updated"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
