"""
Unit Tests for Execution Service Error Handling Module.

Tests for error sanitization to address pen test finding L-01:
The /orders endpoint returns raw exception messages exposing internal details.

Governance: CDB_AGENT_POLICY.md, CDB_PSM_POLICY.md
"""

import pytest
import uuid

from services.execution.error_handling import (
    SafeErrorResponse,
    sanitize_error,
    sanitize_database_error,
    sanitize_validation_error,
    # Error message constants
    ERROR_DATABASE_UNAVAILABLE,
    ERROR_VALIDATION_FAILED,
    ERROR_INTERNAL,
    ERROR_SERVICE_UNAVAILABLE,
    ERROR_AUTHENTICATION_FAILED,
    ERROR_NOT_FOUND,
    ERROR_TIMEOUT,
    # Error code constants
    ERROR_CODE_DATABASE,
    ERROR_CODE_VALIDATION,
    ERROR_CODE_INTERNAL,
    ERROR_CODE_SERVICE_UNAVAILABLE,
    ERROR_CODE_AUTHENTICATION,
    ERROR_CODE_NOT_FOUND,
    ERROR_CODE_TIMEOUT,
    # HTTP status codes
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_UNAUTHORIZED,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_INTERNAL_ERROR,
    HTTP_STATUS_SERVICE_UNAVAILABLE,
    HTTP_STATUS_GATEWAY_TIMEOUT,
)
from services.execution.validation import OrderValidationError


# ============================================
# SAFE ERROR RESPONSE CLASS TESTS
# ============================================


class TestSafeErrorResponse:
    """Test SafeErrorResponse dataclass functionality."""

    @pytest.mark.unit
    def test_safe_error_response_creation(self):
        """Test: SafeErrorResponse can be created with required fields."""
        response = SafeErrorResponse(
            code="TEST_ERROR",
            message="Test error message",
        )

        assert response.code == "TEST_ERROR"
        assert response.message == "Test error message"
        assert response.http_status == HTTP_STATUS_INTERNAL_ERROR  # Default
        assert response.details is None

    @pytest.mark.unit
    def test_safe_error_response_with_all_fields(self):
        """Test: SafeErrorResponse can be created with all fields."""
        response = SafeErrorResponse(
            code="VALIDATION_ERROR",
            message="Validation failed",
            request_id="abc123",
            http_status=HTTP_STATUS_BAD_REQUEST,
            details=["Field error 1", "Field error 2"],
        )

        assert response.code == "VALIDATION_ERROR"
        assert response.message == "Validation failed"
        assert response.request_id == "abc123"
        assert response.http_status == HTTP_STATUS_BAD_REQUEST
        assert response.details == ["Field error 1", "Field error 2"]

    @pytest.mark.unit
    def test_safe_error_response_generates_request_id(self):
        """Test: SafeErrorResponse generates request_id if not provided."""
        response = SafeErrorResponse(
            code="TEST_ERROR",
            message="Test message",
        )

        assert response.request_id is not None
        assert len(response.request_id) > 0

    @pytest.mark.unit
    def test_safe_error_response_to_dict(self):
        """Test: SafeErrorResponse.to_dict() returns correct structure."""
        response = SafeErrorResponse(
            code="VALIDATION_ERROR",
            message="Invalid data",
            request_id="req123",
            http_status=HTTP_STATUS_BAD_REQUEST,
        )

        result = response.to_dict()

        assert result["error"] == "Invalid data"
        assert result["code"] == "VALIDATION_ERROR"
        assert result["request_id"] == "req123"
        assert "details" not in result  # No details = not included

    @pytest.mark.unit
    def test_safe_error_response_to_dict_with_details(self):
        """Test: SafeErrorResponse.to_dict() includes details when present."""
        response = SafeErrorResponse(
            code="VALIDATION_ERROR",
            message="Invalid data",
            request_id="req123",
            http_status=HTTP_STATUS_BAD_REQUEST,
            details=["Error 1", "Error 2"],
        )

        result = response.to_dict()

        assert "details" in result
        assert result["details"] == ["Error 1", "Error 2"]

    @pytest.mark.unit
    def test_safe_error_response_str_representation(self):
        """Test: SafeErrorResponse __str__ returns useful info."""
        response = SafeErrorResponse(
            code="TEST_ERROR",
            message="Test message",
            request_id="abc123",
        )

        str_repr = str(response)

        assert "TEST_ERROR" in str_repr
        assert "Test message" in str_repr
        assert "abc123" in str_repr


