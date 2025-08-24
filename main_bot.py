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
    """Analyze markets for real EMA crossover signals"""
    global last_analysis_time, analysis_count
    
    try:
        logger.info("Starting real market analysis...")
        start_time = time.time()
        
        successful_analyses = 0
        failed_analyses = 0
        
        # Analyze each symbol for EMA crossovers
        for symbol in CRYPTO_PAIRS + FOREX_PAIRS:
            try:
                logger.info(f"Analyzing {symbol}...")
                
                # Fetch real market data
                market_data = fetch_market_data(symbol)
                if market_data is None or len(market_data) < 50:
                    logger.warning(f"Insufficient data for {symbol}, skipping")
                    failed_analyses += 1
                    continue
                
                # Calculate EMAs
                ema_9 = calculate_ema(market_data, 9)
                ema_20 = calculate_ema(market_data, 20)
                
                if ema_9 is None or ema_20 is None:
                    logger.warning(f"Failed to calculate EMAs for {symbol}")
                    failed_analyses += 1
                    continue
                
                # Get current and previous EMA values
                current_ema_9 = ema_9[-1]
                current_ema_20 = ema_20[-1]
                prev_ema_9 = ema_9[-2]
                prev_ema_20 = ema_20[-2]
                
                # Check for EMA crossover
                crossover_signal = detect_ema_crossover(
                    prev_ema_9, prev_ema_20, 
                    current_ema_9, current_ema_20
                )
                
                if crossover_signal:
                    signal_type, strength = crossover_signal
                    current_price = market_data['close'].iloc[-1]
                    
                    # Create detailed notification message
                    message = create_signal_message(
                        symbol, signal_type, current_price, 
                        current_ema_9, current_ema_20, strength
                    )
                    
                    # Send notification
                    if send_notification(message, symbol):
                        logger.info(f"EMA crossover signal sent for {symbol}: {signal_type}")
                    else:
                        logger.warning(f"Failed to send signal notification for {symbol}")
                
                successful_analyses += 1
                logger.info(f"Successfully analyzed {symbol}")
                
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                failed_analyses += 1
                continue
        
        last_analysis_time = datetime.now()
        analysis_count += 1
        
        duration = time.time() - start_time
        logger.info(f"Real market analysis completed in {duration:.2f}s")
        logger.info(f"Successful: {successful_analyses}, Failed: {failed_analyses}")
        
        # Don't let failures stop the bot
        if failed_analyses > 0:
            logger.warning(f"Some analyses failed, but bot continues running")
        
    except Exception as e:
        logger.error(f"Market analysis error: {e}")
        # Don't let analysis errors crash the bot
        logger.info("Bot continues running despite analysis errors")

def fetch_market_data(symbol):
    """Fetch real market data for analysis"""
    try:
        if "USDT" in symbol:
            # Use ccxt for crypto symbols
            return fetch_crypto_data(symbol)
        else:
            # Use yfinance for forex symbols
            return fetch_forex_data(symbol)
            
    except Exception as e:
        logger.error(f"Failed to fetch data for {symbol}: {e}")
        return None

def fetch_crypto_data(symbol):
    """Fetch crypto data using ccxt (Binance)"""
    try:
        import ccxt
        
        # Initialize Binance exchange (public API if no keys provided)
        if BINANCE_API_KEY and BINANCE_SECRET_KEY:
            exchange = ccxt.binance({
                'apiKey': BINANCE_API_KEY,
                'secret': BINANCE_SECRET_KEY,
                'sandbox': False,
                'enableRateLimit': True
            })
            logger.info(f"Using authenticated Binance API for {symbol}")
        else:
            exchange = ccxt.binance({
                'enableRateLimit': True
            })
            logger.info(f"Using public Binance API for {symbol}")
        
        # Fetch 15-minute OHLCV data (last 100 candles)
        ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
        
        if not ohlcv or len(ohlcv) < 50:
            logger.warning(f"Insufficient crypto data for {symbol}")
            return None
        
        # Convert to pandas DataFrame
        import pandas as pd
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        logger.info(f"Fetched {len(df)} crypto candles for {symbol}")
        return df
        
    except Exception as e:
        logger.error(f"Crypto data fetch error for {symbol}: {e}")
        return None

