# 🚀 EMA Crossover Alert Bot

A **simple, reliable, and production-ready** trading bot that monitors cryptocurrency and forex markets for EMA crossover signals and sends real-time alerts to iOS Shortcuts and Telegram.

## ✨ **What This Bot Does**

- 🔄 **Monitors markets every 15 minutes** for trading signals
- ⚡ **Sends instant alerts** to iOS Shortcuts and Telegram
- 🚨 **Detects bullish/bearish signals** with actionable insights
- 💤 **Stays awake 24/7** with automatic keep-alive pings
- 🛡️ **Prevents signal spam** with smart cooldown system

## 🎯 **Key Features**

### **Market Monitoring**
- **Crypto**: BTC, ETH, SOL, XRP (USD pairs)
- **Forex**: EUR/USD, USD/JPY, GBP/USD
- **Analysis**: Every 15 minutes
- **Signals**: Bullish/Bearish EMA crossovers

### **Data Sources** (Global Access)
- **Alpha Vantage**: Primary data source (free tier available)
- **Yahoo Finance**: Reliable fallback for all assets
- **CoinGecko**: Crypto-specific fallback
- **Simulated Data**: Last resort to keep bot running

### **Notifications**
- **iOS Shortcuts**: Direct webhook integration
- **Telegram**: Rich HTML-formatted messages
- **Real-time**: Instant signal delivery
- **Smart**: Cooldown prevents spam

### **Reliability**
- **Keep-alive**: Pings every minute to stay awake
- **Auto-restart**: Handles crashes gracefully
- **Production-ready**: Optimized for Render deployment
- **Simple**: Minimal dependencies, maximum reliability

## 🚀 **Quick Start**

### **1. Deploy to Render**
```bash
# Connect your GitHub repo to Render
# Set environment variables
# Deploy automatically
```

### **2. Configure Notifications**
- **iOS Shortcuts**: Set webhook URL
- **Telegram**: Add bot token and chat ID
- **Test**: Use `/test-notification` endpoint

### **3. Monitor Markets**
- **Status**: Check `/status` endpoint
- **Health**: Monitor `/health` endpoint
- **Logs**: Watch Render dashboard

## 🔧 **API Endpoints**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Bot information and status |
| `/health` | GET | Health check and monitoring |
| `/ping` | GET | Simple keep-alive ping |
| `/status` | GET | Comprehensive bot status |
| `/initialize` | GET | Manual bot initialization |
| `/test-notification` | GET | Test notification system |
| `/test-analysis` | GET | Test market analysis |
| `/webhook/ios` | GET/POST | iOS Shortcuts webhook |

## 🌐 **Environment Variables**

```bash
# Required
IOS_WEBHOOK_URL=your_ios_webhook_url
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Optional
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key
PORT=8000
DEBUG=false
LOG_LEVEL=INFO
```

## 📱 **iOS Shortcuts Setup**

1. **Create shortcut** with "Get Contents of URL"
2. **Set URL**: `https://your-bot.onrender.com/webhook/ios`
3. **Method**: POST
4. **Headers**: `Content-Type: application/json`
5. **Body**: JSON with your message

## 📊 **How It Works**

1. **Bot starts** and initializes background tasks
2. **Every minute**: Keep-alive ping prevents sleep
3. **Every 15 minutes**: Market analysis runs
4. **Data fetching**: Tries multiple sources with fallbacks
5. **When signal detected**: Notification sent immediately
6. **Cooldown applied**: Prevents duplicate alerts

## 🎉 **Benefits**

- ✅ **Simple**: Single file, easy to understand
- ✅ **Reliable**: Robust error handling and recovery
- ✅ **Global**: Works from any location (no geo-restrictions)
- ✅ **Fast**: Minimal dependencies, quick startup
- ✅ **Robust**: Multiple data source fallbacks

## 🔍 **Monitoring**

- **Health checks**: Automatic monitoring
- **Logs**: Real-time debugging
- **Status**: Live bot information
- **Metrics**: Analysis counts and uptime

## 🚨 **Troubleshooting**

### **Bot not responding**
- Check `/health` endpoint
- Verify background tasks are running
- Check Render logs for errors

### **Notifications not working**
- Test with `/test-notification`
- Verify environment variables
- Check iOS Shortcuts configuration

### **Bot going to sleep**
- Verify keep-alive is working
- Check `/ping` endpoint
- Monitor Render activity

## 📄 **License**

MIT License - Feel free to use and modify!

---

**Happy Trading! 🎯📈**

*This bot is designed to be simple, reliable, and production-ready. No complex dependencies, no unnecessary features - just solid trading signal detection and delivery.*

