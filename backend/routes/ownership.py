"""
User Ownership and Resource Management API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from Auth.firebase_auth import get_firebase_user_email
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

router = APIRouter(prefix="/ownership", tags=["Ownership"])

# ============================================================================
# Response Models
# ============================================================================

class ResourceCountResponse(BaseModel):
    datasets: int
    deleted_datasets: int
    conversations: int
    archived_conversations: int
    visualizations: int
    queries: int
    total_storage_bytes: int

class ActivitySummaryResponse(BaseModel):
    recent_uploads: int
    recent_queries: int
    query_success_rate: float
    recent_conversations: int

class TransferOwnershipRequest(BaseModel):
    to_user_email: str

# ============================================================================
# Endpoints
# ============================================================================

@router.get("/resources/count", response_model=ResourceCountResponse)
async def get_resource_count(
    current_user_email: str = Depends(get_firebase_user_email)
):
    """
    Get count of all resources owned by the current user

    Returns counts for:
    - Active datasets
    - Deleted datasets
    - Active conversations
    - Archived conversations
    - Saved visualizations
    - Query history entries
    - Total storage used (bytes)
    """
    try:
        counts = get_user_resource_count(current_user_email)
        return ResourceCountResponse(**counts)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting resource count: {str(e)}")

@router.get("/activity")
async def get_activity(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user_email: str = Depends(get_firebase_user_email)
):
    """
    Get user activity summary for the last N days

    - **days**: Number of days to analyze (default: 30, max: 365)
    """
    try:
        summary = get_user_activity_summary(current_user_email, days)
        return {
            "user_email": current_user_email,
            "days_analyzed": days,
            **summary
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting activity summary: {str(e)}")

@router.get("/resources")
async def list_resources(
    resource_type: str = Query('all', regex='^(all|datasets|conversations|visualizations|queries)$'),
    current_user_email: str = Depends(get_firebase_user_email)
):
    """
    List all resources owned by the current user

    - **resource_type**: Type of resources to list (all, datasets, conversations, visualizations, queries)
    """
    try:
        resources = list_user_resources(current_user_email, resource_type)
        return {
            "user_email": current_user_email,
            "resource_type": resource_type,
            **resources
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing resources: {str(e)}")

@router.get("/storage/breakdown")
async def get_storage_breakdown(
    current_user_email: str = Depends(get_firebase_user_email)
):
    """
    Get detailed storage usage breakdown by dataset

    Returns list of datasets sorted by size (largest first)
    """
    try:
        breakdown = get_user_storage_breakdown(current_user_email)

        total_storage = sum(d['file_size_bytes'] for d in breakdown)

        return {
            "user_email": current_user_email,
            "total_storage_bytes": total_storage,
            "total_storage_mb": round(total_storage / (1024 * 1024), 2),
            "dataset_count": len(breakdown),
            "datasets": breakdown
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting storage breakdown: {str(e)}")

@router.get("/dataset/{dataset_id}/verify")
async def verify_ownership(
    dataset_id: str,
    current_user_email: str = Depends(get_firebase_user_email)
):
    """
    Verify that the current user owns a specific dataset

    - **dataset_id**: Dataset ID to verify
    """
    is_owner, error = verify_dataset_ownership(dataset_id, current_user_email)

    if not is_owner:
        raise HTTPException(status_code=403, detail=error)

    return {
        "dataset_id": dataset_id,
        "is_owner": True,
        "user_email": current_user_email
    }

@router.get("/dataset/{dataset_id}/usage")
async def get_dataset_usage(
    dataset_id: str,
    current_user_email: str = Depends(get_firebase_user_email)
):
    """
    Get usage statistics for a specific dataset

    Returns:
    - Query count
    - Conversation count
    - Visualization count
    - Last accessed time
    - Top queries
    """
    # Verify ownership
    is_owner, error = verify_dataset_ownership(dataset_id, current_user_email)
    if not is_owner:
        raise HTTPException(status_code=403, detail=error)

    try:
        stats = get_dataset_usage_stats(dataset_id)
        return {
            "dataset_id": dataset_id,
            **stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting dataset usage: {str(e)}")

@router.post("/dataset/{dataset_id}/transfer")
async def transfer_ownership(
    dataset_id: str,
    request: TransferOwnershipRequest,
    current_user_email: str = Depends(get_firebase_user_email)
):
    """
    Transfer dataset ownership to another user

    - **dataset_id**: Dataset to transfer
    - **to_user_email**: Email of the user to transfer ownership to

    Note: This also transfers associated conversations and visualizations
    """
    success, error = transfer_dataset_ownership(
        dataset_id,
        current_user_email,
        request.to_user_email
    )

    if not success:
        raise HTTPException(status_code=400, detail=error)

    return {
        "message": "Ownership transferred successfully",
        "dataset_id": dataset_id,
        "from_user": current_user_email,
        "to_user": request.to_user_email
    }

@router.get("/admin/orphaned-tables")
async def list_orphaned_tables(
    current_user_email: str = Depends(get_firebase_user_email)
):
    """
    List data tables that don't have corresponding metadata entries
    (Admin/debugging endpoint)
    """
    # TODO: Add admin role check
    try:
        orphaned = get_orphaned_tables()
        return {
            "count": len(orphaned),
            "tables": orphaned
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding orphaned tables: {str(e)}")

@router.post("/admin/cleanup-orphaned")
async def cleanup_orphaned(
    current_user_email: str = Depends(get_firebase_user_email)
):
    """
    Remove orphaned data tables
    (Admin/debugging endpoint - use with caution!)
    """
    # TODO: Add admin role check and confirmation
    try:
        cleaned = cleanup_orphaned_tables()
        return {
            "message": f"Cleaned up {cleaned} orphaned tables",
            "tables_removed": cleaned
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up: {str(e)}")
