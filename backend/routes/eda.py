"""
Inspection Agent API Routes (formerly EDA Agent)
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Dict, Any, AsyncGenerator
import os
import json
import asyncio
from pathlib import Path

from Auth.Auth_utils import get_current_user
from Agents.inspection_agent import InspectionAnalyzer, InspectionRequest, InspectionReport, InspectionErrorResponse

router = APIRouter(prefix="/agents/eda", tags=["EDA Agent"])

# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/analyze", response_model=InspectionReport)
async def analyze_dataset(
    request: InspectionRequest,
    current_user_email: str = Depends(get_current_user)
):
    """
    Analyze a temporary CSV file for data quality issues using Inspection Agent

    This endpoint is called during Stage 2 of the data cleaning workflow.
    It analyzes the uploaded CSV file and returns a comprehensive report
    of data quality issues, statistics, and recommendations.

    Args:
        request: InspectionRequest with temp_file_path
        current_user_email: Authenticated user email

    Returns:
        InspectionReport with comprehensive analysis
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
        analyzer = InspectionAnalyzer()

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
            detail=f"Inspection service configuration error: {str(e)}"
        )

    except Exception as e:
        # Log error for debugging
        print(f"[ERROR] Inspection analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

@router.post("/analyze-stream")
async def analyze_dataset_stream(
    request: InspectionRequest,
    current_user_email: str = Depends(get_current_user)
):
    """
    Analyze a temporary CSV file with real-time progress streaming via SSE

    This endpoint streams progress updates as the analysis runs, allowing
    the frontend to show detailed progress indicators.

    Args:
        request: InspectionRequest with temp_file_path
        current_user_email: Authenticated user email

    Returns:
        StreamingResponse with Server-Sent Events (SSE)
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Validate temp file path
            temp_file_path = request.temp_file_path

            # Security: Ensure file is in uploads directory
            if not temp_file_path.startswith("./uploads"):
                yield f"event: error\ndata: {json.dumps({'error': 'Invalid file path'})}\n\n"
                return

            # Check if file exists
            if not os.path.exists(temp_file_path):
                yield f"event: error\ndata: {json.dumps({'error': 'Temporary file not found'})}\n\n"
                return

            # Send initial status
            yield f"event: status\ndata: {json.dumps({'stage': 'initializing', 'message': 'Starting analysis...'})}\n\n"
            await asyncio.sleep(0.1)

            # Initialize analyzer with progress callback
            analyzer = InspectionAnalyzer()

            # Track progress
            progress_data = {
                'current_stage': 'loading',
                'total_issues': 0,
                'enriched_issues': 0,
                'current_issue': None
            }

            # Send loading stage
            yield f"event: stage\ndata: {json.dumps({'stage': 'loading', 'message': 'Loading CSV file...'})}\n\n"
            await asyncio.sleep(0.1)

            # Load and analyze (blocking - run in thread pool)
            from concurrent.futures import ThreadPoolExecutor
            import pandas as pd

            # Load CSV
            df = await asyncio.to_thread(pd.read_csv, temp_file_path)
            file_size_bytes = Path(temp_file_path).stat().st_size

            yield f"event: stage\ndata: {json.dumps({'stage': 'summary', 'message': f'Calculating dataset summary ({len(df)} rows, {len(df.columns)} columns)...'})}\n\n"
            await asyncio.sleep(0.1)

            # Calculate summary
            dataset_summary = await asyncio.to_thread(analyzer._calculate_dataset_summary, df, file_size_bytes)

            yield f"event: stage\ndata: {json.dumps({'stage': 'statistics', 'message': 'Calculating column statistics...'})}\n\n"
            await asyncio.sleep(0.1)

            # Calculate column statistics
            column_stats_list = await asyncio.to_thread(analyzer._calculate_column_statistics, df)

            yield f"event: stage\ndata: {json.dumps({'stage': 'detection', 'message': 'Detecting data quality issues...'})}\n\n"
            await asyncio.sleep(0.1)

            # Detect issues
            issues = await asyncio.to_thread(analyzer._detect_issues, df, dataset_summary, column_stats_list)

            progress_data['total_issues'] = len(issues)

            # Enrichment stage with per-issue progress
            if len(issues) > 0:
                yield f"event: stage\ndata: {json.dumps({'stage': 'enrichment', 'message': f'Enriching {len(issues)} issues with AI insights...', 'total': len(issues)})}\n\n"
                await asyncio.sleep(0.1)

                # Enrich issues one by one with progress updates
                enriched_issues = []
                for idx, issue in enumerate(issues):
                    # Send progress for this issue
                    yield f"event: progress\ndata: {json.dumps({'current': idx + 1, 'total': len(issues), 'issue_title': issue.title})}\n\n"
                    await asyncio.sleep(0.05)

                    try:
                        # Get column details
                        column_details = {}
                        for col_name in issue.affected_columns:
                            col_stat = next((c for c in column_stats_list if c.column_name == col_name), None)
                            if col_stat:
                                column_details[col_name] = {
                                    'data_type': col_stat.data_type,
                                    'null_percentage': col_stat.null_percentage,
                                    'unique_count': col_stat.unique_count
                                }

                        # Get sample values
                        sample_values = None
                        if issue.affected_columns and len(issue.affected_columns) > 0:
                            col_name = issue.affected_columns[0]
                            if col_name in df.columns:
                                sample_values = df[col_name].dropna().head(3).tolist()

                        # Generate visualization impact (blocking)
                        visualization_impact = await asyncio.to_thread(
                            analyzer.openai_client.generate_visualization_impact,
                            issue_title=issue.title,
                            issue_type=issue.type,
                            issue_description=issue.description,
                            affected_columns=issue.affected_columns,
                            column_details=column_details,
                            sample_values=sample_values
                        )

                        issue.visualization_impact = visualization_impact
                        enriched_issues.append(issue)

                        # Send completion for this issue
                        yield f"event: issue_complete\ndata: {json.dumps({'current': idx + 1, 'total': len(issues), 'issue_title': issue.title})}\n\n"
                        await asyncio.sleep(0.05)

                    except Exception as e:
                        print(f"[ERROR] Failed to enrich issue: {issue.title} - {str(e)}")
                        enriched_issues.append(issue)

                issues = enriched_issues

            # Generate summary
            yield f"event: stage\ndata: {json.dumps({'stage': 'summary', 'message': 'Generating final summary...'})}\n\n"
            await asyncio.sleep(0.1)

            gpt_summary, visualization_concerns = await asyncio.to_thread(
                analyzer._generate_summary,
                dataset_summary,
                issues
            )

            # Count issues by severity
            critical_count = sum(1 for issue in issues if issue.severity == "critical")
            warning_count = sum(1 for issue in issues if issue.severity == "warning")
            info_count = sum(1 for issue in issues if issue.severity == "info")

            # Build final report
            from Agents.inspection_agent.models import InspectionReport
            report = InspectionReport(
                success=True,
                dataset_summary=dataset_summary,
                column_statistics=column_stats_list,
                issues=issues,
                critical_issues_count=critical_count,
                warning_issues_count=warning_count,
                info_issues_count=info_count,
                gpt_summary=gpt_summary,
                visualization_concerns=visualization_concerns,
                analysis_duration_seconds=0.0
            )

            # Send complete event with full report
            yield f"event: complete\ndata: {json.dumps(report.dict())}\n\n"

        except Exception as e:
            print(f"[ERROR] Streaming analysis failed: {str(e)}")
            import traceback
            traceback.print_exc()

            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering in nginx
        }
    )

@router.get("/health")
async def health_check():
    """
    Health check endpoint for Inspection Agent service
    Verifies OpenAI API key is configured
    """
    import os

    api_key_configured = bool(os.getenv("OPENAI_API_KEY"))

    return {
        "service": "Inspection Agent",
        "status": "healthy" if api_key_configured else "degraded",
        "openai_configured": api_key_configured,
        "message": "Ready for analysis" if api_key_configured else "OpenAI API key not configured"
    }