# ============================================
# DATABASE ERROR SANITIZATION TESTS
# ============================================


class TestDatabaseErrorSanitization:
    """Test database error sanitization - should return safe messages."""

    @pytest.mark.unit
    def test_database_error_returns_safe_message(self):
        """Test: Database errors return safe generic message (L-01 fix)."""
        # Simulate a database error with internal details
        exception = Exception("FATAL: password authentication failed for user 'admin'")

        response = sanitize_database_error(exception)

        assert response.message == ERROR_DATABASE_UNAVAILABLE
        assert response.code == ERROR_CODE_DATABASE
        assert response.http_status == HTTP_STATUS_SERVICE_UNAVAILABLE
        # Internal details should NOT be in message
        assert "password" not in response.message
        assert "admin" not in response.message

    @pytest.mark.unit
    def test_database_error_with_request_id(self):
        """Test: Database error sanitization preserves provided request_id."""
        exception = Exception("Connection refused to database server")

        response = sanitize_database_error(exception, request_id="custom-123")

        assert response.request_id == "custom-123"
        assert response.message == ERROR_DATABASE_UNAVAILABLE

    @pytest.mark.unit
    def test_database_error_generates_request_id_if_not_provided(self):
        """Test: Database error generates request_id when not provided."""
        exception = Exception("Database connection timeout")

        response = sanitize_database_error(exception)

        assert response.request_id is not None
        assert len(response.request_id) > 0

    @pytest.mark.unit
    def test_database_error_hides_connection_string(self):
        """Test: Connection strings with credentials are not exposed."""
        exception = Exception(
            "could not connect to server: postgresql://admin:secret@db.internal:5432/production"
        )

        response = sanitize_database_error(exception)

        assert "postgresql" not in response.message
        assert "admin" not in response.message
        assert "secret" not in response.message
        assert "db.internal" not in response.message

    @pytest.mark.unit
    def test_database_error_hides_table_names(self):
        """Test: Internal table names are not exposed."""
        exception = Exception(
            "relation 'users_credentials' does not exist at character 15"
        )

        response = sanitize_database_error(exception)

        assert "users_credentials" not in response.message
        assert "relation" not in response.message


# ============================================
# VALIDATION ERROR SANITIZATION TESTS
# ============================================


