# Hibachi Algorithmic Trading Bot - Operation Instructions

## Prerequisites
- Python 3.9+ installed
- PostgreSQL or SQLite database (for Optuna storage)
- Telegram Bot Token and Chat ID (for notifications)
- Hibachi DEX API credentials

## Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Database Setup
Create a database for Optuna optimization history:

**For SQLite (Development):**
```bash
# No setup required, database file will be created automatically
```

**For PostgreSQL (Production):**
```bash
createdb hibachi_optimization
```

### 3. Configuration
Create a `.env` file in the project root with the following variables:

```env
# Hibachi DEX API
HIBACHI_API_KEY=your_api_key
HIBACHI_API_SECRET=your_api_secret
HIBACHI_BASE_URL=https://api.hibachi.dex

# Database (Optuna)
OPTUNA_DB_URL=sqlite:///optuna.db
# For PostgreSQL: postgresql://user:password@localhost:5432/hibachi_optimization

# Telegram Notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Trading Configuration
TOTAL_CAPITAL=10000
MAX_POSITIONS=3
POSITION_ALLOCATION=0.15

# Assets to Trade
TRADING_PAIRS=BTC/USDT-P,ETH/USDT-P,SOL/USDT-P
```

## Operation Modes

### Mode 1: Optimization (Walk-Forward + OOS Validation)
Run parameter optimization for a specific asset:

```bash
python main.py --mode optimize --asset BTC-USDT-P
```

Options:
- `--asset`: Asset to optimize (BTC-USDT-P, ETH-USDT-P, SOL-USDT-P)
- `--n-trials`: Number of Optuna trials (default: 100)
- `--db-study-name`: Custom study name (default: strategy_opt_{asset})

### Mode 2: Backtesting
Run vectorized backtest with optimized parameters:

```bash
python main.py --mode backtest --asset BTC-USDT-P
```

Options:
- `--asset`: Asset to backtest
- `--params-file`: Path to optimized parameters JSON (optional)
- `--oos-ratio`: Out-of-sample ratio (default: 0.2)

### Mode 3: Live Trading
Start the live trading bot:

```bash
python main.py --mode live
```

Options:
- `--assets`: Comma-separated list of assets (default: all configured)
- `--dry-run`: Run without executing real orders (paper trading)

### Mode 4: Market Data Fetch
Fetch and store historical kline data:

```bash
python main.py --mode fetch-data --asset BTC-USDT-P --timeframe 1h --limit 1000
```

## Daily Operations

### Start the Bot
```bash
python main.py --mode live
```

### Check System Health
The bot sends heartbeat messages to Telegram every 30 minutes. Check your Telegram channel for status updates.

### View Optimization Results
```bash
python main.py --mode show-results --asset BTC-USDT-P
```

### Generate Daily Report
```bash
python main.py --mode daily-report --date 2024-01-15
```

## Monitoring

### Telegram Notifications
You will receive:
- Trade execution confirmations
- Position open/close alerts
- Daily P&L summaries
- Drawdown warnings
- Market regime shift alerts (ADX changes)
- System heartbeat every 30 minutes

### Log Files
Check `logs/` directory for detailed logs:
- `hibachi_bot.log`: Main application logs
- `orders.log`: Order execution logs
- `optimization.log`: Optuna optimization logs

## Risk Management Overrides

The bot enforces these rules automatically:
- Maximum 3 open positions across all assets
- 15% capital allocation per position
- 55% free margin buffer maintained
- ATR-based dynamic position sizing
- Stop-loss at local pivot points (LTF)

### Manual Intervention
To manually close all positions:
```bash
python main.py --mode emergency-close
```

To pause trading (keeps positions open):
```bash
python main.py --mode pause
```

To resume trading:
```bash
python main.py --mode resume
```

## Troubleshooting

### Common Issues

**Database Connection Error:**
```bash
# Check OPTUNA_DB_URL in .env
# For PostgreSQL, ensure service is running
```

**API Authentication Failed:**
```bash
# Verify HIBACHI_API_KEY and HIBACHI_API_SECRET
# Check API permissions on Hibachi DEX dashboard
```

**Telegram Notifications Not Working:**
```bash
# Verify TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
# Test with: curl "https://api.telegram.org/bot<TOKEN>/getUpdates"
```

**Optimization Taking Too Long:**
```bash
# Reduce --n-trials parameter
# Use SQLite instead of PostgreSQL for faster local optimization
```

## Best Practices

1. **Always run optimization before deploying** to ensure parameters are valid for current market regime
2. **Monitor OOS Sharpe ratio** - deployment denied if OOS Sharpe < 70% of In-Sample Sharpe
3. **Review daily reports** to track performance and drawdown
4. **Keep 55% free margin** - never override position limits
5. **Use dry-run mode** when testing new configurations
6. **Backup optimization database** regularly

## Support

For issues related to:
- Hibachi DEX API: Contact Hibachi support
- Bot functionality: Check logs and GitHub issues
- Optimization strategies: Review SDD Section 3 & 4
