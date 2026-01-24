"""
SQL Validator for Text-to-SQL agent.
Provides syntax validation, security checks, and schema compatibility verification.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Set
from difflib import SequenceMatcher

import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Parenthesis
from sqlparse.tokens import Keyword, DML

from .models import SchemaContext
from .config import VALIDATION_CONFIG


@dataclass
class ValidationError:
    """Represents a validation error or warning"""
    error_type: str  # "syntax", "security", "schema", "missing_column", "missing_table"
    message: str
    severity: str  # "error", "warning"
    suggestion: Optional[str] = None
    similar_names: Optional[List[str]] = None


@dataclass
class ValidationResult:
    """Result of SQL validation"""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    normalized_sql: Optional[str] = None


class SQLValidator:
    """
    Validates SQL queries for syntax, security, and schema compatibility.

    Features:
    - Syntax validation using sqlparse
    - Security checks (blocks dangerous operations)
    - Schema validation (verifies columns/tables exist)
    - Fuzzy matching for suggestions on misspelled names
    """

    def __init__(self, schema: SchemaContext):
        """
        Initialize validator with schema context.

        Args:
            schema: SchemaContext containing table name and column information
        """
        self.schema = schema
        self.table_name = schema.table_name.lower()
        self.column_names = {col.name.lower(): col.name for col in schema.columns}
        self.config = VALIDATION_CONFIG

    def validate(self, sql: str) -> ValidationResult:
        """
        Main entry point for SQL validation.

        Args:
            sql: SQL query to validate

        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        # Preprocess SQL: remove double quotes for case-insensitive validation
        sql = self._remove_double_quotes(sql)

        # Check query length
        if len(sql) > self.config["max_query_length"]:
            errors.append(ValidationError(
                error_type="syntax",
                message=f"Query exceeds maximum length of {self.config['max_query_length']} characters.",
                severity="error"
            ))
            return ValidationResult(is_valid=False, errors=errors)

        # Security check first (most important)
        security_errors = self._check_security(sql)
        errors.extend(security_errors)

        if security_errors:
            return ValidationResult(is_valid=False, errors=errors)

        # Syntax validation
        syntax_errors = self._validate_syntax(sql)
        errors.extend(syntax_errors)

        if syntax_errors:
            return ValidationResult(is_valid=False, errors=errors)

        # Schema validation
        schema_result = self._validate_schema(sql)
        errors.extend(schema_result["errors"])
        warnings.extend(schema_result["warnings"])

        # Normalize SQL if valid
        normalized_sql = None
        if not errors:
            normalized_sql = sqlparse.format(
                sql,
                keyword_case='upper',
                identifier_case='lower',
                strip_comments=True
            )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            normalized_sql=normalized_sql
        )

    def _check_security(self, sql: str) -> List[ValidationError]:
        """
        Check for dangerous SQL operations.

        Args:
            sql: SQL query to check

        Returns:
            List of security-related validation errors
        """
        errors = []
        sql_upper = sql.upper()

        for keyword in self.config["dangerous_keywords"]:
            # Match keyword as a whole word (not part of another word)
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, sql_upper):
                errors.append(ValidationError(
                    error_type="security",
                    message=f"Security violation: {keyword} operations are not allowed.",
                    severity="error",
                    suggestion="Only SELECT queries are permitted for data exploration."
                ))

        # Check for multiple statements (SQL injection attempt)
        statements = [s for s in sqlparse.split(sql) if s.strip()]
        if len(statements) > 1:
            errors.append(ValidationError(
                error_type="security",
                message="Multiple SQL statements detected. Only single queries are allowed.",
                severity="error",
                suggestion="Please submit one query at a time."
            ))

        return errors

    def _validate_syntax(self, sql: str) -> List[ValidationError]:
        """
        Validate SQL syntax using sqlparse.

        Args:
            sql: SQL query to validate

        Returns:
            List of syntax-related validation errors
        """
        errors = []

        # Parse the SQL
        try:
            parsed = sqlparse.parse(sql)
        except Exception as e:
            errors.append(ValidationError(
                error_type="syntax",
                message=f"Failed to parse SQL: {str(e)}",
                severity="error"
            ))
            return errors

        if not parsed or not parsed[0].tokens:
            errors.append(ValidationError(
                error_type="syntax",
                message="Empty or invalid SQL query.",
                severity="error"
            ))
            return errors

        statement = parsed[0]

        # Check for SELECT statement
        first_token = statement.token_first(skip_cm=True, skip_ws=True)
        if first_token is None or first_token.ttype not in (DML,) or first_token.value.upper() != 'SELECT':
            errors.append(ValidationError(
                error_type="syntax",
                message="Query must start with SELECT.",
                severity="error",
                suggestion="Only SELECT queries are supported for data exploration."
            ))
            return errors

        # Check for balanced parentheses
        open_count = sql.count('(')
        close_count = sql.count(')')
        if open_count != close_count:
            diff = abs(open_count - close_count)
            if open_count > close_count:
                errors.append(ValidationError(
                    error_type="syntax",
                    message=f"Mismatched parentheses: {open_count} opening, {close_count} closing.",
                    severity="error",
                    suggestion=f"Missing {diff} closing parenthesis(es)."
                ))
            else:
                errors.append(ValidationError(
                    error_type="syntax",
                    message=f"Mismatched parentheses: {open_count} opening, {close_count} closing.",
                    severity="error",
                    suggestion=f"Missing {diff} opening parenthesis(es)."
                ))

        # Check for balanced quotes
        single_quotes = sql.count("'") - sql.count("\\'")
        if single_quotes % 2 != 0:
            errors.append(ValidationError(
                error_type="syntax",
                message="Unmatched single quote detected.",
                severity="error",
                suggestion="Ensure all string literals are properly quoted."
            ))

        double_quotes = sql.count('"') - sql.count('\\"')
        if double_quotes % 2 != 0:
            errors.append(ValidationError(
                error_type="syntax",
                message="Unmatched double quote detected.",
                severity="error",
                suggestion="Ensure all identifiers are properly quoted."
            ))

        return errors

    def _validate_schema(self, sql: str) -> dict:
        """
        Validate that referenced tables and columns exist in the schema.

        Args:
            sql: SQL query to validate

        Returns:
            Dict with "errors" and "warnings" lists
        """
        errors = []
        warnings = []

        # Extract identifiers from the SQL
        sql_lower = sql.lower()

        # Extract potential column names from the SQL
        # This is a simplified extraction - we look for identifiers
        parsed = sqlparse.parse(sql)[0]
        identifiers = self._extract_identifiers(parsed)

        for identifier in identifiers:
            identifier_lower = identifier.lower()

            # Skip if it's the table name
            if identifier_lower == self.table_name:
                continue

            # Skip SQL keywords and functions
            if self._is_sql_keyword_or_function(identifier_lower):
                continue

            # Skip numeric values and strings
            if self._is_literal(identifier):
                continue

            # Skip if it matches an alias pattern (e.g., "t1", "a", etc.)
            if self._is_likely_alias(identifier_lower):
                continue

            # Check if it's a valid column
            if identifier_lower not in self.column_names:
                # Find similar column names
                similar = self._find_similar_names(identifier_lower, list(self.column_names.keys()))

                if similar:
                    original_names = [self.column_names[s] for s in similar]
                    errors.append(ValidationError(
                        error_type="missing_column",
                        message=f"Column '{identifier}' does not exist in table '{self.schema.table_name}'.",
                        severity="error",
                        suggestion=f"Did you mean: {', '.join(original_names)}?",
                        similar_names=original_names
                    ))
                else:
                    # Only warn if we're not confident it's a column reference
                    warnings.append(ValidationError(
                        error_type="schema",
                        message=f"Unknown identifier '{identifier}' - may be a column that doesn't exist.",
                        severity="warning"
                    ))

        return {"errors": errors, "warnings": warnings}

    def _extract_identifiers(self, statement) -> Set[str]:
        """
        Extract all identifiers from a parsed SQL statement.

        Args:
            statement: Parsed sqlparse statement

        Returns:
            Set of identifier names
        """
        identifiers = set()

        def extract_from_token(token):
            if token.ttype is not None:
                # It's a terminal token
                if token.ttype in (sqlparse.tokens.Name, sqlparse.tokens.Name.Placeholder):
                    identifiers.add(token.value)
            elif hasattr(token, 'tokens'):
                # It's a compound token
                if isinstance(token, Identifier):
                    # Get the real name (handle aliases)
                    real_name = token.get_real_name()
                    if real_name:
                        identifiers.add(real_name)
                    # Also check for column references like table.column
                    for sub in token.tokens:
                        if hasattr(sub, 'ttype') and sub.ttype in (sqlparse.tokens.Name,):
                            identifiers.add(sub.value)
                elif isinstance(token, IdentifierList):
                    for item in token.get_identifiers():
                        extract_from_token(item)
                else:
                    for sub in token.tokens:
                        extract_from_token(sub)

        extract_from_token(statement)
        return identifiers

    def _find_similar_names(self, name: str, candidates: List[str]) -> List[str]:
        """
        Find similar names using fuzzy matching.

        Args:
            name: Name to find matches for
            candidates: List of valid names to compare against

        Returns:
            List of similar names above the similarity threshold
        """
        threshold = self.config["suggestion_similarity_threshold"]
        similar = []

        for candidate in candidates:
            ratio = SequenceMatcher(None, name, candidate).ratio()
            if ratio >= threshold:
                similar.append((candidate, ratio))

        # Sort by similarity (highest first) and return top 3
        similar.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in similar[:3]]

    def _is_sql_keyword_or_function(self, word: str) -> bool:
        """Check if word is a SQL keyword or function."""
        keywords = {
            'select', 'from', 'where', 'and', 'or', 'not', 'in', 'between',
            'like', 'is', 'null', 'order', 'by', 'asc', 'desc', 'limit',
            'offset', 'group', 'having', 'join', 'inner', 'left', 'right',
            'outer', 'on', 'as', 'distinct', 'all', 'union', 'intersect',
            'except', 'case', 'when', 'then', 'else', 'end', 'cast', 'true',
            'false', 'with', 'exists', 'any', 'some',
            # Common functions
            'count', 'sum', 'avg', 'min', 'max', 'round', 'coalesce',
            'nullif', 'ifnull', 'concat', 'substring', 'substr', 'trim',
            'upper', 'lower', 'length', 'replace', 'date', 'year', 'month',
            'day', 'hour', 'minute', 'second', 'extract', 'date_trunc',
            'date_diff', 'now', 'current_date', 'current_timestamp', 'abs',
            'ceil', 'floor', 'power', 'sqrt', 'log', 'exp', 'strftime',
            'typeof', 'printf', 'row_number', 'rank', 'dense_rank', 'over',
            'partition', 'rows', 'range', 'unbounded', 'preceding', 'following',
            'current', 'row', 'first_value', 'last_value', 'lead', 'lag',
            'list', 'string_agg', 'array_agg', 'unnest', 'generate_series'
        }
        return word in keywords

    def _is_literal(self, value: str) -> bool:
        """Check if value is a numeric or string literal."""
        # Check for numeric
        try:
            float(value)
            return True
        except ValueError:
            pass

        # Check for quoted string
        if (value.startswith("'") and value.endswith("'")) or \
           (value.startswith('"') and value.endswith('"')):
            return True

        return False

    def _is_likely_alias(self, identifier: str) -> bool:
        """Check if identifier is likely a table alias."""
        # Common alias patterns: single letters, t1, t2, etc.
        if len(identifier) == 1 and identifier.isalpha():
            return True
        if len(identifier) == 2 and identifier[0].isalpha() and identifier[1].isdigit():
            return True
        return False

    def _remove_double_quotes(self, sql: str) -> str:
        """
        Remove double quotes from SQL query for case-insensitive validation.
        Double quotes are used for quoted identifiers which enforce case sensitivity.
        By removing them, we allow case-insensitive matching.

        Args:
            sql: SQL query with potential double-quoted identifiers

        Returns:
            SQL query with double quotes removed from identifiers
        """
        # Remove double quotes that wrap identifiers (e.g., "ColumnName" -> ColumnName)
        # This regex matches double-quoted strings that look like identifiers
        # and replaces them with just the identifier content
        result = re.sub(r'"([^"]+)"', r'\1', sql)
        return result


def create_validator(schema: SchemaContext) -> SQLValidator:
    """
    Factory function to create a SQLValidator.

    Args:
        schema: SchemaContext for validation

    Returns:
        Configured SQLValidator instance
    """
    return SQLValidator(schema)