class TestValidationErrorSanitization:
    """Test validation error sanitization - should return safe messages."""

    @pytest.mark.unit
    def test_validation_error_returns_safe_message(self):
        """Test: Validation errors return safe generic message."""
        exception = ValueError("Internal validation logic failed on field X")

        response = sanitize_error(exception)

        assert response.message == ERROR_VALIDATION_FAILED
        assert response.code == ERROR_CODE_VALIDATION
        assert response.http_status == HTTP_STATUS_BAD_REQUEST

    @pytest.mark.unit
    def test_type_error_returns_validation_message(self):
        """Test: TypeError returns validation error message."""
        exception = TypeError("expected str, got NoneType")

        response = sanitize_error(exception)

        assert response.message == ERROR_VALIDATION_FAILED
        assert response.code == ERROR_CODE_VALIDATION

    @pytest.mark.unit
    def test_key_error_returns_validation_message(self):
        """Test: KeyError returns validation error message."""
        exception = KeyError("missing_field")

        response = sanitize_error(exception)

        assert response.message == ERROR_VALIDATION_FAILED
        assert response.code == ERROR_CODE_VALIDATION

    @pytest.mark.unit
    def test_sanitize_validation_error_convenience_function(self):
        """Test: sanitize_validation_error convenience function works."""
        exception = Exception("Some validation issue")

        response = sanitize_validation_error(exception, request_id="val-123")

        assert response.message == ERROR_VALIDATION_FAILED
        assert response.code == ERROR_CODE_VALIDATION
        assert response.request_id == "val-123"
        assert response.http_status == HTTP_STATUS_BAD_REQUEST

    @pytest.mark.unit
    def test_sanitize_validation_error_with_details(self):
        """Test: sanitize_validation_error can include safe details."""
        exception = Exception("Validation failed")
        safe_details = ["Symbol format invalid", "Quantity must be positive"]

        response = sanitize_validation_error(
            exception, request_id="val-456", details=safe_details
        )

        assert response.details == safe_details

    @pytest.mark.unit
    def test_order_validation_error_preserves_safe_message(self):
        """Test: OrderValidationError message is preserved (already safe)."""
        exception = OrderValidationError(
            message="Order validation failed",
            details=["Invalid symbol format", "Quantity must be positive"],
        )

        response = sanitize_error(exception)

        assert response.message == "Order validation failed"
        assert response.code == ERROR_CODE_VALIDATION
        assert response.http_status == HTTP_STATUS_BAD_REQUEST
        assert response.details == ["Invalid symbol format", "Quantity must be positive"]


# ============================================
# UNKNOWN/GENERIC ERROR SANITIZATION TESTS
# ============================================


class TestUnknownErrorSanitization:
    """Test unknown exception sanitization - should return generic message."""

    @pytest.mark.unit
    def test_unknown_exception_returns_generic_message(self):
        """Test: Unknown exception types return generic internal error."""
        # Custom exception not in mapping
        class CustomInternalException(Exception):
            pass

        exception = CustomInternalException("Secret internal error details")

        response = sanitize_error(exception)

        assert response.message == ERROR_INTERNAL
        assert response.code == ERROR_CODE_INTERNAL
        assert response.http_status == HTTP_STATUS_INTERNAL_ERROR
        # Internal details should NOT be exposed
        assert "Secret" not in response.message
        assert "internal error details" not in response.message

    @pytest.mark.unit
    def test_generic_exception_returns_safe_message(self):
        """Test: Generic Exception returns safe internal error message."""
        exception = Exception("Some detailed internal error")

        response = sanitize_error(exception)

        # Generic Exception should return internal error
        assert response.code == ERROR_CODE_INTERNAL
        assert "detailed" not in response.message

    @pytest.mark.unit
    def test_exception_with_sensitive_data_sanitized(self):
        """Test: Exceptions containing sensitive data are sanitized."""
        exception = Exception(
            "Error processing user 12345 with token abc123xyz"
        )

        response = sanitize_error(exception)

        # No sensitive data in response
        assert "12345" not in response.message
        assert "abc123xyz" not in response.message
        assert "token" not in response.message


# ============================================
# SPECIFIC EXCEPTION TYPE TESTS
# ============================================


