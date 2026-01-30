"""
OpenAI API client for generating observations and exploration choices.
"""

from openai import OpenAI, RateLimitError
import json
import time
import re
import os
from typing import List, Dict, Any, Optional, Tuple

from .models import Signal, Observation, ExplorationChoice
from .prompts import (
    generate_observation_prompt,
    generate_choices_prompt,
    generate_follow_up_prompt,
)
from .config import OPENAI_CONFIG, CHART_MAPPINGS


class ProactiveOpenAIClient:
    """Client for OpenAI API interactions for proactive agent"""

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
        """Parse retry_after time from rate limit error message."""
        match = re.search(r'try again in (\d+)s', error_message)
        if match:
            return float(match.group(1))

        match = re.search(r'try again in (\d+)m', error_message)
        if match:
            return float(match.group(1)) * 60

        return 20.0

    def _call_with_retry(self, func, *args, max_retries: int = 2, **kwargs):
        """Call OpenAI API with retry logic."""
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)

            except RateLimitError as e:
                last_error = e
                error_msg = str(e)

                if attempt >= max_retries:
                    print(f"[WARNING] Rate limit exceeded after {max_retries} retries.")
                    raise

                retry_after = self._parse_retry_after(error_msg)
                backoff = min(retry_after, 2 ** attempt)

                print(f"[WARNING] Rate limit hit (attempt {attempt + 1}/{max_retries + 1}). "
                      f"Waiting {backoff:.1f}s before retry...")

                time.sleep(backoff)

            except Exception as e:
                last_error = e
                print(f"[ERROR] OpenAI API call failed: {type(e).__name__}: {str(e)}")
                raise

        if last_error:
            raise last_error

    def generate_observation(
        self,
        signal: Signal,
        table_name: str,
        row_count: int,
        column_names: List[str]
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Generate natural language observation from a signal.

        Args:
            signal: Signal object with detection results
            table_name: Name of the data table
            row_count: Total rows in dataset
            column_names: List of column names

        Returns:
            Tuple of (observation_text, importance, key_insight) or (None, None, None) on failure
        """
        try:
            prompt = generate_observation_prompt(
                signal_type=signal.signal_type.value,
                columns=signal.columns,
                strength=signal.strength,
                metadata=signal.metadata,
                table_name=table_name,
                row_count=row_count,
                column_names=column_names
            )

            response = self._call_with_retry(
                self.client.chat.completions.create,
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=OPENAI_CONFIG.get("temperature", 0.7),
                max_tokens=OPENAI_CONFIG.get("max_tokens", 500),
                response_format={"type": "json_object"},
                timeout=OPENAI_CONFIG.get("timeout", 15),
                max_retries=2
            )

            if response.usage:
                print(f"[GPT] Observation - Input: {response.usage.prompt_tokens}, "
                      f"Output: {response.usage.completion_tokens}")

            content = response.choices[0].message.content
            data = json.loads(content)

            return (
                data.get("observation_text"),
                data.get("importance", "medium"),
                data.get("key_insight")
            )

        except Exception as e:
            print(f"[WARNING] Failed to generate observation: {type(e).__name__}: {str(e)}")
            return None, None, None

    def generate_exploration_choices(
        self,
        observation: Observation,
        signal: Signal,
        available_columns: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Generate exploration choices for an observation.

        Args:
            observation: Observation object
            signal: Original signal
            available_columns: Available columns for exploration

        Returns:
            List of choice dictionaries with text, intent, suggested_groupby, suggested_filter
        """
        try:
            prompt = generate_choices_prompt(
                observation_text=observation.text,
                signal_type=signal.signal_type.value,
                columns=signal.columns,
                metadata=signal.metadata,
                available_columns=available_columns
            )

            response = self._call_with_retry(
                self.client.chat.completions.create,
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=OPENAI_CONFIG.get("temperature", 0.7),
                max_tokens=OPENAI_CONFIG.get("max_tokens", 500),
                response_format={"type": "json_object"},
                timeout=OPENAI_CONFIG.get("timeout", 15),
                max_retries=2
            )

            if response.usage:
                print(f"[GPT] Choices - Input: {response.usage.prompt_tokens}, "
                      f"Output: {response.usage.completion_tokens}")

            content = response.choices[0].message.content
            data = json.loads(content)

            choices = data.get("choices", [])

            # Map intents to chart types
            for choice in choices:
                intent = choice.get("intent", "")
                signal_type = signal.signal_type.value
                chart_map = CHART_MAPPINGS.get(signal_type, {})
                choice["suggested_chart"] = chart_map.get(intent, "table")

            return choices[:3]  # Limit to 3 choices

        except Exception as e:
            print(f"[WARNING] Failed to generate choices: {type(e).__name__}: {str(e)}")
            return []

    def generate_follow_up(
        self,
        choice_text: str,
        result_count: int,
        result_columns: List[str],
        sample_data: List[Dict],
        signal: Signal,
        observation: Observation
    ) -> Tuple[Optional[str], Optional[str], List[Dict[str, Any]]]:
        """
        Generate follow-up observation and choices based on query results.

        Args:
            choice_text: The exploration choice text that was selected
            result_count: Number of rows returned
            result_columns: Column names in results
            sample_data: Sample rows from results
            signal: Original signal
            observation: Current observation

        Returns:
            Tuple of (interpretation, follow_up_observation, follow_up_choices)
        """
        try:
            # Format sample data as string
            sample_str = "\n".join([str(row) for row in sample_data[:5]])

            prompt = generate_follow_up_prompt(
                choice_text=choice_text,
                result_count=result_count,
                result_columns=result_columns,
                sample_data=sample_str,
                signal_type=signal.signal_type.value,
                observation_text=observation.text
            )

            response = self._call_with_retry(
                self.client.chat.completions.create,
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=OPENAI_CONFIG.get("temperature", 0.7),
                max_tokens=OPENAI_CONFIG.get("max_tokens", 500),
                response_format={"type": "json_object"},
                timeout=OPENAI_CONFIG.get("timeout", 15),
                max_retries=2
            )

            if response.usage:
                print(f"[GPT] Follow-up - Input: {response.usage.prompt_tokens}, "
                      f"Output: {response.usage.completion_tokens}")

            content = response.choices[0].message.content
            data = json.loads(content)

            interpretation = data.get("interpretation")
            follow_up_observation = data.get("follow_up_observation")
            follow_up_choices = data.get("follow_up_choices", [])

            # Map intents to chart types
            signal_type = signal.signal_type.value
            chart_map = CHART_MAPPINGS.get(signal_type, {})
            for choice in follow_up_choices:
                intent = choice.get("intent", "")
                choice["suggested_chart"] = chart_map.get(intent, "table")

            return interpretation, follow_up_observation, follow_up_choices[:3]

        except Exception as e:
            print(f"[WARNING] Failed to generate follow-up: {type(e).__name__}: {str(e)}")
            return None, None, []
