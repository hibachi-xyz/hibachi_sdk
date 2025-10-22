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

## Authentication

All SDKs require API credentials from Hibachi:

1. Create an account at [hibachi.xyz](https://hibachi.xyz)
2. Generate API keys from your account settings
3. Use the API key, account ID, and private key in your SDK configuration

For detailed authentication setup, see the [Authentication Documentation](https://api-doc.hibachi.xyz/#f1e55d83-5587-4c31-bff2-e972590a16ad).

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

## Support & Contributing

- **Issues**: Report bugs or request features via [GitHub Issues](https://github.com/hibachi-xyz/yule-os/issues)
- **Documentation**: [Official API Docs](https://api-doc.hibachi.xyz/)
- **Community**: Join our community channels (links available on [hibachi.xyz](https://hibachi.xyz))

## License

See individual SDK directories for license information.
