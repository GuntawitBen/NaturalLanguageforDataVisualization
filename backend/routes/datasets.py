"""
Dataset management API endpoints
Handles CSV upload, dataset queries, and dataset management
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
import os
import tempfile
import shutil
from datetime import datetime

from Auth.firebase_auth import verify_firebase_token, get_firebase_user_email
from Auth.Auth_utils import get_current_user
from database import (
    create_dataset,
    get_dataset,
    get_user_datasets,
    delete_dataset,
    query_dataset,
)
from utils.csv_validator import validate_csv_file as validate_csv_structure, ValidationConfig

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

class QueryRequest(BaseModel):
    sql_query: str

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
            print(f"[WARNING] CSV validation warnings for {file.filename}:")
            for warning in validation_result["warnings"]:
                print(f"  - {warning}")

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
            table_name=dataset['table_name']
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
                table_name=ds['table_name']
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
            return {
                "success": True,
                "message": "Temporary file deleted successfully"
            }
        else:
            return {
                "success": True,
                "message": "File already deleted or does not exist"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting temp file: {str(e)}")

@router.post("/preview-temp")
async def preview_temp_csv(
    temp_file_path: str = Form(...),
    limit: int = Form(100),
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

        df = pd.read_csv(temp_file_path)

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

    try:
        # Create dataset in database
        dataset_id = create_dataset(
            user_id=current_user_email,
            dataset_name=dataset_name,
            original_filename=original_filename,
            file_path=temp_file_path,
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

        # Clean up temp file (data is now in MySQL)
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        return DatasetResponse(
            dataset_id=dataset['dataset_id'],
            dataset_name=dataset['dataset_name'],
            original_filename=dataset['original_filename'],
            row_count=dataset['row_count'],
            column_count=dataset['column_count'],
            columns_info=dataset['columns_info'],
            upload_date=dataset['upload_date'].isoformat() if dataset['upload_date'] else None,
            file_size_bytes=dataset['file_size_bytes'],
            table_name=dataset['table_name']
        )

    except HTTPException:
        raise
    except Exception as e:
        # Clean up file on error
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
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
            table_name=dataset['table_name']
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
    hard_delete: bool = False,
    current_user_email: str = Depends(get_current_user)
):
    """
    Delete a dataset (soft delete by default)

    - **hard_delete**: If true, permanently removes the dataset and data
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
    limit: int = 10,
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