def fetch_forex_data(symbol):
    """Fetch forex data using yfinance"""
    try:
        import yfinance as yf
        
        # Fetch 15-minute data for the last 7 days
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="7d", interval="15m")
        
        if data.empty or len(data) < 50:
            logger.warning(f"Insufficient forex data for {symbol}")
            return None
        
        logger.info(f"Fetched {len(data)} forex candles for {symbol}")
        return data
        
    except Exception as e:
        logger.error(f"Forex data fetch error for {symbol}: {e}")
        return None

def calculate_ema(data, period):
    """Calculate Exponential Moving Average"""
    try:
        if len(data) < period:
            return None
        
        # Calculate EMA using pandas
        ema = data['Close'].ewm(span=period, adjust=False).mean()
        return ema.values
        
    except Exception as e:
        logger.error(f"EMA calculation error: {e}")
        return None

def detect_ema_crossover(prev_ema_9, prev_ema_20, current_ema_9, current_ema_20):
    """Detect EMA crossover signals"""
    try:
        # Check for bullish crossover (EMA 9 crosses above EMA 20)
        if prev_ema_9 <= prev_ema_20 and current_ema_9 > current_ema_20:
            # Calculate crossover strength
            strength = abs(current_ema_9 - current_ema_20) / current_ema_20 * 100
            return ("BULLISH", strength)
        
        # Check for bearish crossover (EMA 9 crosses below EMA 20)
        elif prev_ema_9 >= prev_ema_20 and current_ema_9 < current_ema_20:
            # Calculate crossover strength
            strength = abs(current_ema_9 - current_ema_20) / current_ema_20 * 100
            return ("BEARISH", strength)
        
        return None
        
    except Exception as e:
        logger.error(f"EMA crossover detection error: {e}")
        return None

def create_signal_message(symbol, signal_type, price, ema_9, ema_20, strength):
    """Create detailed signal notification message"""
    try:
        # Format price based on symbol type
        if "USDT" in symbol:
            price_str = f"${price:.4f}"
        else:
            price_str = f"${price:.6f}"
        
        # Format strength
        strength_str = f"{strength:.2f}%"
        
        # Create message
        message = f"🚨 {signal_type} EMA CROSSOVER SIGNAL!\n\n"
        message += f"Symbol: {symbol}\n"
        message += f"Price: {price_str}\n"
        message += f"Signal: {signal_type} EMA Crossover\n"
        message += f"EMA 9: ${ema_9:.4f}\n"
        message += f"EMA 20: ${ema_20:.4f}\n"
        message += f"Separation: {strength_str}\n"
        message += f"Time: {datetime.now().strftime('%H:%M UTC')}\n\n"
        
        if signal_type == "BULLISH":
            message += "💚 BULLISH SIGNAL - EMA 9 crossed above EMA 20\n"
            message += "💡 ACTION: Consider BUYING " + symbol
        else:
            message += "🔴 BEARISH SIGNAL - EMA 9 crossed below EMA 20\n"
            message += "💡 ACTION: Consider SELLING " + symbol
        
        message += f"\n\n⚠️  This is not financial advice. Always do your own research."
        
        return message
        
    except Exception as e:
        logger.error(f"Error creating signal message: {e}")
        return f"EMA Crossover Signal: {signal_type} for {symbol}"

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

@app.route('/test-analysis')
def test_analysis():
    """Test market analysis and EMA crossover detection"""
    try:
        logger.info("Manual analysis test requested")
        
        # Run a single analysis cycle
        analyze_markets()
        
        return jsonify({
            "message": "Market analysis test completed",
            "analysis_count": analysis_count,
            "last_analysis": last_analysis_time.isoformat() if last_analysis_time else None,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Analysis test failed: {e}")
        return jsonify({
            "message": "Analysis test failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

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
            "/test-analysis": "Test market analysis",
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
