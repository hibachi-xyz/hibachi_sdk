![Hibachi Logo](./logo.png)

# Hibachi SDKs

Official SDKs for interacting with the [Hibachi](https://hibachi.xyz) cryptocurrency exchange API.

[Official API Documentation](https://api-doc.hibachi.xyz/)

## Available SDKs

| Language | Directory | Status | Installation |
|----------|-----------|--------|--------------|
| Python | [python/](./python/) | ✅ Stable | `pip install hibachi-xyz` |

## Features

All Hibachi SDKs provide access to:

- **REST API**: Market data, account management, trading operations
- **WebSocket API**: Real-time market data, account updates, and order management
- **Authentication**: Secure API key and private key signing
- **Type Safety**: Comprehensive type definitions for all API operations
- **Error Handling**: Detailed error hierarchy for robust error handling

## Getting Started

Each SDK has its own documentation and examples. Navigate to the specific SDK directory for detailed installation instructions, API reference, and usage examples:

- **[Python SDK Documentation](./python/README.md)**

## Quick Example (Python)

```python
from hibachi_xyz import HibachiApiClient

# Initialize client
hibachi = HibachiApiClient(
    api_key="your-api-key",
    account_id=123,
    private_key="your-private-key"
)

# Get account info
account_info = hibachi.get_account_info()
print(f"Balance: {account_info.balance}")

# Place a limit order
nonce, order_id = hibachi.place_limit_order(
    symbol="BTC/USDT-P",
    quantity=0.001,
    price=50000,
    side=Side.BUY,
    max_fees_percent=0.001
)
```

## API Coverage

### REST API
- Market Data: exchange info, prices, orderbook, klines, trades, stats, open interest
- Account Management: balance, positions, trade history, settlements
- Trading: place/update/cancel orders, batch operations
- Capital: deposits, withdrawals, transfers

### WebSocket API
- **Market WebSocket**: Real-time market data subscriptions (prices, trades, orderbook, etc.)
- **Trade WebSocket**: WebSocket-based order management
- **Account WebSocket**: Real-time account balance and position updates

## Repository Structure

```
hibachi_sdk/
├── README.md           # This file - multi-SDK overview
├── python/             # Python SDK
│   ├── README.md       # Python-specific documentation
│   ├── hibachi_xyz/    # SDK source code
│   ├── examples/       # Usage examples
│   ├── tests/          # Test suite
│   └── docs/           # Sphinx documentation
└── CODEOWNERS          # Repository ownership
```
## Authentication

Create a `.env` file and enter your values from hibachi. Please see [Authentication](https://api-doc.hibachi.xyz/#f1e55d83-5587-4c31-bff2-e972590a16ad) for more information. Before start running this SDK, you want to make 10 USDT deposit into the account you will be using below to ensure successful runs. 

```
ENVIRONMENT=production
HIBACHI_API_ENDPOINT_PRODUCTION="https://api.hibachi.xyz"
HIBACHI_DATA_API_ENDPOINT_PRODUCTION="https://data-api.hibachi.xyz"
HIBACHI_API_KEY_PRODUCTION="your_api_key_here"
HIBACHI_PRIVATE_KEY_PRODUCTION="your_private_key_here"
HIBACHI_PUBLIC_KEY_PRODUCTION="your_public_key_here"
HIBACHI_ACCOUNT_ID_PRODUCTION="your_account_id_here"
HIBACHI_TRANSFER_DST_ACCOUNT_PUBLIC_KEY_PRODUCTION="transfer_destination_account_public_key_here"
```

```python
# ensure .env has the values set.
from hibachi_xyz.env_setup import setup_environment
api_endpoint, data_api_endpoint, api_key, account_id, private_key, public_key, _ = setup_environment()

hibachi = HibachiApiClient(
        api_url= api_endpoint,
        data_api_url= data_api_endpoint,
        api_key = api_key,
        account_id = account_id,
        private_key = private_key,
    )

account_info = hibachi.get_account_info()
print(f"Account Balance: {account_info.balance}")
print(f"total Position Notional: {account_info.totalPositionNotional}")
```

Once you can see your account balance you can proceed with the below examples or specific documentation. Let us know if you need any help!

## Support & Contributing

- **Issues**: Report bugs or request features via [GitHub Issues](https://github.com/hibachi-xyz/yule-os/issues)
- **Documentation**: [Official API Docs](https://api-doc.hibachi.xyz/)
- **Community**: Join our community channels (links available on [hibachi.xyz](https://hibachi.xyz))

## License

See individual SDK directories for license information.
