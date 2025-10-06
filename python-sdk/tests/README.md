# Tests Directory

This directory contains unit and integration tests for the Python SDK.

## Directory Structure

```
tests/
├── unit/              # Unit tests (deterministic and isolated to Python SDK)
│   ├── data/          # Test data files (JSON responses)
│   └── http/          # HTTP endpoint tests
│       ├── get/       # GET endpoint tests
│       ├── post/      # POST endpoint tests
│       ├── put/       # PUT endpoint tests
│       └── delete/    # DELETE endpoint tests
├── integration/       # Integration tests (requiring live Hibachi APIs)
└── README.md         # This file
```

## Unit Test Data Directory (`unit/data/`)

The `unit/data/` directory contains JSON files that serve as mock API responses for deterministic unit testing. Most tests are defined to run cases 1-1 with json files. For example `test.withdraw` is a test name; `test.withdraw.0.json` and `test.withdraw.1.json` and all other files of this form will be automatically read into the testing suite and run as independent tests.

### File Naming Convention

There are two types of data files:

#### 1. `response.*.json` Files
Single response objects used directly in tests:
- Format: `response.<operation>.<index>.json`
- Examples:
  - `response.exchange_info.0.json` - Exchange configuration
  - `response.capital_balance.0.json` - Capital balance response
  - `response.orderbook.0.json` - Orderbook snapshot
  - `response.trades.0.json` - Recent trades
  - `response.klines.0.json` - Candlestick/kline data
  - `response.open_interest.0.json` - Open interest data
  - `response.prices.0.json` - Price information
  - `response.stats.0.json` - Market statistics
  - `response.cancel_order.0.json` - Order cancellation response

Each file contains a single JSON response object with the expected structure from the API.

#### 2. `test.*.json` Files
Composite test files containing multiple related responses:
- Format: `test.<operation>.<index>.json`
- Structure: Top-level object with multiple named responses
- Examples:
  - `test.withdraw.0.json` - Contains both `response.exchange_info` and `response.withdraw`
  - `test.transfer.0.json` - Contains `response.exchange_info` and `response.transfer`
  - `test.place_limit_order.0.json` - Contains `response.exchange_info` and `response.order`
  - `test.place_market_order.0.json` - Contains `response.exchange_info` and `response.order`
  - `test.batch_orders.0.json` - Contains `response.exchange_info`, `input.orders`, and `response.batch`
  - `test.update_order.0.json` - Contains `response.exchange_info` and `response.update`
  - `test.cancel_all_orders.0.json` - Contains `response.exchange_info` and `response.cancel_all`

Example structure of a `test.*.json` file:
```json
{
    "response.exchange_info": {
        "feeConfig": { ... },
        "futureContracts": [ ... ],
        "serverTimestamp": 1728000000,
        "apiVersion": "v2.1.0"
    },
    "response.withdraw": {
        "coin": "USDT",
        "orderId": "12345",
        "estimatedCompletionTime": 1728000300
    }
}
```

### Additional Fields for Testing

All test data files include extra fields beyond the minimum required fields. These additional fields serve to:

1. **Test Deserialization Robustness** - Ensure the SDK can handle arbitrary additional fields from the API without breaking
2. **Future Compatibility** - Prepare for potential API additions

Extra fields are prefixed with `extra_field_` to make it explicitly clear they are test additions. For future compatibility tests this is **NOT** expected. E.g. the APIs will begin returning field "XYZ" -> add "XYZ" to existing or new test files, no need for `extra_field_` prefix.

## Test Philosophy

Unit tests follow a deterministic approach:
- **Predictable**: Same inputs always produce the same outputs
- **Isolated**: Tests don't depend on external services or network calls
- **Structured**: Always in the `tests/unit/` root

Integration tests have external dependencies:
- **Comprehensive**: Tests the entire roundtrip of SDK call -> API server -> call result
- **Maximally Stateless**: Best effort attempt to reset state on setup / teardown e.g. flatten positions, transfer balances
- **Structured**: Always in the `tests/integration/` root
