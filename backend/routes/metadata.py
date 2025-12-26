"""
Metadata API Endpoints
Provides access to dataset metadata and statistics
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from Auth.firebase_auth import get_firebase_user_email
from database import get_dataset
from utils.metadata_extractor import (
    extract_comprehensive_metadata,
    extract_column_statistics,
    get_metadata_history,
    save_metadata_snapshot
)

router = APIRouter(prefix="/metadata", tags=["Metadata"])

# ============================================================================
# Response Models
# ============================================================================

class MetadataResponse(BaseModel):
    dataset_id: str
    dataset_name: str
    table_name: str
    row_count: int
    column_count: int
    columns_info: list
    data_quality: Optional[dict] = None
    column_statistics: Optional[list] = None
    extraction_time: str

class ColumnStatisticsResponse(BaseModel):
    column_name: str
    data_type: str
    distinct_count: int
    null_count: int
    statistics: dict

# ============================================================================
# Endpoints
# ============================================================================

@router.get("/{dataset_id}", response_model=MetadataResponse)
async def get_dataset_metadata(
    dataset_id: str,
    include_stats: bool = Query(False, description="Include detailed column statistics"),
    current_user_email: str = Depends(get_firebase_user_email)
):
    """
    Get comprehensive metadata for a dataset

    - **dataset_id**: Dataset ID
    - **include_stats**: Whether to include detailed column statistics (slower)
    """
    # Verify dataset exists and user has access
    dataset = get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset['user_id'] != current_user_email:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        # Extract metadata
        table_name = dataset['table_name']
        metadata = extract_comprehensive_metadata(table_name, include_stats=include_stats)

        # Add dataset info
        metadata['dataset_id'] = dataset_id
        metadata['dataset_name'] = dataset['dataset_name']

        return MetadataResponse(**metadata)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting metadata: {str(e)}")

@router.get("/{dataset_id}/column/{column_name}", response_model=ColumnStatisticsResponse)
async def get_column_statistics(
    dataset_id: str,
    column_name: str,
    current_user_email: str = Depends(get_firebase_user_email)
):
    """
    Get detailed statistics for a specific column

    - **dataset_id**: Dataset ID
    - **column_name**: Name of the column
    """
    # Verify dataset exists and user has access
    dataset = get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset['user_id'] != current_user_email:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        # Find column info
        columns_info = dataset.get('columns_info', [])
        column_info = next((col for col in columns_info if col['name'] == column_name), None)

        if not column_info:
            raise HTTPException(status_code=404, detail=f"Column '{column_name}' not found")

        # Extract statistics
        table_name = dataset['table_name']
        stats = extract_column_statistics(table_name, column_name, column_info['type'])

        return ColumnStatisticsResponse(
            column_name=stats['column_name'],
            data_type=stats['data_type'],
            distinct_count=stats.get('distinct_count', 0),
            null_count=stats.get('null_count', 0),
            statistics=stats
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting column statistics: {str(e)}")

@router.post("/{dataset_id}/snapshot")
async def create_metadata_snapshot(
    dataset_id: str,
    current_user_email: str = Depends(get_firebase_user_email)
):
    """
    Create a metadata snapshot for historical tracking

    - **dataset_id**: Dataset ID
    """
    # Verify dataset exists and user has access
    dataset = get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset['user_id'] != current_user_email:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        # Extract comprehensive metadata
        table_name = dataset['table_name']
        metadata = extract_comprehensive_metadata(table_name, include_stats=True)

        # Save snapshot
        success = save_metadata_snapshot(dataset_id, metadata)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to save metadata snapshot")

        return {
            "message": "Metadata snapshot created successfully",
            "dataset_id": dataset_id,
            "dataset_name": dataset['dataset_name']
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating snapshot: {str(e)}")

@router.get("/{dataset_id}/history")
async def get_dataset_metadata_history(
    dataset_id: str,
    current_user_email: str = Depends(get_firebase_user_email)
):
    """
    Get metadata history for a dataset

    - **dataset_id**: Dataset ID
    """
    # Verify dataset exists and user has access
    dataset = get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset['user_id'] != current_user_email:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        history = get_metadata_history(dataset_id)

        return {
            "dataset_id": dataset_id,
            "dataset_name": dataset['dataset_name'],
            "snapshot_count": len(history),
            "snapshots": history
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving metadata history: {str(e)}")

@router.get("/{dataset_id}/summary")
async def get_dataset_summary(
    dataset_id: str,
    current_user_email: str = Depends(get_firebase_user_email)
):
    """
    Get a quick summary of dataset metadata (fast, no statistics)

    - **dataset_id**: Dataset ID
    """
    # Verify dataset exists and user has access
    dataset = get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset['user_id'] != current_user_email:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        from utils.metadata_extractor import extract_basic_metadata

        table_name = dataset['table_name']
        basic_metadata = extract_basic_metadata(table_name)

        return {
            "dataset_id": dataset_id,
            "dataset_name": dataset['dataset_name'],
            "original_filename": dataset['original_filename'],
            "upload_date": dataset['upload_date'].isoformat() if dataset['upload_date'] else None,
            "last_accessed": dataset['last_accessed'].isoformat() if dataset['last_accessed'] else None,
            **basic_metadata
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving dataset summary: {str(e)}")
