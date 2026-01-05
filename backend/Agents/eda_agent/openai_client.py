"""
OpenAI API client for EDA analysis
"""
from openai import OpenAI
import json
from typing import Dict, List, Any, Optional
from .config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    OPENAI_MAX_TOKENS
)
from .prompts import build_system_prompt, build_user_prompt, build_fallback_summary

class OpenAIClient:
    """Client for OpenAI API interactions"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI client

        Args:
            api_key: OpenAI API key (defaults to config)
        """
        self.api_key = api_key or OPENAI_API_KEY

        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")

        self.client = OpenAI(api_key=self.api_key)

    def analyze_dataset(
        self,
        dataset_summary: Dict[str, Any],
        column_statistics: List[Dict[str, Any]],
        sample_rows: List[Dict[str, Any]],
        detected_issues_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send dataset information to GPT-4 for analysis

        Returns:
            Dictionary with 'summary', 'visualization_concerns', and 'additional_issues'
        """
        try:
            # Build prompts
            system_prompt = build_system_prompt()
            user_prompt = build_user_prompt(
                dataset_summary,
                column_statistics,
                sample_rows,
                detected_issues_summary
            )

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=OPENAI_TEMPERATURE,
                max_tokens=OPENAI_MAX_TOKENS,
                response_format={"type": "json_object"}  # Ensure JSON response
            )

            # Extract and parse response
            content = response.choices[0].message.content
            parsed_response = json.loads(content)

            # Validate response structure
            if not all(key in parsed_response for key in ['summary', 'visualization_concerns']):
                raise ValueError("GPT-4 response missing required fields")

            return {
                "success": True,
                "summary": parsed_response['summary'],
                "visualization_concerns": parsed_response.get('visualization_concerns', []),
                "additional_issues": parsed_response.get('additional_issues', []),
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }

        except Exception as e:
            error_message = str(e)
            error_type = type(e).__name__

            # Determine specific error type
            if "rate" in error_message.lower() or "429" in error_message:
                error_type = "rate_limit"
                error_message = "OpenAI API rate limit exceeded. Please try again later."
            elif "auth" in error_message.lower() or "401" in error_message:
                error_type = "authentication"
                error_message = "OpenAI API authentication failed. Check your API key."
            elif "api" in error_type.lower():
                error_type = "api_error"
            elif isinstance(e, json.JSONDecodeError):
                error_type = "parse_error"
                error_message = "Failed to parse GPT-4 response as JSON"

            return {
                "success": False,
                "error": error_message,
                "error_type": error_type,
                "fallback_summary": build_fallback_summary(len(detected_issues_summary))
            }