class TestSpecificExceptionTypes:
    """Test sanitization of specific exception types."""

    @pytest.mark.unit
    def test_timeout_error_returns_timeout_message(self):
        """Test: TimeoutError returns appropriate timeout message."""
        exception = TimeoutError("Operation timed out after 30s")

        response = sanitize_error(exception)

        assert response.message == ERROR_TIMEOUT
        assert response.code == ERROR_CODE_TIMEOUT
        assert response.http_status == HTTP_STATUS_GATEWAY_TIMEOUT

    @pytest.mark.unit
    def test_connection_error_returns_service_unavailable(self):
        """Test: ConnectionError returns service unavailable message."""
        exception = ConnectionError("Could not connect to redis:6379")

        response = sanitize_error(exception)

        assert response.message == ERROR_SERVICE_UNAVAILABLE
        assert response.code == ERROR_CODE_SERVICE_UNAVAILABLE
        assert response.http_status == HTTP_STATUS_SERVICE_UNAVAILABLE
        # Internal host:port should not be exposed
        assert "redis" not in response.message
        assert "6379" not in response.message

    @pytest.mark.unit
    def test_permission_error_returns_auth_failed(self):
        """Test: PermissionError returns authentication failed message."""
        exception = PermissionError("Access denied for user 'system'")

        response = sanitize_error(exception)

        assert response.message == ERROR_AUTHENTICATION_FAILED
        assert response.code == ERROR_CODE_AUTHENTICATION
        assert response.http_status == HTTP_STATUS_UNAUTHORIZED
        assert "system" not in response.message

    @pytest.mark.unit
    def test_file_not_found_error_returns_not_found(self):
        """Test: FileNotFoundError returns not found message."""
        exception = FileNotFoundError("/etc/secrets/api_key.json not found")

        response = sanitize_error(exception)

        assert response.message == ERROR_NOT_FOUND
        assert response.code == ERROR_CODE_NOT_FOUND
        assert response.http_status == HTTP_STATUS_NOT_FOUND
        # Internal paths should not be exposed
        assert "/etc" not in response.message
        assert "secrets" not in response.message
        assert "api_key" not in response.message

    @pytest.mark.unit
    def test_os_error_returns_internal_error(self):
        """Test: OSError returns internal error message."""
        exception = OSError("Disk full: /var/lib/data")

        response = sanitize_error(exception)

        assert response.message == ERROR_INTERNAL
        assert response.code == ERROR_CODE_INTERNAL
        assert "/var/lib" not in response.message


# ============================================
# REQUEST ID HANDLING TESTS
# ============================================


class TestRequestIdHandling:
    """Test request_id handling in error responses."""

    @pytest.mark.unit
    def test_request_id_included_in_response(self):
        """Test: request_id is always included in response."""
        exception = Exception("Test error")

        response = sanitize_error(exception)

        assert response.request_id is not None
        assert len(response.request_id) > 0

    @pytest.mark.unit
    def test_provided_request_id_preserved(self):
        """Test: Provided request_id is preserved in response."""
        exception = Exception("Test error")

        response = sanitize_error(exception, request_id="custom-req-456")

        assert response.request_id == "custom-req-456"

    @pytest.mark.unit
    def test_request_id_in_to_dict_output(self):
        """Test: request_id appears in to_dict() output."""
        exception = Exception("Test error")

        response = sanitize_error(exception, request_id="dict-test-789")
        result = response.to_dict()

        assert result["request_id"] == "dict-test-789"

    @pytest.mark.unit
    def test_generated_request_id_format(self):
        """Test: Generated request_id has expected format (8 chars from UUID)."""
        exception = Exception("Test error")

        response = sanitize_error(exception)

        # Should be 8 characters (first 8 chars of UUID)
        assert len(response.request_id) == 8


# ============================================
# SECURITY TESTS (Information Disclosure Prevention)
# ============================================


