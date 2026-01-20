"""
Interactive Cleaning Agent API Routes
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import os

from Auth.Auth_utils import get_current_user
from Agents.cleaning_agent import (
    cleaning_agent,
    StartSessionRequest,
    StartSessionResponse,
    ApplyOperationRequest,
    UndoLastRequest,
    OperationResult,
    SessionState
)

router = APIRouter(prefix="/agents/cleaning", tags=["Cleaning Agent"])


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/start-session", response_model=StartSessionResponse)
async def start_cleaning_session(
    request: StartSessionRequest,
    current_user_email: str = Depends(get_current_user)
):
    """
    Start a new interactive cleaning session.

    This endpoint:
    1. Loads the CSV file
    2. Detects all data quality problems
    3. Returns the first problem with cleaning options

    Args:
        request: StartSessionRequest with temp_file_path and dataset_name
        current_user_email: Authenticated user email

    Returns:
        StartSessionResponse with session info and first problem
    """
    try:
        # Validate temp file path
        temp_file_path = request.temp_file_path

        # Security: Ensure file is in uploads directory
        if not temp_file_path.startswith("./uploads"):
            raise HTTPException(
                status_code=400,
                detail="Invalid file path. File must be in uploads directory."
            )

        # Check if file exists
        if not os.path.exists(temp_file_path):
            raise HTTPException(
                status_code=404,
                detail="Temporary file not found. Please upload the file again."
            )

        # Start cleaning session
        response = cleaning_agent.start_session(
            temp_file_path=temp_file_path,
            dataset_name=request.dataset_name
        )

        return response

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Log error for debugging
        print(f"[ERROR] Failed to start cleaning session: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to start cleaning session: {str(e)}"
        )


@router.post("/apply-operation", response_model=OperationResult)
async def apply_cleaning_operation(
    request: ApplyOperationRequest,
    current_user_email: str = Depends(get_current_user)
):
    """
    Apply a selected cleaning operation.

    This endpoint:
    1. Saves a backup of the current DataFrame
    2. Applies the selected cleaning operation
    3. Updates the temp file
    4. Returns the next problem (if any)

    Args:
        request: ApplyOperationRequest with session_id and option_id
        current_user_email: Authenticated user email

    Returns:
        OperationResult with stats and next problem
    """
    try:
        # Apply operation
        result = cleaning_agent.apply_operation(
            session_id=request.session_id,
            option_id=request.option_id,
            custom_parameters=request.custom_parameters
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        # Log error for debugging
        print(f"[ERROR] Failed to apply operation: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply operation: {str(e)}"
        )


@router.post("/undo-last", response_model=OperationResult)
async def undo_last_operation(
    request: UndoLastRequest,
    current_user_email: str = Depends(get_current_user)
):
    """
    Undo the last cleaning operation.

    This endpoint:
    1. Restores the DataFrame from the last backup
    2. Updates the temp file
    3. Removes the last operation from history
    4. Returns the current problem

    Args:
        request: UndoLastRequest with session_id
        current_user_email: Authenticated user email

    Returns:
        OperationResult with restored stats
    """
    try:
        result = cleaning_agent.undo_last(session_id=request.session_id)
        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        # Log error for debugging
        print(f"[ERROR] Failed to undo operation: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to undo operation: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=SessionState)
async def get_session_state(
    session_id: str,
    current_user_email: str = Depends(get_current_user)
):
    """
    Get the current state of a cleaning session.

    Args:
        session_id: Session ID
        current_user_email: Authenticated user email

    Returns:
        SessionState with current session info
    """
    try:
        session_state = cleaning_agent.get_session_state(session_id=session_id)
        return session_state

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        # Log error for debugging
        print(f"[ERROR] Failed to get session state: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session state: {str(e)}"
        )


@router.post("/cleanup")
async def cleanup_backups(
    current_user_email: str = Depends(get_current_user)
):
    """
    Manually trigger cleanup of old sessions and orphaned backup files.

    This endpoint:
    1. Removes sessions older than 30 minutes
    2. Removes orphaned backup files older than 24 hours

    Args:
        current_user_email: Authenticated user email

    Returns:
        Cleanup results
    """
    try:
        from Agents.cleaning_agent.state_manager import session_manager

        # Cleanup old sessions
        session_manager.cleanup_old_sessions()

        # Cleanup orphaned backups
        session_manager.cleanup_orphaned_backups(max_age_hours=24)

        return {
            "status": "success",
            "message": "Cleanup completed successfully"
        }

    except Exception as e:
        print(f"[ERROR] Failed to run cleanup: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to run cleanup: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for cleaning agent.

    Returns:
        Status message
    """
    return {
        "status": "healthy",
        "service": "cleaning_agent",
        "version": "1.0.0"
    }
