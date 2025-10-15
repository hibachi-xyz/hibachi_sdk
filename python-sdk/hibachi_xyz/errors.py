"""Exception hierarchy for the Hibachi SDK.

This module defines the public exception hierarchy for the entire SDK. All exceptions
raised by this library inherit from BaseError.

Exception Hierarchy
-------------------
BaseError
├── ExchangeError - API server returned an error response
├── TransportError - Network/protocol-level errors during transmission
└── ValidationError - Client-side input validation failures
"""


class BaseError(Exception):
    """Base exception for all Hibachi SDK errors.

    All exceptions raised by this library inherit from this class, allowing users
    to catch all SDK-related errors with a single except clause.

    This exception should not be raised directly. Use one of the specific subclasses
    instead (ExchangeError, TransportError, ValidationError).
    """

    pass


# ============================================================================
# EXCHANGE ERROR
# ============================================================================


class ExchangeError(BaseError):
    """Exception raised when the API server returns an error response.

    This exception is raised when a request successfully reaches the API server
    and the server returns a valid response, but that response indicates an error
    condition (e.g., invalid request, rate limit exceeded, authorization failure).

    ExchangeError indicates that:
    - The network connection succeeded
    - The request was properly formatted and transmitted
    - A server processed the request and returned an error response
    """

    pass


class MaintanenceOutage(ExchangeError):
    """Raised when exchange cannot handle response due to maintanence."""

    def __init__(self, message: str):
        """Initialize a MaintanenceOutage error.

        Args:
            message: Description of the maintenance outage error.

        """
        super().__init__(message)


class BadHttpStatus(ExchangeError):
    """Raised when response status from exchange is not 2XX."""

    status_code: int
    message: str

    def __init__(self, status_code: int, message: str):
        """Initialize a BadHttpStatus error.

        Args:
            status_code: The HTTP status code returned by the server.
            message: Description of the HTTP error.

        """
        self.status_code = status_code
        self.message = message


## 5xx status errors - unexpected - should be reported


class InternalServerError(BadHttpStatus):
    """Raised when the server returns a 500 Internal Server Error."""

    pass


class BadGateway(BadHttpStatus):
    """Raised when the server returns a 502 Bad Gateway error."""

    pass


class ServiceUnavailable(BadHttpStatus):
    """Raised when the server returns a 503 Service Unavailable error."""

    pass


class GatewayTimeout(BadHttpStatus):
    """Raised when the server returns a 504 Gateway Timeout error."""

    pass


## 4xx status errors


class BadRequest(BadHttpStatus):
    """Raised when the server returns a 400 Bad Request error."""

    pass


class NotFound(BadHttpStatus):
    """Raised when the server returns a 404 Not Found error."""

    pass


class RateLimited(BadHttpStatus):
    """Raised when the server returns a 429 Rate Limited error."""

    pass


class Unauthorized(BadHttpStatus):
    """Raised when the server returns a 401 Unauthorized error."""

    pass


class Forbidden(BadHttpStatus):
    """Raised when the server returns a 403 Forbidden error."""

    pass


# ============================================================================
# TRANSPORT ERROR
# ============================================================================


class TransportError(BaseError):
    """Exception raised for errors in the process of transporting data to/from the API server.

    This exception is raised when there's a problem in the process of transporting
    data to or from the API server, either in the local networking stack before data
    is sent, during transmission over the network, or when receiving and processing
    data.

    TransportError indicates that:
    - The error occurred in the process of transporting data
    - Valid application-level data was not successfully exchanged
    - The error could be transient and may succeed on retry

    Common causes include:

    Local stack errors (before transmission):
    - Serialization failures (unable to encode data)
    - TLS/SSL certificate errors
    - Local socket/file descriptor exhaustion
    - DNS resolution failures
    - Proxy configuration errors

    Network errors (during transmission):
    - Connection timeouts
    - Connection refused or dropped
    - Network unreachable
    - TLS/SSL handshake failures
    - Read/write timeouts

    Protocol/data handling errors (after transmission):
    - Malformed protocol responses
    - Unexpected connection closure
    - WebSocket connection drops
    - Deserialization failures (malformed or corrupt data)
    """

    pass