class TestSecurityNoInformationDisclosure:
    """Test that error responses don't expose sensitive information (L-01)."""

    @pytest.mark.unit
    def test_no_stack_traces_in_response(self):
        """Test: Stack traces are never included in responses."""
        try:
            raise ValueError("Test error with traceback")
        except ValueError as e:
            response = sanitize_error(e)

        result = response.to_dict()
        result_str = str(result)

        assert "traceback" not in result_str.lower()
        assert "File" not in result_str or "field" in result_str.lower()
        assert "line" not in result_str.lower() or "line" == result_str.lower()

    @pytest.mark.unit
    def test_no_file_paths_in_response(self):
        """Test: File paths are never included in responses."""
        exception = Exception(
            "Error in /home/user/app/services/execution/service.py:123"
        )

        response = sanitize_error(exception)
        result_str = str(response.to_dict())

        assert "/home/" not in result_str
        assert "/app/" not in result_str
        assert "service.py" not in result_str

    @pytest.mark.unit
    def test_no_sql_queries_in_response(self):
        """Test: SQL queries are never included in responses."""
        exception = Exception(
            "Error executing: SELECT * FROM users WHERE password = 'secret123'"
        )

        response = sanitize_error(exception)
        result_str = str(response.to_dict())

        assert "SELECT" not in result_str
        assert "FROM" not in result_str
        assert "users" not in result_str
        assert "password" not in result_str
        assert "secret123" not in result_str

    @pytest.mark.unit
    def test_no_api_keys_in_response(self):
        """Test: API keys are never included in responses."""
        exception = Exception(
            "Authentication failed with API key: sk-1234567890abcdef"
        )

        response = sanitize_error(exception)
        result_str = str(response.to_dict())

        assert "sk-" not in result_str
        assert "1234567890" not in result_str
        assert "abcdef" not in result_str

    @pytest.mark.unit
    def test_no_environment_variables_in_response(self):
        """Test: Environment variable names are never included in responses."""
        exception = Exception(
            "Missing required environment variable: DATABASE_PASSWORD"
        )

        response = sanitize_error(exception)
        result_str = str(response.to_dict())

        assert "DATABASE_PASSWORD" not in result_str
        assert "environment" not in result_str.lower()

    @pytest.mark.unit
    def test_no_internal_hostnames_in_response(self):
        """Test: Internal hostnames are never included in responses."""
        exception = Exception(
            "Failed to connect to db-primary.internal.company.com:5432"
        )

        response = sanitize_error(exception)
        result_str = str(response.to_dict())

        assert "db-primary" not in result_str
        assert ".internal." not in result_str
        assert "company.com" not in result_str
        assert "5432" not in result_str

    @pytest.mark.unit
    def test_no_exception_class_details_in_response(self):
        """Test: Exception class names/details not exposed to client."""
        class CustomSecretException(Exception):
            """This has internal documentation."""
            pass

        exception = CustomSecretException("Internal secret")

        response = sanitize_error(exception)
        result_str = str(response.to_dict())

        assert "CustomSecretException" not in result_str
        assert "Internal secret" not in result_str


# ============================================
# RESPONSE STRUCTURE TESTS
# ============================================


class TestResponseStructure:
    """Test the structure of error responses."""

    @pytest.mark.unit
    def test_response_has_required_fields(self):
        """Test: Response dictionary has all required fields."""
        exception = Exception("Test error")

        response = sanitize_error(exception)
        result = response.to_dict()

        assert "error" in result
        assert "code" in result
        assert "request_id" in result

    @pytest.mark.unit
    def test_response_error_is_string(self):
        """Test: Error message is a string."""
        exception = Exception("Test error")

        response = sanitize_error(exception)
        result = response.to_dict()

        assert isinstance(result["error"], str)

    @pytest.mark.unit
    def test_response_code_is_string(self):
        """Test: Error code is a string."""
        exception = Exception("Test error")

        response = sanitize_error(exception)
        result = response.to_dict()

        assert isinstance(result["code"], str)

    @pytest.mark.unit
    def test_response_request_id_is_string(self):
        """Test: Request ID is a string."""
        exception = Exception("Test error")

        response = sanitize_error(exception)
        result = response.to_dict()

        assert isinstance(result["request_id"], str)

    @pytest.mark.unit
    def test_http_status_is_appropriate_for_error_type(self):
        """Test: HTTP status codes are appropriate for error types."""
        # Validation error -> 400
        response = sanitize_error(ValueError("test"))
        assert response.http_status == HTTP_STATUS_BAD_REQUEST

        # Connection error -> 503
        response = sanitize_error(ConnectionError("test"))
        assert response.http_status == HTTP_STATUS_SERVICE_UNAVAILABLE

        # Timeout -> 504
        response = sanitize_error(TimeoutError("test"))
        assert response.http_status == HTTP_STATUS_GATEWAY_TIMEOUT

        # Permission error -> 401
        response = sanitize_error(PermissionError("test"))
        assert response.http_status == HTTP_STATUS_UNAUTHORIZED

        # Not found -> 404
        response = sanitize_error(FileNotFoundError("test"))
        assert response.http_status == HTTP_STATUS_NOT_FOUND


