"""
OpenAI API client for generating cleaning option recommendations.
"""

from openai import OpenAI, RateLimitError
import json
import time
import re
import os
from typing import List, Optional, Tuple

from .models import Problem, CleaningOption, DatasetStats
from .prompts import generate_recommendation_prompt
from .config import OPENAI_CONFIG, RECOMMENDATION_CONFIG


class CleaningOpenAIClient:
    """Client for OpenAI API interactions for cleaning agent"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI client

        Args:
            api_key: OpenAI API key (defaults to environment variable)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")

        self.client = OpenAI(api_key=self.api_key)
        self.model = OPENAI_CONFIG["model"]

    def _parse_retry_after(self, error_message: str) -> float:
        """
        Parse retry_after time from rate limit error message

        Args:
            error_message: Error message from OpenAI

        Returns:
            Retry after time in seconds (default 20s)
        """
        # Try to parse "Please try again in Xs" or "Please try again in Xm"
        match = re.search(r'try again in (\d+)s', error_message)
        if match:
            return float(match.group(1))

        match = re.search(r'try again in (\d+)m', error_message)
        if match:
            return float(match.group(1)) * 60

        # Default to 20 seconds
        return 20.0

    def _call_with_retry(self, func, *args, max_retries: int = 2, **kwargs):
        """
        Call OpenAI API with retry logic

        Args:
            func: Function to call
            max_retries: Maximum number of retries
            *args, **kwargs: Arguments to pass to func

        Returns:
            API response

        Raises:
            Exception: If all retries fail
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)

            except RateLimitError as e:
                last_error = e
                error_msg = str(e)

                # If this is the last attempt, raise the error
                if attempt >= max_retries:
                    print(f"[WARNING] Rate limit exceeded after {max_retries} retries.")
                    raise

                # Parse retry_after from error message
                retry_after = self._parse_retry_after(error_msg)
                backoff = min(retry_after, 2 ** attempt)

                print(f"[WARNING] Rate limit hit (attempt {attempt + 1}/{max_retries + 1}). "
                      f"Waiting {backoff:.1f}s before retry...")

                time.sleep(backoff)

            except Exception as e:
                last_error = e
                print(f"[ERROR] OpenAI API call failed: {type(e).__name__}: {str(e)}")
                raise

        # Should never reach here, but just in case
        if last_error:
            raise last_error

    def generate_recommendation(
        self,
        problem: Problem,
        options: List[CleaningOption],
        dataset_stats: DatasetStats,
        dataset_name: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate GPT recommendation for which cleaning option is best.

        Args:
            problem: Problem with severity, metadata, affected columns
            options: List of CleaningOption objects (with static pros/cons)
            dataset_stats: Current dataset statistics (row count, column count)
            dataset_name: Name of the dataset for context

        Returns:
            Tuple of (recommended_option_id, reason) or (None, None) on failure

        Behavior:
            - Retries once on failure (max 2 attempts total)
            - Fails silently and returns (None, None) on any error
            - Validates recommended_option_id exists in options list
            - Uses temperature=0.3 for deterministic recommendations
            - max_tokens=150 for short, concise reasons
        """
        try:
            # Build context dictionary
            context = {
                "dataset": {
                    "name": dataset_name,
                    "total_rows": dataset_stats.row_count,
                    "total_columns": dataset_stats.column_count
                },
                "problem": {
                    "type": problem.problem_type.value,
                    "title": problem.title,
                    "description": problem.description,
                    "affected_columns": problem.affected_columns,
                    "metadata": problem.metadata
                },
                "options": [
                    {
                        "option_id": opt.option_id,
                        "option_name": opt.option_name
                    }
                    for opt in options
                ]
            }

            # Generate prompt
            prompt = generate_recommendation_prompt(context)

            # Call OpenAI API with retry
            response = self._call_with_retry(
                self.client.chat.completions.create,
                model=RECOMMENDATION_CONFIG.get("model", self.model),
                messages=[{"role": "user", "content": prompt}],
                temperature=RECOMMENDATION_CONFIG.get("temperature", 0.3),
                max_completion_tokens=RECOMMENDATION_CONFIG.get("max_completion_tokens", 150),
                timeout=RECOMMENDATION_CONFIG.get("timeout", 8)
            )

            # Log token usage
            if response.usage:
                prompt_details = getattr(response.usage, 'prompt_tokens_details', None)
                cached_tokens = getattr(prompt_details, 'cached_tokens', 0) if prompt_details else 0
                print(f"[GPT] Token usage - Input: {response.usage.prompt_tokens}, "
                      f"Output: {response.usage.completion_tokens}, "
                      f"Cached: {cached_tokens}")

            # Parse response
            content = response.choices[0].message.content
            if not content:
                print("[WARNING] GPT returned empty content")
                return None, None

            # Handle potential markdown code blocks
            content = content.strip()
            if content.startswith("```"):
                import re
                content = re.sub(r'^```(?:json)?\s*', '', content)
                content = re.sub(r'\s*```$', '', content)

            data = json.loads(content)

            recommended_id = data.get("recommended_option_id")
            reason = data.get("reason")

            # Validate recommended_id exists in options
            option_ids = [opt.option_id for opt in options]
            if recommended_id not in option_ids:
                print(f"[WARNING] GPT recommended invalid option_id: {recommended_id}")
                print(f"[INFO] Valid option IDs: {option_ids}")
                return None, None

            return recommended_id, reason

        except Exception as e:
            # Fail silently - return None, None
            print(f"[WARNING] Failed to generate GPT recommendation: {type(e).__name__}: {str(e)}")
            return None, None