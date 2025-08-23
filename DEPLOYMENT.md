# 🚀 Deployment Guide - EMA Crossover Alert Bot

This guide will walk you through deploying your EMA Crossover Alert Bot to Render cloud platform.

## 📋 Prerequisites

Before deployment, ensure you have:

- [ ] GitHub account with this repository forked/cloned
- [ ] Render account (free tier available)
- [ ] Telegram Bot token and chat ID
- [ ] iOS Shortcuts webhook URL
- [ ] Binance API credentials (optional)

## 🔧 Step 1: Prepare Your Repository

### 1.1 Fork/Clone Repository
```bash
# If you haven't already, fork this repository to your GitHub account
# Then clone your fork locally
git clone https://github.com/YOUR_USERNAME/ema-crossover-bot.git
cd ema-crossover-bot
```

### 1.2 Verify File Structure
Ensure you have all required files:
```
ema-crossover-bot/
├── main_bot_cloud.py          # Main bot orchestration
├── data_fetcher.py            # Market data fetching
├── technical_indicators.py    # Technical analysis
├── alert_manager.py           # Signal processing
├── notifications/             # Notification system
│   ├── __init__.py
│   ├── ios_shortcuts.py
│   ├── telegram_bot.py
│   └── notification_manager.py
├── config.py                  # Configuration
├── requirements.txt           # Dependencies
├── Dockerfile                 # Container configuration
├── render.yaml               # Render deployment config
├── README.md                 # Documentation
└── test_bot.py               # Testing script
```

## 🌐 Step 2: Set Up Telegram Bot

### 2.1 Create Telegram Bot
1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow prompts to create your bot
4. Save the bot token (you'll need this)

### 2.2 Get Chat ID
1. Send a message to your bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Look for the `chat` object and note the `id` field
4. This is your `TELEGRAM_CHAT_ID`

## 📱 Step 3: Set Up iOS Shortcuts

### 3.1 Create Shortcut
1. Open iOS Shortcuts app
2. Create new shortcut
3. Add "Get Contents of URL" action
4. Set URL to: `https://your-bot-url.onrender.com/test-ios`
5. Add "Show Notification" action
6. Save shortcut

### 3.2 Get Webhook URL
1. In Shortcuts, tap the shortcut name
2. Tap "Share" button
3. Select "Copy Link"
4. This is your `IOS_WEBHOOK_URL`

## ☁️ Step 4: Deploy to Render

### 4.1 Connect Repository
1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" → "Web Service"
3. Connect your GitHub account
4. Select your forked repository

### 4.2 Configure Service
Fill in the service configuration:

- **Name**: `ema-crossover-bot` (or your preferred name)
- **Environment**: `Python 3`
- **Region**: Choose closest to you
- **Branch**: `main`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 main_bot_cloud:app`

### 4.3 Set Environment Variables
Add these environment variables in Render:

| Variable | Value | Required |
|----------|-------|----------|
| `IOS_WEBHOOK_URL` | Your iOS Shortcuts webhook URL | ✅ Yes |
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | ✅ Yes |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID | ✅ Yes |
| `BINANCE_API_KEY` | Your Binance API key | ❌ No |
| `BINANCE_SECRET_KEY` | Your Binance API secret | ❌ No |
| `PORT` | `8080` | ❌ No |
| `LOG_LEVEL` | `INFO` | ❌ No |
| `DEBUG` | `false` | ❌ No |

### 4.4 Deploy
1. Click "Create Web Service"
2. Wait for build to complete (usually 2-5 minutes)
3. Note your service URL (e.g., `https://ema-crossover-bot.onrender.com`)

## 🧪 Step 5: Test Deployment

### 5.1 Health Check
```bash
curl https://your-bot-url.onrender.com/health
```
Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "uptime_seconds": 120,
  "is_running": true
}
```

### 5.2 Test Notifications
```bash
# Test all notification channels
curl https://your-bot-url.onrender.com/test-notification

# Test iOS Shortcuts specifically
curl https://your-bot-url.onrender.com/test-ios