# ============================================
# ERROR CONSTANTS TESTS
# ============================================


class TestErrorConstants:
    """Test error message and code constants."""

    @pytest.mark.unit
    def test_error_message_constants_defined(self):
        """Test: All error message constants are defined."""
        assert ERROR_DATABASE_UNAVAILABLE is not None
        assert ERROR_VALIDATION_FAILED is not None
        assert ERROR_INTERNAL is not None
        assert ERROR_SERVICE_UNAVAILABLE is not None
        assert ERROR_AUTHENTICATION_FAILED is not None
        assert ERROR_NOT_FOUND is not None
        assert ERROR_TIMEOUT is not None

    @pytest.mark.unit
    def test_error_message_constants_are_strings(self):
        """Test: All error message constants are strings."""
        assert isinstance(ERROR_DATABASE_UNAVAILABLE, str)
        assert isinstance(ERROR_VALIDATION_FAILED, str)
        assert isinstance(ERROR_INTERNAL, str)
        assert isinstance(ERROR_SERVICE_UNAVAILABLE, str)

    @pytest.mark.unit
    def test_error_code_constants_defined(self):
        """Test: All error code constants are defined."""
        assert ERROR_CODE_DATABASE is not None
        assert ERROR_CODE_VALIDATION is not None
        assert ERROR_CODE_INTERNAL is not None
        assert ERROR_CODE_SERVICE_UNAVAILABLE is not None
        assert ERROR_CODE_AUTHENTICATION is not None
        assert ERROR_CODE_NOT_FOUND is not None
        assert ERROR_CODE_TIMEOUT is not None

    @pytest.mark.unit
    def test_http_status_constants_defined(self):
        """Test: All HTTP status code constants are defined."""
        assert HTTP_STATUS_BAD_REQUEST == 400
        assert HTTP_STATUS_UNAUTHORIZED == 401
        assert HTTP_STATUS_NOT_FOUND == 404
        assert HTTP_STATUS_INTERNAL_ERROR == 500
        assert HTTP_STATUS_SERVICE_UNAVAILABLE == 503
        assert HTTP_STATUS_GATEWAY_TIMEOUT == 504

    @pytest.mark.unit
    def test_error_messages_are_safe_for_users(self):
        """Test: Error messages are appropriate for end users."""
        # Messages should be generic and not reveal internals
        safe_messages = [
            ERROR_DATABASE_UNAVAILABLE,
            ERROR_VALIDATION_FAILED,
            ERROR_INTERNAL,
            ERROR_SERVICE_UNAVAILABLE,
            ERROR_AUTHENTICATION_FAILED,
            ERROR_NOT_FOUND,
            ERROR_TIMEOUT,
        ]

        for message in safe_messages:
            # Should not contain technical terms that expose architecture
            assert "sql" not in message.lower()
            assert "query" not in message.lower()
            assert "connection pool" not in message.lower()
            assert "redis" not in message.lower()
            assert "postgres" not in message.lower()


# ============================================
# LOGGING BEHAVIOR TESTS
# ============================================


class TestLoggingBehavior:
    """Test that errors are properly logged while sanitized for response."""

    @pytest.mark.unit
    def test_sanitize_error_with_logging_disabled(self):
        """Test: sanitize_error works with logging disabled."""
        exception = Exception("Internal details")

        # This should not raise even with logging disabled
        response = sanitize_error(exception, log_full_error=False)

        assert response.message == ERROR_INTERNAL
        assert response.request_id is not None

    @pytest.mark.unit
    def test_sanitize_error_with_logging_enabled(self):
        """Test: sanitize_error works with logging enabled (default)."""
        exception = Exception("Internal details")

        # Default behavior includes logging
        response = sanitize_error(exception)

        assert response.message == ERROR_INTERNAL
        assert response.request_id is not None
