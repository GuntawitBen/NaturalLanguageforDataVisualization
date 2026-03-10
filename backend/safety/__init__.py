"""
Safety package for input validation and guardrails.

Uses Guardrails AI framework with custom validators to protect the chatbot:
- Prompt injection detection (user input)
- Indirect prompt injection detection (CSV/data content)
- SQL safety validation (generated queries)
"""

from .guardrails_service import (
    check_input,
    check_data_content,
    check_sql,
    GuardrailResult,
)

__all__ = ["check_input", "check_data_content", "check_sql", "GuardrailResult"]
