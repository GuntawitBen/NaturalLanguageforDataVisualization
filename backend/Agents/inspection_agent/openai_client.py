"""
OpenAI API client for summary and visualization impact generation
"""
from openai import OpenAI, RateLimitError
import json
import time
import re
from typing import Dict, List, Any, Optional, Tuple
from .config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_MAX_RETRIES
from .prompts import build_visualization_impact_prompt, build_summary_prompt

class OpenAIClient:
    """Client for OpenAI API interactions"""

    def __init__(self, api_key: Optional[str] = None, max_retries: Optional[int] = None):
        """
        Initialize OpenAI client

        Args:
            api_key: OpenAI API key (defaults to config)
            max_retries: Maximum number of retries for rate limit errors (defaults to config)
        """
        self.api_key = api_key or OPENAI_API_KEY

        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")

        self.client = OpenAI(api_key=self.api_key)
        self.max_retries = max_retries if max_retries is not None else OPENAI_MAX_RETRIES

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

    def _call_with_retry(self, func, *args, max_retries: Optional[int] = None, **kwargs):
        """
        Call OpenAI API with exponential backoff retry logic

        Args:
            func: Function to call (e.g., self.client.chat.completions.create)
            max_retries: Override default max_retries
            *args, **kwargs: Arguments to pass to func

        Returns:
            API response

        Raises:
            RateLimitError: If retries exhausted
        """
        retries = max_retries if max_retries is not None else self.max_retries
        last_error = None

        for attempt in range(retries + 1):
            try:
                return func(*args, **kwargs)

            except RateLimitError as e:
                last_error = e
                error_msg = str(e)

                # If this is the last attempt, raise the error
                if attempt >= retries:
                    print(f"[WARNING] Rate limit exceeded after {retries} retries. Skipping.")
                    raise

                # Parse retry_after from error message
                retry_after = self._parse_retry_after(error_msg)

                # Add exponential backoff (but respect the API's suggested time)
                backoff = min(retry_after, 2 ** attempt)

                print(f"[WARNING] Rate limit hit (attempt {attempt + 1}/{retries + 1}). "
                      f"Waiting {backoff:.1f}s before retry...")

                time.sleep(backoff)

        # Should never reach here, but just in case
        if last_error:
            raise last_error

    def generate_summary(
        self,
        dataset_summary: Dict[str, Any],
        issues: List[Dict[str, Any]]
    ) -> Tuple[str, List[str]]:
        """
        Generate summary and visualization concerns from detected issues

        Returns:
            Tuple of (summary_text, visualization_concerns_list)
        """
        try:
            # Build prompt
            prompt = build_summary_prompt(dataset_summary, issues)

            # Call OpenAI API with retry logic
            response = self._call_with_retry(
                self.client.chat.completions.create,
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Summarize data quality findings. Return JSON with 'summary' (2-3 sentences) and 'visualization_concerns' (list)."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300,
                response_format={"type": "json_object"},
                max_retries=2
            )

            # Parse response
            content = response.choices[0].message.content
            parsed = json.loads(content)

            summary = parsed.get('summary', 'Analysis complete.')
            concerns = parsed.get('visualization_concerns', [])

            print(f"[GPT-4] Generated summary successfully")
            return summary, concerns

        except RateLimitError as e:
            print(f"[WARNING] Rate limit exceeded for summary generation. Using fallback.")
            # Fallback with note about rate limits
            if len(issues) == 0:
                return "Your dataset appears clean with no major quality issues detected.", []
            else:
                critical = sum(1 for i in issues if i.get('severity') == 'critical')
                warning = sum(1 for i in issues if i.get('severity') == 'warning')
                return (
                    f"Analysis complete. Found {len(issues)} issue(s): {critical} critical, {warning} warnings. "
                    f"(Detailed AI summary unavailable due to API rate limits)",
                    []
                )

        except Exception as e:
            print(f"[ERROR] Failed to generate summary: {type(e).__name__}: {str(e)}")
            # Fallback
            if len(issues) == 0:
                return "Your dataset appears clean with no major quality issues detected.", []
            else:
                critical = sum(1 for i in issues if i.get('severity') == 'critical')
                warning = sum(1 for i in issues if i.get('severity') == 'warning')
                return f"Analysis complete. Found {len(issues)} issue(s): {critical} critical, {warning} warnings.", []

    def generate_visualization_impact(
        self,
        issue_title: str,
        issue_type: str,
        issue_description: str,
        affected_columns: List[str],
        column_details: Dict[str, Any],
        sample_values: List[Any] = None
    ) -> str:
        """
        Generate dynamic visualization impact explanation for a specific issue

        Returns:
            String with visualization impact explanation
        """
        try:
            # Build prompt
            prompt = build_visualization_impact_prompt(
                issue_title=issue_title,
                issue_type=issue_type,
                issue_description=issue_description,
                affected_columns=affected_columns,
                column_details=column_details,
                sample_values=sample_values
            )

            # Call OpenAI API with retry logic
            response = self._call_with_retry(
                self.client.chat.completions.create,
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Explain how data issues affect charts/graphs. 3 sentences max. Be specific."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=150,
                max_retries=2  # Lower retries for enrichment to avoid long delays
            )

            # Extract response
            impact_text = response.choices[0].message.content.strip()

            # Log success
            print(f"[GPT-4] Generated impact successfully ({len(impact_text)} chars)")

            return impact_text

        except RateLimitError as e:
            # Rate limit exhausted after retries
            print(f"[WARNING] Rate limit exceeded for issue '{issue_title}'. Using fallback message.")
            return "This data quality issue may affect the accuracy and clarity of your visualizations. (AI analysis unavailable due to rate limits)"

        except Exception as e:
            # Other errors - fallback to generic message
            error_type = type(e).__name__
            error_msg = str(e)
            print(f"[ERROR] Failed to generate visualization impact: {error_type}: {error_msg}")

            return "This data quality issue may affect the accuracy and clarity of your visualizations, potentially leading to misleading or incomplete visual representations of your data."
