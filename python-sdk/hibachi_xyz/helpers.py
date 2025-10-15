"""Helper utilities for the Hibachi Python SDK.

This module contains utility functions for serialization, deserialization,
API response handling, WebSocket management, and display formatting.
"""

import inspect
import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from time import time
from types import NoneType
from typing import Any, Callable, Dict, TypeVar, get_args, get_origin

import orjson
from prettyprinter import cpprint

from hibachi_xyz.errors import (
    DeserializationError,
    MaintanenceOutage,
    SerializationError,
)
from hibachi_xyz.types import (
    BatchResponseOrder,
    CancelOrderBatchResponse,
    CreateOrderBatchResponse,
    ErrorBatchResponse,
    ExchangeInfo,
    HibachiNumericInput,
    Json,
    JsonObject,
    MaintenanceWindow,
    UpdateOrderBatchResponse,
    numeric_to_decimal,
)

log = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

DEFAULT_API_URL: str = "https://api.hibachi.xyz"
DEFAULT_DATA_API_URL: str = "https://data-api.hibachi.xyz"


# ============================================================================
# CLIENT IDENTIFICATION
# ============================================================================


@lru_cache(maxsize=1)
def get_hibachi_client() -> str:
    """Get the Hibachi client identification string."""
    import hibachi_xyz

    return f"HibachiPythonSDK/{hibachi_xyz.__version__}"


# ============================================================================
# REFLECTION UTILITIES
# ============================================================================


@lru_cache(maxsize=1)
def _required_fields(signature: inspect.Signature) -> list[str]:
    """Extract list of required parameter names from a function signature.

    Returns parameter names that have no default value and are positional
    or keyword parameters.
    """
    return [
        name
        for name, param in signature.parameters.items()
        if param.default is inspect._empty
        and param.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
    ]


@lru_cache(maxsize=1)
def _required_nullable_fields(signature: inspect.Signature) -> list[str]:
    """Return names of parameters that are required and whose annotation allows None.

    This is useful for determining which fields should be explicitly set to None
    when constructing objects from partial data.
    """
    required_nullable: list[str] = []
    for name, param in signature.parameters.items():
        # only return required fields
        if name not in _required_fields(signature):
            continue

        # can only handle annotated fields
        ann = param.annotation
        if ann is inspect._empty:
            continue

        origin, args = get_origin(ann), get_args(ann)

        # annotation is None
        if ann is NoneType:
            required_nullable.append(name)
        # annotation is a Union including None
        elif origin is not None and NoneType in args:
            required_nullable.append(name)

    return required_nullable


# ============================================================================
# OBJECT CONSTRUCTION
# ============================================================================

T = TypeVar("T")


def create_with(
    func: Callable[..., T], data: Dict[str, Any], *, implicit_null: bool = False
) -> T:
    """Create an object from a dictionary, filtering to only valid parameters.

    This allows constructing objects from API responses that may contain
    additional fields beyond what the constructor expects, making the SDK
    more resilient to API changes.

    Args:
        func: Constructor or factory function to call
        data: Dictionary of data to pass as kwargs
        implicit_null: If True, add explicit None values for required nullable fields

    Returns:
        Instance created by calling func with filtered data

    """
    sig = inspect.signature(func)
    valid_keys = sig.parameters.keys()
    filtered_data = {k: v for k, v in data.items() if k in valid_keys}
    if implicit_null:
        missing_fields = (
            field
            for field in _required_nullable_fields(sig)
            if field not in filtered_data
        )
        filtered_data.update({field: None for field in missing_fields})

    return func(**filtered_data)


# ============================================================================
# SERIALIZATION / DESERIALIZATION
# ============================================================================


def decimal_as_str(obj: object) -> str:
    """Serialize Decimal objects to JSON strings.

    Converts Decimal to string to preserve precision in JSON serialization.
    """
    if isinstance(obj, Decimal):
        return str(obj)

    raise TypeError


def serialize_request(request: Json | None) -> bytes | None:
    """Serialize a request object to JSON bytes.

    Uses orjson for fast serialization with custom Decimal handling.

    Args:
        request: Request data to serialize

    Returns:
        JSON bytes or None if request is None

    Raises:
        SerializationError: If serialization fails

    """
    if request is None:
        return None
    try:
        return orjson.dumps(request, default=decimal_as_str)
    except Exception as e:
        raise SerializationError(f"Failed to serialize {request=}") from e


