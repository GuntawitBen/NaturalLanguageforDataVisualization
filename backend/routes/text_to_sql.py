"""
Text-to-SQL Agent API Routes
"""

from fastapi import APIRouter, HTTPException, Depends

from Auth.Auth_utils import get_current_user
from Agents.text_to_sql_agent import (
    text_to_sql_agent,
    StartSessionRequest,
    StartSessionResponse,
    ChatRequest,
    ChatResponse,
    SessionState,
)

router = APIRouter(prefix="/agents/text-to-sql", tags=["Text-to-SQL Agent"])


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/start-session", response_model=StartSessionResponse)
async def start_session(
    request: StartSessionRequest,
    current_user_email: str = Depends(get_current_user)
):
    """
    Start a new text-to-SQL chat session.

    This endpoint:
    1. Validates the dataset exists
    2. Builds schema context from the dataset
    3. Creates a new session with conversation history
    4. Returns sample questions based on the schema

    Args:
        request: StartSessionRequest with dataset_id
        current_user_email: Authenticated user email

    Returns:
        StartSessionResponse with session_id, schema, and sample_questions
    """
    try:
        response = text_to_sql_agent.start_session(
            dataset_id=request.dataset_id
        )
        return response

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        print(f"[ERROR] Failed to start text-to-SQL session: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to start session: {str(e)}"
        )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user_email: str = Depends(get_current_user)
):
    """
    Send a chat message to generate SQL and get results.

    This endpoint:
    1. Generates SQL from the natural language question
    2. Executes the SQL on the dataset
    3. Returns the SQL query and results
    4. Handles errors with automatic retry (1 attempt)

    Args:
        request: ChatRequest with session_id and message
        current_user_email: Authenticated user email

    Returns:
        ChatResponse with status, message, sql_query, results, etc.
    """
    try:
        response = text_to_sql_agent.chat(
            session_id=request.session_id,
            message=request.message
        )
        return response

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        print(f"[ERROR] Failed to process chat message: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=SessionState)
async def get_session(
    session_id: str,
    current_user_email: str = Depends(get_current_user)
):
    """
    Get the current state of a text-to-SQL session.

    Args:
        session_id: Session ID
        current_user_email: Authenticated user email

    Returns:
        SessionState with schema, messages, and timestamps
    """
    try:
        session_state = text_to_sql_agent.get_session_state(session_id)
        return session_state

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        print(f"[ERROR] Failed to get session state: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session state: {str(e)}"
        )


@router.delete("/session/{session_id}")
async def end_session(
    session_id: str,
    current_user_email: str = Depends(get_current_user)
):
    """
    End a text-to-SQL session.

    Args:
        session_id: Session ID
        current_user_email: Authenticated user email

    Returns:
        Success status
    """
    try:
        deleted = text_to_sql_agent.end_session(session_id)

        if deleted:
            return {
                "status": "success",
                "message": f"Session {session_id} ended successfully"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}"
            )

    except HTTPException:
        raise

    except Exception as e:
        print(f"[ERROR] Failed to end session: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to end session: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for text-to-SQL agent.

    Returns:
        Status message with active session count
    """
    from Agents.text_to_sql_agent.state_manager import session_manager

    return {
        "status": "healthy",
        "service": "text_to_sql_agent",
        "version": "1.0.0",
        "active_sessions": session_manager.get_active_session_count()
    }