class HttpConnectionError(TransportError):
    """Raised when a connection cannot be established or is lost."""

    def __init__(self, message: str, url: str | None = None):
        """Initialize an HttpConnectionError.

        Args:
            message: Description of the connection error.
            url: The URL that failed to connect, if available.

        """
        self.message = message
        self.url = url
        if url:
            super().__init__(f"{message} (url: {url})")
        else:
            super().__init__(message)


class TransportTimeoutError(TransportError):
    """Raised when a request or connection times out."""

    def __init__(self, message: str, timeout_seconds: float | None = None):
        """Initialize a TransportTimeoutError.

        Args:
            message: Description of the timeout error.
            timeout_seconds: The timeout duration in seconds, if available.

        """
        self.message = message
        self.timeout_seconds = timeout_seconds
        if timeout_seconds:
            super().__init__(f"{message} (timeout: {timeout_seconds}s)")
        else:
            super().__init__(message)


class WebSocketConnectionError(TransportError):
    """Raised when WebSocket connection fails or is closed unexpectedly."""

    def __init__(self, message: str, url: str | None = None):
        """Initialize a WebSocketConnectionError.

        Args:
            message: Description of the WebSocket connection error.
            url: The WebSocket URL that failed to connect, if available.

        """
        self.message = message
        self.url = url
        if url:
            super().__init__(f"{message} (url: {url})")
        else:
            super().__init__(message)


class WebSocketMessageError(TransportError):
    """Raised when there's an error processing a WebSocket message."""

    def __init__(self, message: str):
        """Initialize a WebSocketMessageError.

        Args:
            message: Description of the WebSocket message processing error.

        """
        self.message = message
        super().__init__(message)


class DeserializationError(TransportError):
    """Raised when response data cannot be deserialized/decoded."""

    def __init__(self, message: str):
        """Initialize a DeserializationError.

        Args:
            message: Description of the deserialization error.

        """
        self.message = message
        super().__init__(message)


class SerializationError(TransportError):
    """Raised when request data cannot be serialized/encoded."""

    def __init__(self, message: str):
        """Initialize a SerializationError.

        Args:
            message: Description of the serialization error.

        """
        self.message = message
        super().__init__(message)


# ============================================================================
# TRANSPORT ERROR
# ============================================================================


class ValidationError(BaseError):
    """Exception raised for client-side input validation failures.

    This exception is raised when input parameters fail validation checks before
    any request is sent to the API server. ValidationError indicates a problem
    with the arguments provided to SDK methods, such as missing required fields,
    invalid types, out-of-range values, or malformed data.

    ValidationError indicates that:
    - No network request was attempted
    - The error is due to invalid input from the caller
    - The error can be fixed by correcting the input parameters

    Common causes include:
    - Missing required parameters
    - Invalid parameter types (e.g., string instead of number)
    - Out-of-range values
    - Malformed identifiers or formats
    - Mutually exclusive parameters specified together
    """

    pass


class MissingCredentialsError(ValidationError):
    """Raised when required authentication credentials are missing."""

    def __init__(self, credential_type: str = "API key"):
        """Initialize a MissingCredentialsError.

        Args:
            credential_type: The type of credential that is missing (default: "API key").

        """
        self.credential_type = credential_type
        super().__init__(f"{credential_type} is not set")


# ============================================================================
# DEPRECATED TYPES
# ============================================================================


class HibachiApiError(BadHttpStatus):
    """Deprecated - use hibachi_xyz.errors.ExchangeError and subclasses."""

    status_code: int
    message: str

    def __init__(self, status_code: int, message: str):
        """Initialize a HibachiApiError (deprecated).

        Args:
            status_code: The HTTP status code returned by the server.
            message: Description of the API error.

        """
        self.status_code = status_code
        self.message = message
