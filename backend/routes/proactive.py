"""
Proactive Agent API Routes

Endpoints for proactive data insights and guided exploration.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from Auth.Auth_utils import get_current_user
from Agents.proactive_agent import (
    proactive_agent,
    ProactiveInsights,
    ExploreRequest,
    ExploreResponse,
    ChooseRequest,
    ChooseResponse,
)

router = APIRouter(prefix="/agents/proactive", tags=["Proactive Agent"])


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/{dataset_id}/insights", response_model=ProactiveInsights)
async def get_insights(
    dataset_id: str,
    current_user_email: str = Depends(get_current_user)
):
    """
    Compute and return insights for a dataset (on-demand).

    This endpoint:
    1. Loads the dataset
    2. Runs statistical signal detection (trends, outliers, dominance, etc.)
    3. Generates natural language observations using GPT
    4. Creates exploration choices for each observation

    Args:
        dataset_id: Dataset identifier
        current_user_email: Authenticated user email

    Returns:
        ProactiveInsights with signals, observations, and choices
    """
    try:
        insights = proactive_agent.get_insights(dataset_id)
        return insights

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        print(f"[ERROR] Failed to compute insights: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute insights: {str(e)}"
        )


@router.post("/{dataset_id}/explore", response_model=ExploreResponse)
async def start_exploration(
    dataset_id: str,
    request: Optional[ExploreRequest] = None,
    current_user_email: str = Depends(get_current_user)
):
    """
    Start an exploration session for a dataset.

    This endpoint:
    1. Computes insights (if not cached)
    2. Creates a new exploration session
    3. Returns the first observation and available choices

    Args:
        dataset_id: Dataset identifier
        request: Optional request with starting observation
        current_user_email: Authenticated user email

    Returns:
        ExploreResponse with session ID and initial state
    """
    try:
        observation_id = request.observation_id if request else None

        response = proactive_agent.start_exploration(
            dataset_id=dataset_id,
            user_id=current_user_email,
            observation_id=observation_id
        )

        return response

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        print(f"[ERROR] Failed to start exploration: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to start exploration: {str(e)}"
        )


@router.post("/session/{session_id}/choose", response_model=ChooseResponse)
async def make_choice(
    session_id: str,
    request: ChooseRequest,
    current_user_email: str = Depends(get_current_user)
):
    """
    Make a choice in an exploration session.

    This endpoint:
    1. Finds the selected choice
    2. Executes the associated SQL query
    3. Generates follow-up observations and choices based on results
    4. Returns results and follow-up options

    Args:
        session_id: Exploration session identifier
        request: ChooseRequest with choice_id
        current_user_email: Authenticated user email

    Returns:
        ChooseResponse with SQL results and follow-up options
    """
    try:
        response = proactive_agent.make_choice(
            session_id=session_id,
            choice_id=request.choice_id
        )

        if not response.success:
            raise HTTPException(status_code=400, detail=response.message)

        return response

    except HTTPException:
        raise

    except Exception as e:
        print(f"[ERROR] Failed to process choice: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to process choice: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=ExploreResponse)
async def get_session_state(
    session_id: str,
    current_user_email: str = Depends(get_current_user)
):
    """
    Get the current state of an exploration session.

    Args:
        session_id: Exploration session identifier
        current_user_email: Authenticated user email

    Returns:
        ExploreResponse with current observation and available choices
    """
    try:
        response = proactive_agent.get_session_state(session_id)

        if not response:
            raise HTTPException(
                status_code=404,
                detail="Session not found or expired"
            )

        return response

    except HTTPException:
        raise

    except Exception as e:
        print(f"[ERROR] Failed to get session state: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session state: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for proactive agent.

    Returns:
        Status message
    """
    return {
        "status": "healthy",
        "service": "proactive_agent",
        "version": "1.0.0"
    }
