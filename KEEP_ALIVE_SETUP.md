# 🚀 Keep Your Bot Alive 24/7 - Setup Guide

## 📊 **The Issue:**
Render's free tier automatically sleeps services after 15 minutes of inactivity. Your bot was running perfectly for 2 days but then received a termination signal - this is **normal behavior**, not an error.

## ✅ **Solutions to Keep Your Bot Running 24/7:**

### **Option 1: UptimeRobot (Recommended - FREE)**

1. **Go to [uptimerobot.com](https://uptimerobot.com)**
2. **Create a free account**
3. **Add a new monitor:**
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: EMA Crossover Bot
   - **URL**: `https://ema-cross.onrender.com/health`
   - **Monitoring Interval**: 5 minutes
   - **Monitor Timeout**: 30 seconds
4. **Save the monitor**

**Result**: Your bot will be pinged every 5 minutes, keeping it awake 24/7!

### **Option 2: Pingdom (Alternative - FREE)**

1. **Go to [pingdom.com](https://pingdom.com)**
2. **Create a free account**
3. **Add a new check:**
   - **Check Type**: HTTP
   - **Name**: EMA Crossover Bot
   - **URL**: `https://ema-cross.onrender.com/health`
   - **Check Interval**: 5 minutes
4. **Save the check**

### **Option 3: Multiple Free Services**

Deploy the same bot on multiple platforms:
- **Render** (current)
- **Railway** (free tier)
- **Fly.io** (free tier)
- **Heroku** (free tier)

### **Option 4: Upgrade to Render Paid Plan**

- **Starter Plan**: $7/month
- **No auto-sleep**
- **Always running**
- **Better performance**

## 🛠️ **Manual Wake-Up (Emergency)**

If your bot goes to sleep, you can wake it up manually:

```bash
# Wake up the bot
curl https://ema-cross.onrender.com/wake-up

# Check status
curl https://ema-cross.onrender.com/status
```

## 📱 **New Endpoints Added:**

- **`/wake-up`**: Manually wake up the bot and trigger analysis
- **`/configure`**: Configure bot settings
- **Enhanced keep-alive**: Now pings external services to generate traffic

## 🎯 **Recommended Setup:**

1. **Set up UptimeRobot** (5-minute intervals)
2. **Test the `/wake-up` endpoint** manually
3. **Monitor the logs** for keep-alive success
4. **Consider upgrading** to paid plan for 100% uptime

## 📊 **Expected Behavior:**

- **With UptimeRobot**: Bot stays awake 24/7
- **Without external ping**: Bot sleeps after 15 minutes of inactivity
- **Wake-up time**: 10-30 seconds when pinged

Your bot is working perfectly - it just needs external traffic to stay awake on Render's free tier! 🚀
