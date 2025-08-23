# EMA Crossover Alert Bot 🤖📈

A sophisticated automated trading signal generator that monitors cryptocurrency and forex markets for EMA crossover signals with multi-confirmation indicators.

## 🚀 Features

- **Multi-Confirmation System**: EMA crossover + Break of Structure (BOS) + Change of Character (CHOCH)
- **Dual Notification Channels**: iOS Shortcuts + Telegram Bot
- **Smart Cooldown Management**: Prevents signal spam with configurable cooldown periods
- **Real-time Market Analysis**: 15-minute intervals for crypto and forex pairs
- **Cloud-Optimized**: Built for Render deployment with keep-alive functionality
- **Comprehensive Logging**: Detailed logging for monitoring and debugging

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Fetcher  │    │   Technical      │    │   Alert Manager │
│                 │    │   Indicators     │    │                 │
│ • Binance API   │───▶│ • EMA Crossover  │───▶│ • Signal       │
│ • Yahoo Finance │    │ • BOS Detection  │    │   Processing   │
│ • Rate Limiting │    │ • CHOCH Analysis │    │ • Cooldown     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Notification   │    │   Flask Web     │
                       │   Manager        │    │   Server        │
                       │                 │    │                 │
                       │ • iOS Shortcuts │    │ • Health Checks │
                       │ • Telegram Bot  │    │ • Status API    │
                       │ • Fallback      │    │ • Keep-alive    │
                       └──────────────────┘    └─────────────────┘
```

## 📊 Trading Strategy

### Core Strategy
- **Fast EMA**: 9-period (quick signal detection)
- **Slow EMA**: 20-period (noise filtering)
- **Timeframe**: 15-minute candles
- **Signal Types**: Base signals (2/5 confidence) and Confirmed signals (3-5/5 confidence)

### Confirmation Indicators
1. **Break of Structure (BOS)**
   - Lookback: 5 periods
   - Volume threshold: 1.5x average volume
   - Purpose: Trend continuation validation

2. **Change of Character (CHOCH)**
   - Lookback: 10 periods
   - Volume threshold: 1.5x average volume
   - Purpose: Trend reversal confirmation

### Signal Filtering
- Minimum signal strength: 0.7 (70%)
- Base signal cooldown: 30 minutes
- Confirmed signal cooldown: 1 hour
- Volume confirmation required for BOS/CHOCH

## 🛠️ Installation

### Prerequisites
- Python 3.11+
- Binance API credentials (optional, for crypto data)
- Telegram Bot token and chat ID
- iOS Shortcuts webhook URL

### Local Setup
```bash
# Clone repository
git clone <repository-url>
cd ema-crossover-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export IOS_WEBHOOK_URL="your_ios_webhook_url"
export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
export TELEGRAM_CHAT_ID="your_telegram_chat_id"
export BINANCE_API_KEY="your_binance_api_key"
export BINANCE_SECRET_KEY="your_binance_secret_key"

# Run the bot
python main_bot_cloud.py
```

### Docker Setup
```bash
# Build Docker image
docker build -t ema-crossover-bot .

# Run container
docker run -p 8080:8080 \
  -e IOS_WEBHOOK_URL="your_ios_webhook_url" \
  -e TELEGRAM_BOT_TOKEN="your_telegram_bot_token" \
  -e TELEGRAM_CHAT_ID="your_telegram_chat_id" \
  ema-crossover-bot
```

## ☁️ Render Deployment

### Quick Deploy
1. Fork this repository
2. Connect to Render
3. Create new Web Service
4. Set environment variables in Render dashboard
5. Deploy!

### Environment Variables
Set these in your Render dashboard:

| Variable | Description | Required |
|----------|-------------|----------|
| `IOS_WEBHOOK_URL` | iOS Shortcuts webhook endpoint | Yes |
| `TELEGRAM_BOT_TOKEN` | Telegram bot authentication token | Yes |
| `TELEGRAM_CHAT_ID` | Target chat ID for notifications | Yes |
| `BINANCE_API_KEY` | Binance API key for crypto data | No |
| `BINANCE_SECRET_KEY` | Binance API secret | No |
| `PORT` | Flask server port (default: 8080) | No |
| `LOG_LEVEL` | Logging level (default: INFO) | No |

## 🔧 Configuration

### Market Pairs
Edit `config.py` to modify trading pairs:

```python
# Cryptocurrencies
CRYPTO_PAIRS = [
    "BTCUSDT",
    "ETHUSDT", 
    "SOLUSDT",
    "XRPUSDT"
]

