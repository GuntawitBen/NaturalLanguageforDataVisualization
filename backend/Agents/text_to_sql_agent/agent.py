"""
Main Text-to-SQL Agent orchestrator.
"""

from typing import Optional, Dict, Any, List, Union

from .models import (
    SchemaContext,
    ChatResponse,
    StartSessionResponse,
    SessionState,
    GPTSQLResponse,
)
from .openai_client import TextToSQLOpenAIClient
from .state_manager import session_manager, build_schema_context
from .config import SQL_CONFIG, VALIDATION_CONFIG
from .sql_validator import SQLValidator, ValidationResult
from ..chart_rec_agent import chart_rec_agent

from database.db_utils import get_dataset, query_dataset


class TextToSQLAgent:
    """Main orchestrator for text-to-SQL operations"""

    def __init__(self):
        self.openai_client = TextToSQLOpenAIClient()

    def start_session(self, dataset_id: str, user_id: str = None) -> StartSessionResponse:
        """
        Start a new chat session for a dataset

        Args:
            dataset_id: Dataset identifier
            user_id: User identifier (for persistence)

        Returns:
            StartSessionResponse with session ID, schema, and sample questions

        Raises:
            ValueError: If dataset not found
        """
        # Verify dataset exists
        dataset = get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset not found: {dataset_id}")

        # Build schema context
        schema = build_schema_context(dataset_id)
        if not schema:
            raise ValueError(f"Failed to build schema for dataset: {dataset_id}")

        # Create session with user_id for persistence
        session = session_manager.create_session(dataset_id, schema, user_id)

        # Generate proactive intro and recommendations
        intro_message, recommendations = self._generate_proactive_intro(schema)

        print(f"[AGENT] Started session {session.session_id} for dataset {dataset_id}")
        print(f"[AGENT] Schema: {len(schema.columns)} columns, {schema.row_count:,} rows")

        # Save the intro message to conversation history with recommendations
        # Wrap in try-catch to prevent breaking session start if persistence fails
        if intro_message:
            try:
                intro_data = {"recommendations": recommendations} if recommendations else None
                session_manager.add_message(
                    session.session_id,
                    "assistant",
                    intro_message,
                    sql_query=None,
                    query_result=None,
                    visualization_recommendations=intro_data
                )
            except Exception as e:
                print(f"[AGENT] Warning: Failed to persist intro message: {e}")

        return StartSessionResponse(
            session_id=session.session_id,
            schema=schema,
            sample_questions=recommendations,
            intro_message=intro_message
        )

    def _generate_proactive_intro(self, schema: SchemaContext) -> tuple[str, list[str]]:
        """
        Generate conversational intro with recommendations.

        Args:
            schema: Schema context for the dataset

        Returns:
            Tuple of (intro_message, list of recommendations)
        """
        try:
            intro, recommendations = self.openai_client.generate_proactive_intro(schema)
            if intro and recommendations:
                print(f"[AGENT] Generated proactive intro with {len(recommendations)} suggestions")
                return intro, recommendations
        except Exception as e:
            print(f"[AGENT] Failed to generate proactive intro: {e}")

        # Fallback - return empty values
        return "", []

    def resume_session(self, session_id: str, user_id: str) -> StartSessionResponse:
        """
        Resume an existing session from history

        Args:
            session_id: Session/conversation identifier
            user_id: User identifier

        Returns:
            StartSessionResponse with session ID, schema, and sample questions

        Raises:
            ValueError: If session not found
        """
        from database.db_utils import get_conversation

        # Get conversation from database
        conversation = get_conversation(session_id)
        if not conversation:
            raise ValueError(f"Session not found: {session_id}")

        dataset_id = conversation['dataset_id']

        # Verify dataset still exists
        dataset = get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset no longer exists: {dataset_id}")

        # Build schema context
        schema = build_schema_context(dataset_id)
        if not schema:
            raise ValueError(f"Failed to build schema for dataset: {dataset_id}")

        # Restore session from database to memory
        session = session_manager.restore_session(session_id, schema, user_id)
        if not session:
            raise ValueError(f"Failed to restore session: {session_id}")

        print(f"[AGENT] Resumed session {session_id} with {len(session.messages)} messages")

        return StartSessionResponse(
            session_id=session.session_id,
            schema=schema,
            sample_questions=[]
        )

    def chat(self, session_id: str, message: str) -> ChatResponse:
        """
        Process a chat message and return SQL + results

        Args:
            session_id: Session identifier
            message: User's natural language question

        Returns:
            ChatResponse with status, SQL, results, or error/clarification

        Raises:
            ValueError: If session not found
        """
        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found or expired: {session_id}")

        # Update activity
        session_manager.update_activity(session_id)

        # Get conversation history (before adding current message)
        messages = session_manager.get_messages(session_id)

        # Detect if user is replying to a clarification/error
        from .prompts import get_last_clarification_context
        clarification_context = get_last_clarification_context(messages)

        # Add user message to history
        session_manager.add_message(session_id, "user", message)

        # Generate SQL
        gpt_response = self.openai_client.generate_sql(
            question=message,
            schema=session.schema,
            messages=messages,
            clarification_context=clarification_context
        )

        # Handle recommendations
        if gpt_response.recommendations:
            explanation = gpt_response.explanation or "Here are some interesting questions you could explore:"
            session_manager.add_message(session_id, "assistant", explanation)

            return ChatResponse(
                status="recommendations",
                message=explanation,
                recommendations=gpt_response.recommendations
            )

        # Handle clarification needed
        if gpt_response.clarification_needed:
            clarification_msg = gpt_response.clarification_needed
            session_manager.add_message(session_id, "assistant", clarification_msg)

            return ChatResponse(
                status="clarification_needed",
                message=clarification_msg
            )

        # Handle error from GPT - use the specific error message
        if gpt_response.error:
            error_msg = gpt_response.error
            session_manager.add_message(session_id, "assistant", error_msg)

            return ChatResponse(
                status="error",
                message=error_msg,
                error_details=gpt_response.error_type
            )

        # Handle missing SQL
        if not gpt_response.sql:
            return ChatResponse(
                status="error",
                message="Failed to generate SQL query.",
                error_details="No SQL was generated by the model."
            )

        sql_query = gpt_response.sql
        explanation = gpt_response.explanation or "Query generated successfully."

        # Validate SQL before execution
        validation_result = self._validate_sql(sql_query, session.schema)

        if not validation_result.is_valid:
            # Try to handle validation errors (auto-fix or return helpful message)
            validation_response = self._handle_validation_error(
                session=session,
                original_sql=sql_query,
                validation_result=validation_result,
                original_question=message
            )
            if isinstance(validation_response, ChatResponse):
                # Return error response to user
                return validation_response
            elif isinstance(validation_response, str):
                # Auto-fix succeeded, use the fixed SQL
                sql_query = validation_response
            # If None, continue with original (shouldn't happen when is_valid=False)
        elif validation_result.normalized_sql:
            # Use normalized SQL if available
            sql_query = validation_result.normalized_sql

        # Execute SQL query
        result = self._execute_sql(session.dataset_id, sql_query)

        # Handle execution error with retry
        if not result["success"]:
            retry_response = self._handle_sql_error(
                session=session,
                original_sql=sql_query,
                error_message=result["error"]
            )
            if retry_response:
                return retry_response

            # Retry failed, return error
            error_msg = f"SQL execution failed: {result['error']}"
            session_manager.add_message(session_id, "assistant", error_msg, sql_query)

            return ChatResponse(
                status="error",
                message="The generated query failed to execute.",
                sql_query=sql_query,
                error_details=result["error"]
            )

        # Success - format results
        results_data = self._format_results(result)

        # Add assistant message with SQL
        response_msg = explanation
        if result.get("row_count", 0) == 0:
            response_msg += " The query returned no results."
        else:
            response_msg += f" Found {result['row_count']:,} rows."

        # Save message with query results for history
        query_result_for_db = {
            "columns": result.get("columns", []),
            "data": results_data,
            "row_count": result.get("row_count", 0)
        }
        
        # Get chart recommendations
        # Map columns in result to their types from schema context
        columns_info = []
        for col_name in result.get("columns", []):
            col_type = "unknown"
            # Try to find type in schema
            for schema_col in session.schema.columns:
                if schema_col.name == col_name:
                    col_type = schema_col.type
                    break
            columns_info.append({"name": col_name, "type": col_type})

        # Get context from previous user message to handle multi-turn requests (e.g. "Scatter plot" -> "with quantity")
        user_question_with_context = message
        last_user_msg = None
        # messages contains history before current turn
        for msg in reversed(messages):
            if msg.role == "user":
                last_user_msg = msg.content
                break
        
        if last_user_msg:
            user_question_with_context = f"Context: {last_user_msg}\nCurrent Request: {message}"

        viz_response = chart_rec_agent.get_recommendations(
            user_question=user_question_with_context,
            sql_query=sql_query,
            columns_info=columns_info,
            sample_data=results_data
        )
        
        viz_recommendations = [rec.model_dump() for rec in viz_response.recommendations] if viz_response else None

        # Add assistant message with SQL and VIZ recommendations to session and DB
        session_manager.add_message(
            session_id,
            "assistant",
            response_msg,
            sql_query,
            query_result_for_db,
            visualization_recommendations=viz_recommendations
        )

        return ChatResponse(
            status="success",
            message=response_msg,
            sql_query=sql_query,
            results=results_data,
            columns=result.get("columns", []),
            row_count=result.get("row_count", 0),
            visualization_recommendations=viz_recommendations
        )

    def _execute_sql(self, dataset_id: str, sql_query: str) -> Dict[str, Any]:
        """
        Execute SQL query on dataset

        Args:
            dataset_id: Dataset identifier
            sql_query: SQL query to execute

        Returns:
            Query result dict with success, data, columns, etc.
        """
        return query_dataset(dataset_id, sql_query)

    def _format_results(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Format query results as list of dicts

        Args:
            result: Raw query result

        Returns:
            List of row dictionaries
        """
        if not result.get("success") or not result.get("data"):
            return []

        columns = result.get("columns", [])
        data = result.get("data", [])

        # Convert tuples to dicts
        from decimal import Decimal

        formatted = []
        for row in data:
            row_dict = {}
            for i, col in enumerate(columns):
                value = row[i] if i < len(row) else None
                # Handle special types for JSON serialization
                if value is not None:
                    if isinstance(value, Decimal):
                        value = float(value)
                    elif hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    elif isinstance(value, (bytes, bytearray)):
                        value = value.decode('utf-8', errors='replace')
                row_dict[col] = value
            formatted.append(row_dict)

        return formatted

    def _handle_sql_error(
        self,
        session: SessionState,
        original_sql: str,
        error_message: str
    ) -> Optional[ChatResponse]:
        """
        Attempt to fix SQL error with GPT retry

        Args:
            session: Current session state
            original_sql: SQL that failed
            error_message: Error from DuckDB

        Returns:
            ChatResponse with fixed results, or None if retry failed
        """
        max_retries = SQL_CONFIG["max_retries"]

        if max_retries <= 0:
            return None

        print(f"[AGENT] Attempting to fix SQL error: {error_message}")

        # Ask GPT to fix the SQL
        fix_response = self.openai_client.fix_sql_error(
            original_sql=original_sql,
            error_message=error_message,
            schema=session.schema
        )

        if fix_response.error or not fix_response.sql:
            print(f"[AGENT] Failed to fix SQL: {fix_response.error}")
            return None

        fixed_sql = fix_response.sql

        # Try executing fixed SQL
        result = self._execute_sql(session.dataset_id, fixed_sql)

        if not result["success"]:
            print(f"[AGENT] Fixed SQL also failed: {result['error']}")
            return None

        # Success with fixed SQL
        results_data = self._format_results(result)
        explanation = fix_response.explanation or "Query was fixed and executed successfully."

        response_msg = f"{explanation} Found {result.get('row_count', 0):,} rows."

        # Save message with query results for history
        query_result_for_db = {
            "columns": result.get("columns", []),
            "data": results_data,
            "row_count": result.get("row_count", 0)
        }
        session_manager.add_message(session.session_id, "assistant", response_msg, fixed_sql, query_result_for_db)

        return ChatResponse(
            status="success",
            message=response_msg,
            sql_query=fixed_sql,
            results=results_data,
            columns=result.get("columns", []),
            row_count=result.get("row_count", 0)
        )

    def _validate_sql(self, sql: str, schema: SchemaContext) -> ValidationResult:
        """
        Validate SQL query for syntax, security, and schema compatibility.

        Args:
            sql: SQL query to validate
            schema: Schema context for validation

        Returns:
            ValidationResult with validation status and errors
        """
        if not VALIDATION_CONFIG.get("enable_syntax_validation", True) and \
           not VALIDATION_CONFIG.get("enable_security_validation", True) and \
           not VALIDATION_CONFIG.get("enable_schema_validation", True):
            # Validation disabled, return valid result
            return ValidationResult(is_valid=True, normalized_sql=sql)

        validator = SQLValidator(schema)
        return validator.validate(sql)

    def _handle_validation_error(
        self,
        session: SessionState,
        original_sql: str,
        validation_result: ValidationResult,
        original_question: str
    ) -> Union[ChatResponse, str, None]:
        """
        Handle validation errors - try to fix or return helpful error message.

        Args:
            session: Current session state
            original_sql: SQL that failed validation
            validation_result: Validation result with errors
            original_question: Original user question

        Returns:
            ChatResponse with error details, or fixed SQL string if auto-fix succeeded
        """
        errors = validation_result.errors

        # Check for security errors first - these cannot be auto-fixed
        security_errors = [e for e in errors if e.error_type == "security"]
        if security_errors:
            error_msg = security_errors[0].message
            suggestion = security_errors[0].suggestion or ""
            full_msg = f"{error_msg} {suggestion}".strip()

            session_manager.add_message(
                session.session_id, "assistant", f"Error: {full_msg}", original_sql
            )

            return ChatResponse(
                status="error",
                message=full_msg,
                sql_query=original_sql,
                error_details=error_msg
            )

        # Check for missing column errors - provide suggestions
        column_errors = [e for e in errors if e.error_type == "missing_column"]
        if column_errors:
            error = column_errors[0]
            error_msg = error.message

            if error.similar_names:
                suggestion = error.suggestion or f"Did you mean: {', '.join(error.similar_names)}?"
                full_msg = f"{error_msg} {suggestion}"

                # Try to auto-fix by asking GPT to regenerate with correct column names
                print(f"[AGENT] Attempting to auto-fix column error: {error_msg}")
                fix_hint = f"The column might be misspelled. Valid columns are: {', '.join([col.name for col in session.schema.columns])}"

                fix_response = self.openai_client.fix_sql_error(
                    original_sql=original_sql,
                    error_message=f"{error_msg} {fix_hint}",
                    schema=session.schema
                )

                if fix_response.sql and not fix_response.error:
                    # Validate the fixed SQL
                    fixed_validation = self._validate_sql(fix_response.sql, session.schema)
                    if fixed_validation.is_valid:
                        # Return the fixed SQL to use
                        print(f"[AGENT] Auto-fixed SQL: {fix_response.sql}")
                        return fixed_validation.normalized_sql or fix_response.sql
            else:
                full_msg = error_msg

            session_manager.add_message(
                session.session_id, "assistant", f"Error: {full_msg}", original_sql
            )

            return ChatResponse(
                status="error",
                message=full_msg,
                sql_query=original_sql,
                error_details=error_msg
            )

        # Handle syntax errors
        syntax_errors = [e for e in errors if e.error_type == "syntax"]
        if syntax_errors:
            error = syntax_errors[0]
            error_msg = error.message
            suggestion = error.suggestion or ""
            full_msg = f"{error_msg} {suggestion}".strip()

            session_manager.add_message(
                session.session_id, "assistant", f"Error: {full_msg}", original_sql
            )

            return ChatResponse(
                status="error",
                message=full_msg,
                sql_query=original_sql,
                error_details=error_msg
            )

        # Handle any other errors
        if errors:
            error = errors[0]
            error_msg = error.message
            suggestion = error.suggestion or ""
            full_msg = f"{error_msg} {suggestion}".strip()

            session_manager.add_message(
                session.session_id, "assistant", f"Error: {full_msg}", original_sql
            )

            return ChatResponse(
                status="error",
                message=full_msg,
                sql_query=original_sql,
                error_details=error_msg
            )

        return None

    def get_session_state(self, session_id: str) -> SessionState:
        """
        Get the current state of a session

        Args:
            session_id: Session identifier

        Returns:
            SessionState

        Raises:
            ValueError: If session not found
        """
        session = session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found or expired: {session_id}")

        return session

    def end_session(self, session_id: str) -> bool:
        """
        End and cleanup a session

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted
        """
        return session_manager.delete_session(session_id)

    def get_follow_up_suggestions(self, session_id: str) -> Dict[str, Any]:
        """
        Generate follow-up suggestions based on the last assistant message with results.

        Args:
            session_id: Session identifier

        Returns:
            Dict with 'intro_message' and 'suggestions' list

        Raises:
            ValueError: If session not found or no valid message to generate from
        """
        session = session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found or expired: {session_id}")

        # Find the last assistant message with SQL query and results
        last_message = None
        last_user_question = None

        for msg in reversed(session.messages):
            if msg.role == "assistant" and msg.sql_query and last_message is None:
                last_message = msg
            elif msg.role == "user" and last_message is not None:
                last_user_question = msg.content
                break

        if not last_message or not last_user_question:
            return {"intro_message": "", "suggestions": []}

        # We need results data - get from the last query execution
        # The results were stored in the message but we need to re-execute or get from DB
        # For now, get the last query results from the conversation messages in DB
        from database.db_utils import get_conversation_messages

        db_messages = get_conversation_messages(session_id)

        # Find the last assistant message with query_result
        result_data = None
        result_columns = []
        row_count = 0

        for msg in reversed(db_messages):
            if msg.get('role') == 'assistant' and msg.get('query_result'):
                query_result = msg['query_result']
                result_data = query_result.get('data', [])
                result_columns = query_result.get('columns', [])
                row_count = query_result.get('row_count', 0)
                break

        if not result_data:
            return {"intro_message": "", "suggestions": []}

        try:
            result = self.openai_client.generate_follow_up_suggestions(
                original_question=last_user_question,
                sql_query=last_message.sql_query,
                result_columns=result_columns,
                sample_results=result_data,
                row_count=row_count,
                schema=session.schema
            )
            return result
        except Exception as e:
            print(f"[AGENT] Failed to generate follow-up suggestions: {e}")
            return {"intro_message": "", "suggestions": []}


# Global agent instance
text_to_sql_agent = TextToSQLAgent()
