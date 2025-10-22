"""Environment configuration setup utilities.

This module provides functions for loading environment variables from .env files
and configuring the SDK for local development.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from hibachi_xyz.errors import ValidationError

log = logging.getLogger(__name__)


def setup_environment() -> tuple[str, str, str, int, str, str, str]:
    """Load and return environment variables for Hibachi API configuration.

    Loads environment variables from a .env file if present, otherwise falls
    back to system environment variables. Reads environment-specific variables
    based on the ENVIRONMENT variable (defaults to 'production').

    Returns:
        Tuple:
            - api_endpoint: The main API endpoint URL
            - data_api_endpoint: The data API endpoint URL
            - api_key: The API authentication key
            - account_id: The account ID as an integer
            - private_key: The private key for signing
            - public_key: The public key
            - dst_public_key: The destination public key for transfers

    """
    # Load the .env file if it exists
    env_file_path = Path(".env")
    if env_file_path.exists():
        log.info("Loading environment variables from .env file")
        load_dotenv()  # This loads variables from .env file (if it exists)
    else:
        log.info(".env file not found. Falling back to Bash Environment variables.")

    # Use a default environment if no environment is passed
    environment = os.getenv(
        "ENVIRONMENT", "production"
    ).lower()  # Default to 'production' if not passed

    # Print out the environment for debugging purposes
    log.info("Using %s environment", environment)

    # Dynamically load environment variables based on the environment
    api_endpoint = os.environ.get(
        f"HIBACHI_API_ENDPOINT_{environment.upper()}", "https://api.hibachi.xyz"
    )
    data_api_endpoint = os.environ.get(
        f"HIBACHI_DATA_API_ENDPOINT_{environment.upper()}",
        "https://data-api.hibachi.xyz",
    )
    api_key = os.environ.get(f"HIBACHI_API_KEY_{environment.upper()}", "your-api-key")
    try:
        account_id = int(
            os.environ.get(f"HIBACHI_ACCOUNT_ID_{environment.upper()}", "0")
        )
    except ValueError as e:
        raise ValidationError(
            f"Invalid HIBACHI_ACCOUNT_ID_{environment.upper()}: {e}"
        ) from e
    private_key = os.environ.get(
        f"HIBACHI_PRIVATE_KEY_{environment.upper()}", "your-private"
    )
    public_key = os.environ.get(
        f"HIBACHI_PUBLIC_KEY_{environment.upper()}", "your-public"
    )
    dst_public_key = os.environ.get(
        f"HIBACHI_TRANSFER_DST_ACCOUNT_PUBLIC_KEY_{environment.upper()}",
        "transfer-dst-account-public-key",
    )

    # Return the environment variables for use in the tests
    return (
        api_endpoint,
        data_api_endpoint,
        api_key,
        account_id,
        private_key,
        public_key,
        dst_public_key,
    )
