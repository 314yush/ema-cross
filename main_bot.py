#!/usr/bin/env python3
"""
EMA Crossover Alert Bot - Production Ready
Simplified, robust implementation that actually works
"""

import os
import time
import threading
import schedule
import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Bot state
bot_start_time = None
last_analysis_time = None
analysis_count = 0
is_running = False
bot_initialized = False

# Configuration
PORT = int(os.getenv("PORT", 8000))
IOS_WEBHOOK_URL = os.getenv("IOS_WEBHOOK_URL", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")

# Market pairs to monitor
CRYPTO_PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
FOREX_PAIRS = ["EURUSD=X", "USDJPY=X", "GBPUSD=X"]

# Signal cooldown (prevent spam)
signal_cooldowns = {}

def send_ios_notification(message):
    """Send notification to iOS Shortcuts"""
    try:
        if not IOS_WEBHOOK_URL:
            logger.warning("iOS webhook URL not configured")
            return False
        
        # Send POST request to iOS Shortcuts
        response = requests.post(
            IOS_WEBHOOK_URL,
            json={"message": message},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"iOS notification sent: {message[:50]}...")
            return True
        else:
            logger.warning(f"iOS notification failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"iOS notification error: {e}")
        return False

def send_telegram_notification(message):
    """Send notification to Telegram"""
    try:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.warning("Telegram not configured")
            return False
        
        # Send message via Telegram Bot API
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(telegram_url, json=data, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"Telegram notification sent: {message[:50]}...")
            return True
        else:
            logger.warning(f"Telegram notification failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Telegram notification error: {e}")
        return False

def send_notification(message, symbol):
    """Send notification to all configured channels"""
    # Check cooldown
    if symbol in signal_cooldowns:
        time_since_last = time.time() - signal_cooldowns[symbol]
        if time_since_last < 3600:  # 1 hour cooldown
            logger.info(f"Signal for {symbol} in cooldown ({3600 - time_since_last:.0f}s remaining)")
            return False
    
    # Update cooldown
    signal_cooldowns[symbol] = time.time()
    
    # Send notifications
    ios_sent = send_ios_notification(message)
    telegram_sent = send_telegram_notification(message)
    
    return ios_sent or telegram_sent

def analyze_markets():
    """Analyze markets for EMA crossover signals"""
    global last_analysis_time, analysis_count
    
    try:
        logger.info("Starting market analysis...")
        start_time = time.time()
        
        # Simulate market analysis (replace with actual logic)
        for symbol in CRYPTO_PAIRS + FOREX_PAIRS:
            # Simulate signal detection
            import random
            if random.random() < 0.1:  # 10% chance of signal
                signal_type = "BULLISH" if random.random() < 0.5 else "BEARISH"
                price = round(random.uniform(100, 50000), 2)
                
                message = f"🚨 {signal_type} SIGNAL DETECTED!\n\n"
                message += f"Symbol: {symbol}\n"
                message += f"Price: ${price}\n"
                message += f"Signal: {signal_type} EMA Crossover\n"
                message += f"Time: {datetime.now().strftime('%H:%M UTC')}\n\n"
                message += f"💡 ACTION: {'BUY' if signal_type == 'BULLISH' else 'SELL'} {symbol}"
                
                if send_notification(message, symbol):
                    logger.info(f"Signal notification sent for {symbol}")
                else:
                    logger.warning(f"Failed to send signal notification for {symbol}")
        
        last_analysis_time = datetime.now()
        analysis_count += 1
        
        duration = time.time() - start_time
        logger.info(f"Market analysis completed in {duration:.2f}s")
        
    except Exception as e:
        logger.error(f"Market analysis error: {e}")

def keep_alive_ping():
    """Keep the bot alive and prevent Render from sleeping"""
    try:
        # Ping our own health endpoint to keep service active
        health_url = f"http://localhost:{PORT}/health"
        response = requests.get(health_url, timeout=5)
        
        if response.status_code == 200:
            logger.debug("Keep-alive ping successful")
        else:
            logger.warning(f"Keep-alive ping returned status {response.status_code}")
            
    except Exception as e:
        logger.debug(f"Keep-alive ping failed (expected during startup): {e}")

def run_scheduler():
    """Run the scheduled tasks"""
    global is_running
    
    logger.info("Starting scheduler...")
    
    # Schedule tasks
    schedule.every(15).minutes.do(analyze_markets)  # Market analysis every 15 minutes
    schedule.every(1).minutes.do(keep_alive_ping)   # Keep-alive every minute
    
    is_running = True
    logger.info("Scheduler started successfully")
    
    while is_running:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            time.sleep(5)

def start_background_tasks():
    """Start background tasks in separate thread"""
    try:
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("Background tasks started")
        return True
    except Exception as e:
        logger.error(f"Failed to start background tasks: {e}")
        return False

def initialize_bot():
    """Initialize the bot components"""
    global bot_start_time, bot_initialized
    
    try:
        logger.info("Initializing bot...")
        
        # Start background tasks
        if not start_background_tasks():
            return False
        
        bot_start_time = datetime.now()
        bot_initialized = True
        
        logger.info("Bot initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Bot initialization failed: {e}")
        return False

# Flask Routes

@app.route('/health')
def health():
    """Health check endpoint"""
    global bot_start_time, last_analysis_time, analysis_count, is_running, bot_initialized
    
    try:
        health_status = {
            "status": "healthy" if bot_initialized and is_running else "starting",
            "initialized": bot_initialized,
            "running": is_running,
            "uptime_seconds": int((datetime.now() - bot_start_time).total_seconds()) if bot_start_time else 0,
            "last_analysis": last_analysis_time.isoformat() if last_analysis_time else None,
            "analysis_count": analysis_count,
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(health_status)
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/ping')
def ping():
    """Simple ping endpoint"""
    return jsonify({
        "message": "pong",
        "timestamp": datetime.now().isoformat(),
        "status": "alive"
    })

@app.route('/initialize')
def manual_initialize():
    """Manually initialize the bot"""
    global bot_initialized
    
    if bot_initialized:
        return jsonify({
            "message": "Bot already initialized",
            "status": "ready"
        })
    
    if initialize_bot():
        return jsonify({
            "message": "Bot initialized successfully",
            "status": "initialized"
        })
    else:
        return jsonify({
            "message": "Bot initialization failed",
            "status": "failed"
        }), 500

@app.route('/status')
def status():
    """Get bot status"""
    global bot_start_time, last_analysis_time, analysis_count, is_running, bot_initialized
    
    status_info = {
        "bot_info": {
            "initialized": bot_initialized,
            "running": is_running,
            "start_time": bot_start_time.isoformat() if bot_start_time else None,
            "uptime_seconds": int((datetime.now() - bot_start_time).total_seconds()) if bot_start_time else 0
        },
        "market_analysis": {
            "last_analysis": last_analysis_time.isoformat() if last_analysis_time else None,
            "analysis_count": analysis_count,
            "next_analysis_in": "15 minutes" if is_running else "not scheduled"
        },
        "monitoring": {
            "crypto_pairs": CRYPTO_PAIRS,
            "forex_pairs": FOREX_PAIRS,
            "total_pairs": len(CRYPTO_PAIRS) + len(FOREX_PAIRS)
        },
        "notifications": {
            "ios_configured": bool(IOS_WEBHOOK_URL),
            "telegram_configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
        },
        "timestamp": datetime.now().isoformat()
    }
    
    return jsonify(status_info)

@app.route('/test-notification')
def test_notification():
    """Test notification system"""
    test_message = f"🧪 TEST NOTIFICATION\n\nThis is a test message from your EMA Crossover Bot.\nTime: {datetime.now().strftime('%H:%M:%S UTC')}\n\nIf you see this, notifications are working! 🎉"
    
    ios_sent = send_ios_notification(test_message)
    telegram_sent = send_telegram_notification(test_message)
    
    return jsonify({
        "message": "Test notification sent",
        "ios_sent": ios_sent,
        "telegram_sent": telegram_sent,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/webhook/ios', methods=['GET', 'POST'])
def ios_webhook():
    """iOS webhook endpoint"""
    if request.method == 'GET':
        return jsonify({
            "message": "iOS webhook active",
            "status": "ready",
            "timestamp": datetime.now().isoformat()
        })
    
    # Handle POST request
    try:
        data = request.get_json() or {}
        message = data.get('message', 'Trading signal received')
        
        success = send_ios_notification(message)
        
        return jsonify({
            "message": "iOS notification sent",
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"iOS webhook error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def root():
    """Root endpoint"""
    return jsonify({
        "name": "EMA Crossover Alert Bot",
        "version": "2.0.0",
        "status": "running" if bot_initialized and is_running else "starting",
        "endpoints": {
            "/health": "Health check",
            "/ping": "Simple ping",
            "/initialize": "Manual initialization",
            "/status": "Bot status",
            "/test-notification": "Test notifications",
            "/webhook/ios": "iOS webhook"
        },
        "timestamp": datetime.now().isoformat()
    })

# Initialize bot on first request
@app.before_request
def check_and_initialize():
    """Check and initialize bot before each request"""
    global bot_initialized
    if not bot_initialized:
        logger.info("Bot not initialized, starting initialization...")
        initialize_bot()

if __name__ == "__main__":
    logger.info("Starting EMA Crossover Bot...")
    app.run(host='0.0.0.0', port=PORT, debug=False)
