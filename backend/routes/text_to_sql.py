"""
Text-to-SQL Agent API Routes
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from Auth.Auth_utils import get_current_user
from Agents.text_to_sql_agent import (
    text_to_sql_agent,
    StartSessionRequest,
    StartSessionResponse,
    ChatRequest,
    ChatResponse,
    SessionState,
)
from database.db_utils import (
    get_user_conversations,
    get_conversation,
    get_conversation_messages,
    delete_conversation,
    touch_conversation
)

router = APIRouter(prefix="/agents/text-to-sql", tags=["Text-to-SQL Agent"])


# ============================================================================
# Response Models for History
# ============================================================================

class HistoryItem(BaseModel):
    """A conversation in the history list"""
    session_id: str
    dataset_id: Optional[str]
    dataset_name: Optional[str]
    title: Optional[str]
    first_question: Optional[str]
    message_count: int
    created_at: str
    updated_at: str


class HistoryListResponse(BaseModel):
    """Response for history list"""
    conversations: List[HistoryItem]


class HistoryDetailResponse(BaseModel):
    """Response for single conversation history"""
    session_id: str
    dataset_id: Optional[str]
    dataset_name: Optional[str]
    title: Optional[str]
    messages: List[dict]
    created_at: str


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
            dataset_id=request.dataset_id,
            user_id=current_user_email
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


# ============================================================================
# History Endpoints
# ============================================================================

@router.get("/history", response_model=HistoryListResponse)
async def get_history(
    dataset_id: Optional[str] = None,
    current_user_email: str = Depends(get_current_user)
):
    """
    Get list of past text-to-SQL sessions for the current user.

    Args:
        dataset_id: Optional dataset ID to filter conversations by

    Returns:
        List of past conversations with metadata
    """
    try:
        conversations = get_user_conversations(current_user_email, limit=50, dataset_id=dataset_id)

        history_items = []
        for conv in conversations:
            history_items.append(HistoryItem(
                session_id=conv['conversation_id'],
                dataset_id=conv.get('dataset_id'),
                dataset_name=conv.get('dataset_name'),
                title=conv.get('title'),
                first_question=conv.get('first_question'),
                message_count=conv.get('message_count', 0),
                created_at=str(conv.get('created_at', '')),
                updated_at=str(conv.get('updated_at', ''))
            ))

        return HistoryListResponse(conversations=history_items)

    except Exception as e:
        print(f"[ERROR] Failed to get history: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to get history: {str(e)}"
        )


@router.get("/history/{session_id}", response_model=HistoryDetailResponse)
async def get_history_detail(
    session_id: str,
    current_user_email: str = Depends(get_current_user)
):
    """
    Get full conversation history for a specific session.

    Args:
        session_id: Session/conversation identifier

    Returns:
        Full conversation with all messages
    """
    try:
        # Get conversation
        conversation = get_conversation(session_id)
        if not conversation:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

        # Verify user owns this conversation
        if conversation.get('user_id') != current_user_email:
            raise HTTPException(status_code=403, detail="Access denied")

        # Get messages
        messages = get_conversation_messages(session_id)

        # Format messages for response
        formatted_messages = []
        for msg in messages:
            query_result = msg.get('query_result')

            formatted_messages.append({
                "role": msg['role'],
                "content": msg['content'],
                "sql_query": msg.get('query_sql'),
                "query_result": query_result,
                "created_at": str(msg.get('created_at', ''))
            })

        return HistoryDetailResponse(
            session_id=session_id,
            dataset_id=conversation.get('dataset_id'),
            dataset_name=conversation.get('dataset_name'),
            title=conversation.get('title'),
            messages=formatted_messages,
            created_at=str(conversation.get('created_at', ''))
        )

    except HTTPException:
        raise

    except Exception as e:
        print(f"[ERROR] Failed to get history detail: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to get history detail: {str(e)}"
        )


@router.post("/history/{session_id}/resume", response_model=StartSessionResponse)
async def resume_session(
    session_id: str,
    current_user_email: str = Depends(get_current_user)
):
    """
    Resume a historical session, restoring it to active memory.

    Args:
        session_id: Session/conversation identifier

    Returns:
        StartSessionResponse with session info
    """
    try:
        # Verify user owns this conversation
        conversation = get_conversation(session_id)
        if not conversation:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

        if conversation.get('user_id') != current_user_email:
            raise HTTPException(status_code=403, detail="Access denied")

        # Update the timestamp to keep most recent at top
        touch_conversation(session_id)

        response = text_to_sql_agent.resume_session(
            session_id=session_id,
            user_id=current_user_email
        )
        return response

    except HTTPException:
        raise

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        print(f"[ERROR] Failed to resume session: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to resume session: {str(e)}"
        )


@router.delete("/history/{session_id}")
async def delete_history_session(
    session_id: str,
    current_user_email: str = Depends(get_current_user)
):
    """
    Delete a conversation from history.

    Args:
        session_id: Session/conversation identifier

    Returns:
        Success status
    """
    try:
        # Verify user owns this conversation
        conversation = get_conversation(session_id)
        if not conversation:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

        if conversation.get('user_id') != current_user_email:
            raise HTTPException(status_code=403, detail="Access denied")

        # Delete the conversation (hard delete to remove from history)
        deleted = delete_conversation(session_id, hard_delete=True)

        if deleted:
            return {
                "status": "success",
                "message": f"Session {session_id} deleted successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete session"
            )

    except HTTPException:
        raise

    except Exception as e:
        print(f"[ERROR] Failed to delete session: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete session: {str(e)}"
        )
