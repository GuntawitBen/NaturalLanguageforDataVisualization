"""
OpenAI API client for SQL generation.
"""

from openai import OpenAI, RateLimitError
import json
import time
import re
import os
from typing import Optional, List

from .models import SchemaContext, Message, GPTSQLResponse
from .prompts import build_system_prompt, build_user_prompt
from .config import OPENAI_CONFIG, RATE_LIMIT_CONFIG


class TextToSQLOpenAIClient:
    """Client for OpenAI API interactions for text-to-SQL generation"""

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

        # Default to base delay
        return RATE_LIMIT_CONFIG["base_delay"]

    def _call_with_retry(self, func, *args, **kwargs):
        """
        Call OpenAI API with retry logic

        Args:
            func: Function to call
            *args, **kwargs: Arguments to pass to func

        Returns:
            API response

        Raises:
            Exception: If all retries fail
        """
        max_retries = RATE_LIMIT_CONFIG["max_retries"]
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
                backoff = min(
                    retry_after,
                    RATE_LIMIT_CONFIG["base_delay"] * (RATE_LIMIT_CONFIG["exponential_base"] ** attempt)
                )
                backoff = min(backoff, RATE_LIMIT_CONFIG["max_delay"])

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

    def _parse_gpt_response(self, content: str) -> GPTSQLResponse:
        """
        Parse GPT response into structured format

        Args:
            content: Raw response content from GPT

        Returns:
            GPTSQLResponse object
        """
        try:
            # Try to parse as JSON
            # Handle potential markdown code blocks
            content = content.strip()
            if content.startswith("```"):
                # Remove markdown code blocks
                content = re.sub(r'^```(?:json)?\s*', '', content)
                content = re.sub(r'\s*```$', '', content)

            data = json.loads(content)

            return GPTSQLResponse(
                sql=data.get("sql"),
                explanation=data.get("explanation"),
                clarification_needed=data.get("clarification_needed"),
                error=data.get("error"),
                recommendations=data.get("recommendations")
            )

        except json.JSONDecodeError as e:
            print(f"[WARNING] Failed to parse GPT response as JSON: {e}")
            print(f"[DEBUG] Raw content: {content[:500]}")

            # Try to extract SQL if present in non-JSON format
            sql_match = re.search(r'SELECT\s+.+?(?:;|$)', content, re.IGNORECASE | re.DOTALL)
            if sql_match:
                return GPTSQLResponse(
                    sql=sql_match.group(0).rstrip(';') + '',
                    explanation="Extracted from non-JSON response"
                )

            return GPTSQLResponse(
                error=f"Failed to parse response: {str(e)}"
            )

    def generate_sql(
        self,
        question: str,
        schema: SchemaContext,
        messages: List[Message] = None
    ) -> GPTSQLResponse:
        """
        Generate SQL query from natural language question

        Args:
            question: Natural language question
            schema: Database schema context
            messages: Conversation history (optional)

        Returns:
            GPTSQLResponse with SQL or clarification request
        """
        try:
            # Build prompts
            system_prompt = build_system_prompt(schema)
            user_prompt = build_user_prompt(question, messages)

            # Call OpenAI API with retry
            response = self._call_with_retry(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=OPENAI_CONFIG["temperature"],
                max_tokens=OPENAI_CONFIG["max_tokens"],
                timeout=OPENAI_CONFIG["timeout"]
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
            return self._parse_gpt_response(content)

        except Exception as e:
            print(f"[ERROR] Failed to generate SQL: {type(e).__name__}: {str(e)}")
            return GPTSQLResponse(
                error=f"Failed to generate SQL: {str(e)}"
            )

    def fix_sql_error(
        self,
        original_sql: str,
        error_message: str,
        schema: SchemaContext
    ) -> GPTSQLResponse:
        """
        Attempt to fix a SQL error by asking GPT

        Args:
            original_sql: The SQL that failed
            error_message: The error message from DuckDB
            schema: Database schema context

        Returns:
            GPTSQLResponse with fixed SQL or error
        """
        try:
            system_prompt = build_system_prompt(schema)

            user_prompt = f"""The following SQL query produced an error:

SQL: {original_sql}

Error: {error_message}

Please fix the SQL query to resolve this error. Respond with JSON format:
{{"sql": "fixed query", "explanation": "what was fixed"}}"""

            response = self._call_with_retry(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=OPENAI_CONFIG["temperature"],
                max_tokens=OPENAI_CONFIG["max_tokens"],
                timeout=OPENAI_CONFIG["timeout"]
            )

            content = response.choices[0].message.content
            return self._parse_gpt_response(content)

        except Exception as e:
            print(f"[ERROR] Failed to fix SQL: {type(e).__name__}: {str(e)}")
            return GPTSQLResponse(
                error=f"Failed to fix SQL: {str(e)}"
            )
