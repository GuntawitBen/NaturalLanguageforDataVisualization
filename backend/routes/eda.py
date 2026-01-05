"""
EDA Agent API Routes
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import os
from pathlib import Path

from Auth.Auth_utils import get_current_user
from Agents.eda_agent import EDAAnalyzer, EDARequest, EDAReport, EDAErrorResponse

router = APIRouter(prefix="/agents/eda", tags=["EDA Agent"])

# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/analyze", response_model=EDAReport)
async def analyze_dataset(
    request: EDARequest,
    current_user_email: str = Depends(get_current_user)
):
    """
    Analyze a temporary CSV file for data quality issues

    This endpoint is called during Stage 2 of the data cleaning workflow.
    It analyzes the uploaded CSV file and returns a comprehensive report
    of data quality issues, statistics, and recommendations.

    Args:
        request: EDARequest with temp_file_path
        current_user_email: Authenticated user email

    Returns:
        EDAReport with comprehensive analysis
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

        # Initialize analyzer
        analyzer = EDAAnalyzer()

        # Perform analysis
        report = analyzer.analyze_csv(
            file_path=temp_file_path,
            include_sample_rows=request.include_sample_rows,
            max_sample_rows=request.max_sample_rows
        )

        return report

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except ValueError as e:
        # OpenAI API key not configured
        raise HTTPException(
            status_code=500,
            detail=f"EDA service configuration error: {str(e)}"
        )

    except Exception as e:
        # Log error for debugging
        print(f"[ERROR] EDA analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """
    Health check endpoint for EDA service
    Verifies OpenAI API key is configured
    """
    import os

    api_key_configured = bool(os.getenv("OPENAI_API_KEY"))

    return {
        "service": "EDA Agent",
        "status": "healthy" if api_key_configured else "degraded",
        "openai_configured": api_key_configured,
        "message": "Ready for analysis" if api_key_configured else "OpenAI API key not configured"
    }