# Check notification system status
curl https://your-bot-url.onrender.com/notification-status
```

### 5.3 Check Bot Status
```bash
curl https://your-bot-url.onrender.com/status
```

## 🔍 Step 6: Monitor and Debug

### 6.1 View Logs
1. In Render dashboard, go to your service
2. Click "Logs" tab
3. Monitor for errors or issues

### 6.2 Common Issues and Solutions

#### Bot Going to Sleep
**Problem**: Bot stops responding after 15 minutes
**Solution**: 
- Verify keep-alive ping is running every 2 minutes
- Check `/health` endpoint accessibility
- Ensure webhook URL is correct

#### Notifications Not Working
**Problem**: No notifications received
**Solution**:
- Check environment variables in Render dashboard
- Test notification endpoints
- Verify webhook URLs and tokens
- Check notification system status

#### Data Fetching Errors
**Problem**: Market analysis failing
**Solution**:
- Check API rate limits
- Verify symbol formats
- Review error logs for specific failures
- Test individual data sources

### 6.3 Performance Monitoring
Monitor these metrics:
- **Uptime**: Should be 99%+ on Render free tier
- **Response Time**: Health checks should respond in <5 seconds
- **Error Rate**: Should be minimal
- **Signal Generation**: Check if signals are being generated

## 🔄 Step 7: Maintenance and Updates

### 7.1 Automatic Deployments
- Render automatically redeploys when you push to main branch
- Monitor build logs for any issues
- Test endpoints after each deployment

### 7.2 Scaling Considerations
- **Free Tier Limits**: 750 hours/month, auto-sleep after 15 minutes
- **Upgrade Path**: Consider paid plans for production use
- **Monitoring**: Set up external monitoring for critical deployments

### 7.3 Backup and Recovery
- Keep local copy of configuration
- Document environment variables
- Test recovery procedures

## 📊 Step 8: Production Readiness

### 8.1 Security Checklist
- [ ] No API keys in code
- [ ] Environment variables secured
- [ ] HTTPS enabled (automatic on Render)
- [ ] Rate limiting implemented
- [ ] Error handling without data exposure

### 8.2 Performance Checklist
- [ ] Health checks responding <5 seconds
- [ ] Keep-alive ping working
- [ ] Market analysis completing in reasonable time
- [ ] Notifications delivering reliably
- [ ] Memory usage stable

### 8.3 Monitoring Checklist
- [ ] Logs accessible and readable
- [ ] Error tracking implemented
- [ ] Performance metrics available
- [ ] Alert system working
- [ ] Backup procedures documented

## 🆘 Troubleshooting Quick Reference

| Issue | Quick Fix | Detailed Solution |
|-------|-----------|-------------------|
| Bot not responding | Check `/health` endpoint | Verify keep-alive system |
| No notifications | Test `/test-notification` | Check environment variables |
| Build failing | Check requirements.txt | Verify Python version compatibility |
| Service sleeping | Increase keep-alive frequency | Check Render free tier limits |
| Data errors | Verify API credentials | Check rate limiting |

## 📞 Support Resources

- **Render Documentation**: [docs.render.com](https://docs.render.com/)
- **Telegram Bot API**: [core.telegram.org/bots](https://core.telegram.org/bots)
- **iOS Shortcuts**: [support.apple.com/shortcuts](https://support.apple.com/shortcuts)
- **GitHub Issues**: Use repository issues for bot-specific problems

## 🎯 Next Steps

After successful deployment:

1. **Monitor Performance**: Watch logs and metrics
2. **Test Signals**: Wait for first trading signals
3. **Optimize Parameters**: Adjust based on performance
4. **Add Markets**: Expand to more trading pairs
5. **Enhance Features**: Implement additional indicators

---

**🎉 Congratulations! Your EMA Crossover Alert Bot is now deployed and running in the cloud!**

Remember to:
- Keep your API keys secure
- Monitor the bot regularly
- Test notifications periodically
- Update dependencies as needed

Happy trading! 🚀📈

