"""
OpenAI API client for SQL generation.
"""

from openai import OpenAI, RateLimitError
import json
import time
import re
import os
from typing import Optional, List, Dict, Any

from .models import SchemaContext, Message, GPTSQLResponse
from .prompts import build_system_prompt, build_user_prompt, FOLLOW_UP_SUGGESTIONS_PROMPT
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
                error_type=data.get("error_type"),
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
                max_completion_tokens=OPENAI_CONFIG["max_completion_tokens"],
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

    def generate_proactive_intro(self, schema: SchemaContext) -> tuple[str, list[str]]:
        """
        Generate a conversational introduction with recommendations for a dataset.

        Args:
            schema: Database schema context

        Returns:
            Tuple of (intro_message, list of recommendations)
        """
        try:
            from .prompts import build_system_prompt

            system_prompt = build_system_prompt(schema)

            user_prompt = """Analyze this dataset schema and provide a brief, direct introduction for a user who just opened this dataset.

Write a concise message that:
1. Starts with "I've analyzed your data" or similar phrasing (NOT "Welcome" or "fascinating dataset")
2. Briefly states what the data contains (1-2 sentences max)
3. Lists 3-4 specific questions they could explore (based on actual column names)

Keep it professional and to the point - like a data analyst giving a quick briefing. Avoid flowery language, excessive enthusiasm, or words like "fascinating", "exciting", "wonderful".

Return JSON:
{
    "intro_message": "Your direct, analytical message here...",
    "recommendations": ["Question 1?", "Question 2?", "Question 3?"]
}

The recommendations array should contain the exact questions mentioned in your intro_message, so they can be displayed as clickable buttons."""

            response = self._call_with_retry(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,  # Slightly higher for more natural language
                max_completion_tokens=500,
                timeout=OPENAI_CONFIG["timeout"]
            )

            # Log token usage
            if response.usage:
                prompt_details = getattr(response.usage, 'prompt_tokens_details', None)
                cached_tokens = getattr(prompt_details, 'cached_tokens', 0) if prompt_details else 0
                print(f"[GPT] Proactive intro token usage - Input: {response.usage.prompt_tokens}, "
                      f"Output: {response.usage.completion_tokens}, "
                      f"Cached: {cached_tokens}")

            # Parse response
            content = response.choices[0].message.content
            parsed = self._parse_gpt_response(content)

            # intro_message maps to explanation field in GPTSQLResponse
            intro = parsed.explanation or ""
            recommendations = parsed.recommendations or []

            # If parsing didn't capture intro_message, try direct JSON parsing
            if not intro:
                import json
                content_clean = content.strip()
                if content_clean.startswith("```"):
                    content_clean = re.sub(r'^```(?:json)?\s*', '', content_clean)
                    content_clean = re.sub(r'\s*```$', '', content_clean)
                try:
                    data = json.loads(content_clean)
                    intro = data.get("intro_message", "")
                    recommendations = data.get("recommendations", recommendations)
                except json.JSONDecodeError:
                    pass

            return intro, recommendations

        except Exception as e:
            print(f"[ERROR] Failed to generate proactive intro: {type(e).__name__}: {str(e)}")
            return "", []

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
                max_completion_tokens=OPENAI_CONFIG["max_completion_tokens"],
                timeout=OPENAI_CONFIG["timeout"]
            )

            content = response.choices[0].message.content
            return self._parse_gpt_response(content)

        except Exception as e:
            print(f"[ERROR] Failed to fix SQL: {type(e).__name__}: {str(e)}")
            return GPTSQLResponse(
                error=f"Failed to fix SQL: {str(e)}"
            )

    def generate_follow_up_suggestions(
        self,
        original_question: str,
        sql_query: str,
        result_columns: List[str],
        sample_results: List[Dict[str, Any]],
        row_count: int,
        schema: SchemaContext
    ) -> Dict[str, Any]:
        """
        Generate proactive follow-up suggestions based on query results.

        Args:
            original_question: The user's original question
            sql_query: The SQL query that was executed
            result_columns: Columns returned in the result
            sample_results: Sample data from the results (first few rows)
            row_count: Total number of rows returned
            schema: Database schema context

        Returns:
            Dict with 'intro_message' and 'suggestions' list
        """
        try:
            # Find unexplored columns (columns in schema but not in result)
            unexplored = [c.name for c in schema.columns if c.name not in result_columns]

            # Limit sample results for prompt (first 5 rows)
            sample_for_prompt = sample_results[:5] if sample_results else []

            # Build the prompt
            prompt = FOLLOW_UP_SUGGESTIONS_PROMPT.format(
                original_question=original_question,
                sql_query=sql_query,
                result_columns=", ".join(result_columns) if result_columns else "None",
                sample_results=json.dumps(sample_for_prompt, default=str),
                row_count=row_count,
                unexplored_columns=", ".join(unexplored) if unexplored else "None"
            )

            response = self._call_with_retry(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data analyst assistant. Generate insightful follow-up questions based on query results."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_completion_tokens=600,
                timeout=OPENAI_CONFIG["timeout"]
            )

            # Log token usage
            if response.usage:
                prompt_details = getattr(response.usage, 'prompt_tokens_details', None)
                cached_tokens = getattr(prompt_details, 'cached_tokens', 0) if prompt_details else 0
                print(f"[GPT] Follow-up suggestions token usage - Input: {response.usage.prompt_tokens}, "
                      f"Output: {response.usage.completion_tokens}, "
                      f"Cached: {cached_tokens}")

            # Parse response
            content = response.choices[0].message.content.strip()

            # Handle potential markdown code blocks
            if content.startswith("```"):
                content = re.sub(r'^```(?:json)?\s*', '', content)
                content = re.sub(r'\s*```$', '', content)

            data = json.loads(content)
            intro_message = data.get("intro_message", "Here are some follow-up questions you might find interesting:")
            suggestions = data.get("suggestions", [])

            # Clean suggestions (just need question now)
            cleaned = []
            for s in suggestions[:4]:  # Limit to 4 suggestions
                if isinstance(s, dict) and "question" in s:
                    cleaned.append(s.get("question", ""))

            print(f"[GPT] Generated {len(cleaned)} follow-up suggestions")
            return {
                "intro_message": intro_message,
                "suggestions": cleaned
            }

        except json.JSONDecodeError as e:
            print(f"[WARNING] Failed to parse follow-up suggestions JSON: {e}")
            return {"intro_message": "", "suggestions": []}
        except Exception as e:
            print(f"[ERROR] Failed to generate follow-up suggestions: {type(e).__name__}: {str(e)}")
            return {"intro_message": "", "suggestions": []}