# Forex pairs
FOREX_PAIRS = [
    "EURUSD=X",
    "USDJPY=X",
    "GBPUSD=X"
]
```

### Technical Parameters
```python
# EMA Configuration
FAST_EMA = 9
SLOW_EMA = 20
TIMEFRAME = "15m"

# Confirmation Settings
BOS_LOOKBACK = 5
CHOCH_LOOKBACK = 10
VOLUME_THRESHOLD = 1.5
MIN_SIGNAL_STRENGTH = 0.7

# Cooldown Periods
BASE_SIGNAL_COOLDOWN = 30  # minutes
CONFIRMED_SIGNAL_COOLDOWN = 60  # minutes
```

## 📱 Notification Setup

### iOS Shortcuts
1. Create new Shortcut in iOS Shortcuts app
2. Add "Get Contents of URL" action
3. Set URL to your bot's webhook endpoint
4. Add notification action
5. Get webhook URL from Shortcuts

### Telegram Bot
1. Message @BotFather on Telegram
2. Create new bot with `/newbot`
3. Get bot token
4. Get chat ID by messaging bot and checking: `https://api.telegram.org/bot<TOKEN>/getUpdates`

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Bot information and available endpoints |
| `/health` | GET | Health check and keep-alive |
| `/status` | GET | Comprehensive bot status and market summary |
| `/test-notification` | GET | Test notification system |
| `/test-ios` | GET | Test iOS Shortcuts specifically |
| `/notification-status` | GET | Notification system health |
| `/clear-cooldown/<symbol>` | GET | Clear cooldown for testing |

### Example API Usage
```bash
# Health check
curl https://your-bot-url.onrender.com/health

# Bot status
curl https://your-bot-url.onrender.com/status

# Test notifications
curl https://your-bot-url.onrender.com/test-notification
```

## 📊 Monitoring & Debugging

### Logs
- Application logs: `bot.log`
- Render logs: Available in Render dashboard
- Log level: Configurable via `LOG_LEVEL` environment variable

### Health Monitoring
- **Keep-alive ping**: Every 2 minutes to prevent Render sleep
- **Health endpoint**: `/health` for external monitoring
- **Status endpoint**: `/status` for comprehensive bot status

### Common Issues
1. **Bot going to sleep**: Check keep-alive ping frequency
2. **Notifications not working**: Verify environment variables and test endpoints
3. **Data fetching errors**: Check API rate limits and credentials

## 🧪 Testing

### Test Notifications
```bash
# Test all notification channels
curl https://your-bot-url.onrender.com/test-notification

# Test iOS Shortcuts specifically
curl https://your-bot-url.onrender.com/test-ios

# Check notification system status
curl https://your-bot-url.onrender.com/notification-status
```

### Test Signal Processing
```bash
# Clear cooldown for testing
curl https://your-bot-url.onrender.com/clear-cooldown/BTCUSDT
```

## 🔒 Security Considerations

- **API Keys**: Never commit API keys to version control
- **Environment Variables**: Use Render's secure environment variable system
- **Rate Limiting**: Built-in rate limiting for API calls
- **Error Handling**: Comprehensive error handling without exposing sensitive data

## 📈 Performance Characteristics

- **Analysis Frequency**: Every 15 minutes
- **Keep-alive Frequency**: Every 2 minutes
- **Data Fetch Timeout**: 10 seconds
- **Memory Management**: Alert history limited to last 1000 entries
- **Concurrent Operations**: Asynchronous notification sending

## 🚀 Future Enhancements

### Strategy Expansions
- [ ] RSI, MACD, and other momentum indicators
- [ ] Multi-timeframe analysis
- [ ] Support and resistance level detection
- [ ] Adaptive parameter optimization

### Notification Enhancements
- [ ] Discord and Slack integration
- [ ] Notification scheduling and quiet hours
- [ ] Notification acknowledgment and tracking
- [ ] Delivery analytics and reports

### Data Enhancements
- [ ] Real-time streaming data feeds
- [ ] Data quality scoring and validation
- [ ] Alternative data sources for confirmation
- [ ] Data visualization and charting capabilities

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This bot is for educational and informational purposes only. It does not constitute financial advice. Trading cryptocurrencies and forex involves substantial risk of loss. Always do your own research and consider consulting with a financial advisor before making trading decisions.

## 📞 Support

For issues and questions:
1. Check the troubleshooting guide in the documentation
2. Review the logs for error details
3. Test the notification endpoints
4. Open an issue on GitHub

---

**Happy Trading! 🚀📊**

