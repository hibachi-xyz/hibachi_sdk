import logging
import os
from pathlib import Path

from dotenv import load_dotenv

log = logging.getLogger(__name__)


def setup_environment():
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
    account_id = int(
        os.environ.get(f"HIBACHI_ACCOUNT_ID_{environment.upper()}", "your-account-id")
    )
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