def deserialize_response(response_body: bytes, url: str) -> Json:
    """Deserialize a JSON response body.

    Args:
        response_body: Response bytes to deserialize
        url: URL that was requested (for error messages)

    Returns:
        Deserialized JSON object or array

    Raises:
        DeserializationError: If deserialization fails

    """
    try:
        return orjson.loads(response_body)  # type: ignore
    except Exception as e:
        raise DeserializationError(
            f"Failed to parse JSON response from {url}: {e}"
        ) from e


def deserialize_batch_response_order(
    data: JsonObject,
) -> BatchResponseOrder:
    """Deserialize a batch response order based on which fields are present.

    Logic:
    - If 'errorCode' is present -> ErrorBatchResponse
    - If both 'nonce' and 'orderId' are present -> CreateOrderBatchResponse
    - If only 'orderId' is present -> UpdateOrderBatchResponse
    - If only 'nonce' is present -> CancelOrderBatchResponse

    Args:
        data: JSON object to deserialize

    Returns:
        Appropriate batch response type

    Raises:
        DeserializationError: If the data cannot be deserialized into any known type

    """
    try:
        for k in list(data.keys()):
            if data[k] is None:
                del data[k]
        if "errorCode" in data:
            return create_with(ErrorBatchResponse, data)
        elif "nonce" in data and "orderId" in data:
            return create_with(CreateOrderBatchResponse, data)
        elif "orderId" in data:
            return create_with(UpdateOrderBatchResponse, data)
        elif "nonce" in data:
            return create_with(CancelOrderBatchResponse, data)
        else:
            raise DeserializationError(
                f"Unknown batch response order format - missing required fields: {data}"
            )
    except (TypeError, KeyError, ValueError) as e:
        raise DeserializationError(
            f"Failed to deserialize batch response order: {data}"
        ) from e


# ============================================================================
# MAINTENANCE WINDOW HANDLING
# ============================================================================


def check_maintenance_window(response: JsonObject) -> None:
    """Check API response for maintenance status and raise exception if found.

    This function inspects an API response for a status field indicating exchange health.
    The exchange can be in one of three states:
    - NORMAL: Exchange is operating normally (no exception raised)
    - SCHEDULED_MAINTENANCE: Exchange is undergoing scheduled maintenance with known timing
    - UNSCHEDULED_MAINTENANCE: Exchange is undergoing unscheduled maintenance

    When any MAINTENANCE status is detected, a MaintanenceOutage exception is raised with
    details about the maintenance window timing (if available for scheduled maintenance).

    Args:
        response: JSON response from the API containing potential maintenance information

    Raises:
        MaintanenceOutage: If status is anything other than "NORMAL",
            with a message containing human-readable UTC timestamps for scheduled windows

    """
    # Only return early if status is NORMAL
    status = response.get("status")
    if status == "NORMAL":
        return

    # Build message based on maintenance type
    if status == "UNSCHEDULED_MAINTENANCE":
        raise MaintanenceOutage(
            "Exchange is currently undergoing unscheduled maintenance"
        )

    # Handle scheduled maintenance with timing details
    if status == "SCHEDULED_MAINTENANCE":
        message_parts = ["Exchange is currently undergoing scheduled maintenance"]
    else:
        # Unknown status - still raise but with generic message
        raise MaintanenceOutage(f"Exchange is currently unavailable (status: {status})")

    # Try to extract additional details from currentMaintenanceWindow if present
    current_window = response.get("currentMaintenanceWindow")
    if isinstance(current_window, dict):
        # Extract and format timestamps if available
        begin_timestamp = current_window.get("begin")
        end_timestamp = current_window.get("end")

        # Check if we have at least one timestamp
        has_begin = isinstance(begin_timestamp, (int, float))
        has_end = isinstance(end_timestamp, (int, float))

        if has_begin or has_end:
            # Format begin time or use placeholder
            if has_begin:
                try:
                    begin_time = datetime.fromtimestamp(begin_timestamp).strftime(  # type: ignore
                        "%Y-%m-%d %H:%M:%S UTC"
                    )
                except (ValueError, OSError):
                    begin_time = "<unknown>"
            else:
                begin_time = "<unknown>"

            # Format end time or use placeholder
            if has_end:
                try:
                    end_time = datetime.fromtimestamp(end_timestamp).strftime(  # type: ignore
                        "%Y-%m-%d %H:%M:%S UTC"
                    )
                except (ValueError, OSError):
                    end_time = "<unknown>"
            else:
                end_time = "<unknown>"

            message_parts[0] += f" from {begin_time} to {end_time}"

        # Add note if available
        note = current_window.get("note")
        if isinstance(note, str) and note:
            message_parts.append(f"Reason: {note}")

    raise MaintanenceOutage(". ".join(message_parts))


def get_next_maintenance_window(
    exchange_info: ExchangeInfo,
) -> MaintenanceWindow | None:
    """Get the next scheduled maintenance window if any exists.

    Args:
        exchange_info: The exchange information containing maintenance windows

    Returns:
        Details about the next maintenance window or None if none exists

    """
    windows = exchange_info.maintenanceWindow
    if not windows:
        return None

    now = datetime.now().timestamp()
    future_windows = [w for w in windows if w.begin > now]

    if not future_windows:
        return None

    next_window = min(future_windows, key=lambda w: w.begin)

    return next_window


def format_maintenance_window(window_info: MaintenanceWindow | None) -> str:
    """Format maintenance window information into a user-friendly string.

    Args:
        window_info: Maintenance window information from get_next_maintenance_window

    Returns:
        Formatted string with maintenance window details

    """
    if window_info is None:
        return "No upcoming maintenance windows scheduled."

    # Calculate time until maintenance starts
    now = datetime.now()
    start_time = datetime.fromtimestamp(window_info.begin)
    time_until = start_time - now

    duration_hours_raw = Decimal((window_info.end - window_info.begin) / 3600.0)

    # Calculate days, hours, minutes
    days = time_until.days
    hours, remainder = divmod(time_until.seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    # Format the start time
    start_str = start_time.strftime("%d %B %Y at %H:%M")

    # Format the duration
    if duration_hours_raw < 1:
        duration_str = f"{int(duration_hours_raw * 60)} minutes"
    else:
        duration_str = (
            f"{int(duration_hours_raw)} hour{'s' if duration_hours_raw != 1 else ''}"
        )

    # Combine all information
    return (
        f"The next maintenance window starts in {days}d{hours}h{minutes}m on {start_str} "
        f"for a duration of {duration_str}. "
        f"Reason: {window_info.note}."
    )


# ============================================================================
# EXCHANGE INFORMATION UTILITIES
# ============================================================================


def get_withdrawal_fee_for_amount(
    exchange_info: ExchangeInfo, amount: HibachiNumericInput
) -> int | float:
    """Calculate the instant withdrawal fee for a given amount.

    Fees are tiered based on withdrawal amount. This function finds the
    appropriate fee tier for the given amount.

    Args:
        exchange_info: The exchange information containing fee tiers
        amount: Withdrawal amount

    Returns:
        Fee percentage/amount for the withdrawal

    """
    amount = numeric_to_decimal(amount)
    fees = exchange_info.feeConfig.instantWithdrawalFees
    # Sort fees by threshold (highest first)
    sorted_fees = sorted(fees, key=lambda x: x[0], reverse=True)

    for threshold, fee in sorted_fees:
        if amount >= threshold:
            return fee

    # Default to highest fee if amount is below all thresholds
    return sorted_fees[-1][1]


# ============================================================================
# TIME UTILITIES
# ============================================================================


def absolute_creation_deadline(relative_creation_deadline: Decimal) -> int:
    """Convert a relative creation deadline (in seconds) to an absolute timestamp.

    Note: This is based on wall time and can drift. Server-side uses NTP with
    chrony AWS Time Sync Service. If client time is significantly off from
    server time, this may not function as expected.

    TODO: This should be able to return a float but API server currently can't handle that

    Args:
        relative_creation_deadline: Deadline in seconds from now

    Returns:
        Unix timestamp as integer

    """
    return int(relative_creation_deadline + Decimal(time()))


# ============================================================================
# DISPLAY UTILITIES
# ============================================================================


def print_data(response: Any) -> None:
    """Pretty-print response data, handling dataclasses specially.

    Dataclass instances are converted to dictionaries before printing
    for better formatting.

    Args:
        response: Data to print

    """
    if is_dataclass(response) and not isinstance(response, type):
        cpprint(asdict(response))
    else:
        cpprint(response)
