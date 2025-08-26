#!/usr/bin/env python3
"""
EMA Crossover Alert Bot - Production Ready
Bulletproof implementation that survives Gunicorn on Render
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
initialization_attempts = 0
max_initialization_attempts = 5

# Configuration
PORT = int(os.getenv("PORT", 8000))
IOS_WEBHOOK_URL = os.getenv("IOS_WEBHOOK_URL", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Render-specific configuration
RENDER = os.getenv("RENDER", "false").lower() == "true"
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "")  # Set this in Render environment

# External keep-alive services (free)
EXTERNAL_PING_URLS = [
    "https://api.uptimerobot.com/v2/getMonitors",  # UptimeRobot API
    "https://httpbin.org/get",  # Simple HTTP test
]

# Auto-detect Render URL from request headers
def get_render_url():
    """Auto-detect Render URL from request context"""
    global RENDER_URL
    
    if RENDER_URL:
        return RENDER_URL
    
    try:
        # Try to get from request context (if available)
        from flask import request
        if request and hasattr(request, 'headers'):
            # Check for common proxy headers
            forwarded_proto = request.headers.get('X-Forwarded-Proto', '')
            forwarded_host = request.headers.get('X-Forwarded-Host', '')
            host = request.headers.get('Host', '')
            
            if forwarded_proto and forwarded_host:
                return f"{forwarded_proto}://{forwarded_host}"
            elif host and not host.startswith('localhost'):
                return f"https://{host}"
    except:
        pass
    
    return ""

# Market pairs to monitor
CRYPTO_PAIRS = ["BTC", "ETH", "SOL", "XRP"]  # Simplified symbols
FOREX_PAIRS = ["EURUSD", "USDJPY", "GBPUSD"]  # Simplified symbols

# Signal cooldown (prevent spam)
signal_cooldowns = {}

# Global scheduler and thread references
scheduler_thread = None
keep_alive_thread = None

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

def detect_choch(data, lookback_periods=10):
    """Detect Change of Character (CHOCH) with volume confirmation"""
    try:
        if len(data) < lookback_periods + 5:
            return None, 0
        
        # Get recent data for analysis
        recent_data = data.tail(lookback_periods + 5)
        
        # Calculate average volume for comparison
        avg_volume = recent_data['volume'].mean()
        
        # Look for momentum changes in the last 5-10 periods
        highs = recent_data['high'].tail(5)
        lows = recent_data['low'].tail(5)
        
        # Check for higher highs and higher lows (bullish momentum)
        bullish_momentum = all(highs.iloc[i] >= highs.iloc[i-1] for i in range(1, len(highs)))
        bullish_momentum &= all(lows.iloc[i] >= lows.iloc[i-1] for i in range(1, len(lows)))
        
        # Check for lower highs and lower lows (bearish momentum)
        bearish_momentum = all(highs.iloc[i] <= highs.iloc[i-1] for i in range(1, len(highs)))
        bearish_momentum &= all(lows.iloc[i] <= lows.iloc[i-1] for i in range(1, len(lows)))
        
        # Check volume confirmation (1.5x average)
        current_volume = data['volume'].iloc[-1]
        volume_confirmed = current_volume >= (avg_volume * 1.5)
        
        if bullish_momentum and volume_confirmed:
            return "BULLISH", 1.0
        elif bearish_momentum and volume_confirmed:
            return "BEARISH", 1.0
        elif bullish_momentum or bearish_momentum:
            return "BULLISH" if bullish_momentum else "BEARISH", 0.5
        else:
            return None, 0
            
    except Exception as e:
        logger.error(f"CHOCH detection error: {e}")
        return None, 0

def detect_bos(data, lookback_periods=20, price_threshold=0.01):
    """Detect Break of Structure (BOS) using fractal swing analysis"""
    try:
        if len(data) < lookback_periods + 10:
            return None, 0
        
        # Get data for structure analysis
        structure_data = data.tail(lookback_periods + 10)
        
        # Find swing highs and lows (fractals)
        swing_highs = []
        swing_lows = []
        
        for i in range(2, len(structure_data) - 2):
            # Swing high: higher than 2 bars before and after
            if (structure_data['high'].iloc[i] > structure_data['high'].iloc[i-1] and 
                structure_data['high'].iloc[i] > structure_data['high'].iloc[i-2] and
                structure_data['high'].iloc[i] > structure_data['high'].iloc[i+1] and
                structure_data['high'].iloc[i] > structure_data['high'].iloc[i+2]):
                swing_highs.append((i, structure_data['high'].iloc[i]))
            
            # Swing low: lower than 2 bars before and after
            if (structure_data['low'].iloc[i] < structure_data['low'].iloc[i-1] and 
                structure_data['low'].iloc[i] < structure_data['low'].iloc[i-2] and
                structure_data['low'].iloc[i] < structure_data['low'].iloc[i+1] and
                structure_data['low'].iloc[i] < structure_data['low'].iloc[i+2]):
                swing_lows.append((i, structure_data['low'].iloc[i]))
        
        if not swing_highs or not swing_lows:
            return None, 0
        
        # Get current price and recent structure levels
        current_price = data['close'].iloc[-1]
        recent_high = max(swing_highs, key=lambda x: x[0])[1] if swing_highs else None
        recent_low = min(swing_lows, key=lambda x: x[0])[1] if swing_lows else None
        
        # Check for break above resistance (bullish BOS)
        if recent_high and current_price > recent_high:
            price_break = (current_price - recent_high) / recent_high
            if price_break >= price_threshold:  # 1% threshold
                # Check volume confirmation
                current_volume = data['volume'].iloc[-1]
                avg_volume = data['volume'].tail(20).mean()
                volume_confirmed = current_volume >= (avg_volume * 1.5)
                
                if volume_confirmed:
                    return "BULLISH", 2.0
                else:
                    return "BULLISH", 1.5
        
        # Check for break below support (bearish BOS)
        if recent_low and current_price < recent_low:
            price_break = (recent_low - current_price) / recent_low
            if price_break >= price_threshold:  # 1% threshold
                # Check volume confirmation
                current_volume = data['volume'].iloc[-1]
                avg_volume = data['volume'].tail(20).mean()
                volume_confirmed = current_volume >= (avg_volume * 1.5)
                
                if volume_confirmed:
                    return "BEARISH", 2.0
                else:
                    return "BEARISH", 1.5
        
        return None, 0
        
    except Exception as e:
        logger.error(f"BOS detection error: {e}")
        return None, 0

def calculate_confidence_level(ema_signal, choch_signal, bos_signal):
    """Calculate confidence level based on signal confirmations"""
    try:
        base_confidence = 3  # Base EMA crossover confidence
        
        # Add CHOCH confirmation
        if choch_signal and choch_signal[0] == ema_signal[0]:  # Same direction
            base_confidence += 1
        
        # Add BOS confirmation
        if bos_signal and bos_signal[0] == ema_signal[0]:  # Same direction
            base_confidence += 1
        
        # Ensure confidence is within 1-5 range
        confidence = max(1, min(5, base_confidence))
        
        return confidence
        
    except Exception as e:
        logger.error(f"Confidence calculation error: {e}")
        return 3  # Default to base confidence

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
                
                # Fetch real market data with multiple fallbacks
                market_data = fetch_market_data_robust(symbol)
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
                    
                    # Enhanced analysis: CHOCH and BOS detection
                    choch_signal = detect_choch(market_data)
                    bos_signal = detect_bos(market_data)
                    
                    # Calculate confidence level
                    confidence_level = calculate_confidence_level(
                        crossover_signal, choch_signal, bos_signal
                    )
                    
                    # Create enhanced notification message
                    message = create_signal_message(
                        symbol, signal_type, current_price, 
                        current_ema_9, current_ema_20, strength,
                        confidence_level, choch_signal, bos_signal
                    )
                    
                    # Send notification
                    if send_notification(message, symbol):
                        logger.info(f"Enhanced signal sent for {symbol}: {signal_type} (Confidence: {confidence_level}/5)")
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

def fetch_market_data_robust(symbol):
    """Fetch market data with Yahoo Finance (works globally)"""
    try:
        # Use Yahoo Finance as primary source (proven to work)
        data = fetch_yahoo_finance_data(symbol)
        if data is not None:
            logger.info(f"Yahoo Finance data successful for {symbol}")
            return data
        
        # If Yahoo Finance fails, log error and return None
        logger.error(f"Yahoo Finance failed for {symbol}")
        return None
        
    except Exception as e:
        logger.error(f"Data fetching failed for {symbol}: {e}")
        return None

def fetch_yahoo_finance_data(symbol):
    """Fetch data from Yahoo Finance (works globally)"""
    try:
        import yfinance as yf
        import pandas as pd
        
        # Add appropriate suffix for Yahoo Finance
        if symbol in CRYPTO_PAIRS:
            yf_symbol = f"{symbol}-USD"
        else:
            yf_symbol = f"{symbol}=X"
        
        # Fetch 15-minute data for the last 7 days
        ticker = yf.Ticker(yf_symbol)
        data = ticker.history(period="7d", interval="15m")
        
        if data.empty or len(data) < 50:
            logger.warning(f"Insufficient Yahoo Finance data for {symbol}: {len(data)} points")
            return None
        
        # Ensure we have the required columns
        if 'Close' not in data.columns:
            logger.warning(f"Missing Close column for {symbol} from Yahoo Finance")
            return None
        
        # Rename columns to match our expected format
        data = data.rename(columns={
            'Close': 'close',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Volume': 'volume'
        })
        
        logger.info(f"Yahoo Finance: {len(data)} data points for {symbol}")
        return data
        
    except Exception as e:
        logger.error(f"Yahoo Finance fetch error for {symbol}: {e}")
        return None

def calculate_ema(data, period):
    """Calculate Exponential Moving Average"""
    try:
        if len(data) < period:
            return None
        
        # Calculate EMA using pandas
        ema = data['close'].ewm(span=period, adjust=False).mean()
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

def create_signal_message(symbol, signal_type, price, ema_9, ema_20, strength, confidence_level, choch_signal=None, bos_signal=None):
    """Create detailed signal notification message with confidence levels"""
    try:
        # Format price based on symbol type
        if symbol in CRYPTO_PAIRS:
            price_str = f"${price:.4f}"
        else:
            price_str = f"${price:.6f}"
        
        # Format strength
        strength_str = f"{strength:.2f}%"
        
        # Confidence level emojis
        confidence_emojis = {
            1: "⚠️",
            2: "⚠️", 
            3: "⚡",
            4: "🔥",
            5: "🚀"
        }
        
        confidence_emoji = confidence_emojis.get(confidence_level, "⚡")
        
        # Create message header
        message = f"{confidence_emoji} {signal_type} SIGNAL - CONFIDENCE {confidence_level}/5!\n\n"
        message += f"Symbol: {symbol}\n"
        message += f"Price: {price_str}\n"
        message += f"Signal Type: {signal_type} EMA Crossover\n"
        message += f"EMA 9: ${ema_9:.4f}\n"
        message += f"EMA 20: ${ema_20:.4f}\n"
        message += f"EMA Separation: {strength_str}\n"
        message += f"Time: {datetime.now().strftime('%H:%M UTC')}\n\n"
        
        # Add confirmation details
        message += "📊 CONFIRMATION ANALYSIS:\n"
        message += f"✅ EMA Crossover: {signal_type}\n"
        
        if choch_signal:
            choch_type, choch_strength = choch_signal
            if choch_type == signal_type:
                message += f"✅ CHOCH: {choch_type} Momentum (Volume: {'Confirmed' if choch_strength >= 1.0 else 'Partial'})\n"
            else:
                message += f"⚠️ CHOCH: {choch_type} Momentum (Conflicts with signal)\n"
        else:
            message += "❌ CHOCH: No momentum change detected\n"
        
        if bos_signal:
            bos_type, bos_strength = bos_signal
            if bos_type == signal_type:
                message += f"✅ BOS: {bos_type} Structure Break (Volume: {'Confirmed' if bos_strength >= 2.0 else 'Partial'})\n"
            else:
                message += f"⚠️ BOS: {bos_type} Structure Break (Conflicts with signal)\n"
        else:
            message += "❌ BOS: No structure break detected\n"
        
        message += f"\n🎯 CONFIDENCE BREAKDOWN:\n"
        message += f"• Base EMA Crossover: 3/5\n"
        if choch_signal and choch_signal[0] == signal_type:
            message += f"• +1 CHOCH Confirmation: 4/5\n"
        if bos_signal and bos_signal[0] == signal_type:
            message += f"• +1 BOS Confirmation: 5/5\n"
        
        message += f"\n💡 ACTION RECOMMENDATION:\n"
        if signal_type == "BULLISH":
            message += f"💚 Consider BUYING {symbol} - {confidence_level}/5 Confidence\n"
        else:
            message += f"🔴 Consider SELLING {symbol} - {confidence_level}/5 Confidence\n"
        
        # Add risk assessment based on confidence
        if confidence_level >= 4:
            message += "🔥 HIGH CONFIDENCE - Strong technical confirmation\n"
        elif confidence_level == 3:
            message += "⚡ MEDIUM CONFIDENCE - Basic EMA signal only\n"
        else:
            message += "⚠️ LOW CONFIDENCE - Conflicting signals detected\n"
        
        message += f"\n⚠️  This is not financial advice. Always do your own research."
        
        return message
        
    except Exception as e:
        logger.error(f"Error creating signal message: {e}")
        return f"EMA Crossover Signal: {signal_type} for {symbol} - Confidence {confidence_level}/5"

def keep_alive_ping():
    """Keep the bot alive and prevent Render from sleeping"""
    try:
        render_url = get_render_url()
        
        if RENDER and render_url:
            # On Render, ping external URL
            health_url = f"{render_url}/health"
            logger.info(f"Render keep-alive ping to: {health_url}")
            
            # Also ping external services to generate traffic
            for ping_url in EXTERNAL_PING_URLS:
                try:
                    requests.get(ping_url, timeout=5)
                    logger.debug(f"External ping successful: {ping_url}")
                except:
                    pass  # Ignore external ping failures
        else:
            # Local development, ping localhost
            health_url = f"http://localhost:{PORT}/health"
            logger.info(f"Local keep-alive ping to: {health_url}")
        
        response = requests.get(health_url, timeout=10)
        
        if response.status_code == 200:
            logger.info("Keep-alive ping successful")
        else:
            logger.warning(f"Keep-alive ping failed: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Keep-alive ping error: {e}")

def run_scheduler():
    """Run the scheduler in a separate thread"""
    global is_running
    
    try:
        logger.info("Starting scheduler...")
        
        # Schedule market analysis every 15 minutes
        schedule.every(15).minutes.do(analyze_markets)
        
        # Schedule keep-alive ping every minute
        schedule.every(1).minutes.do(keep_alive_ping)
        
        logger.info("Scheduler started successfully")
        
        # Run the scheduler
        while is_running:
            schedule.run_pending()
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        # Try to restart scheduler
        if is_running:
            logger.info("Attempting to restart scheduler...")
            time.sleep(5)
            run_scheduler()

def initialize_bot():
    """Initialize the bot with bulletproof error handling"""
    global bot_start_time, is_running, bot_initialized, scheduler_thread, keep_alive_thread, initialization_attempts
    
    try:
        if bot_initialized:
            logger.info("Bot already initialized, skipping...")
            return True
            
        logger.info("Initializing bot...")
        
        # Set bot state
        bot_start_time = datetime.now()
        is_running = True
        bot_initialized = True
        
        # Start scheduler in background thread
        if scheduler_thread is None or not scheduler_thread.is_alive():
            scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
            scheduler_thread.start()
            logger.info("Scheduler thread started")
        
        # Start keep-alive thread as backup
        if keep_alive_thread is None or not keep_alive_thread.is_alive():
            keep_alive_thread = threading.Thread(target=keep_alive_loop, daemon=True)
            keep_alive_thread.start()
            logger.info("Keep-alive thread started")
        
        logger.info("Bot initialized successfully")
        initialization_attempts = 0
        return True
        
    except Exception as e:
        logger.error(f"Bot initialization error: {e}")
        initialization_attempts += 1
        
        if initialization_attempts < max_initialization_attempts:
            logger.info(f"Retrying initialization in 5 seconds... (Attempt {initialization_attempts}/{max_initialization_attempts})")
            time.sleep(5)
            return initialize_bot()
        else:
            logger.error("Max initialization attempts reached. Bot may not function properly.")
            return False

def keep_alive_loop():
    """Dedicated keep-alive loop that runs independently"""
    global is_running
    
    try:
        logger.info("Starting dedicated keep-alive loop...")
        
        while is_running:
            try:
                render_url = get_render_url()
                
                if RENDER and render_url:
                    # On Render, ping external URL
                    health_url = f"{render_url}/health"
                else:
                    # Local development, ping localhost
                    health_url = f"http://localhost:{PORT}/health"
                
                response = requests.get(health_url, timeout=10)
                
                if response.status_code == 200:
                    logger.debug("Keep-alive ping successful")
                else:
                    logger.warning(f"Keep-alive ping failed: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Keep-alive ping error: {e}")
            
            # Wait 1 minute before next ping
            time.sleep(60)
            
    except Exception as e:
        logger.error(f"Keep-alive loop error: {e}")
        # Restart the loop
        if is_running:
            time.sleep(5)
            keep_alive_loop()

# Flask routes
@app.route('/health')
def health_check():
    """Health check endpoint"""
    global bot_start_time, last_analysis_time, analysis_count, is_running, bot_initialized
    
    try:
        uptime = (datetime.now() - bot_start_time).total_seconds() if bot_start_time else 0
        
        return jsonify({
            "status": "healthy" if bot_initialized and is_running else "unhealthy",
            "initialized": bot_initialized,
            "running": is_running,
            "uptime_seconds": int(uptime),
            "last_analysis": last_analysis_time.isoformat() if last_analysis_time else None,
            "analysis_count": analysis_count,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/ping')
def ping():
    """Simple ping endpoint"""
    return jsonify({"message": "pong", "timestamp": datetime.now().isoformat()})

@app.route('/initialize')
def manual_initialize():
    """Manual initialization endpoint"""
    try:
        success = initialize_bot()
        return jsonify({
            "message": "Bot initialization",
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Manual initialization error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/status')
def status():
    """Bot status endpoint"""
    global bot_start_time, last_analysis_time, analysis_count, is_running, bot_initialized
    
    try:
        uptime = (datetime.now() - bot_start_time).total_seconds() if bot_start_time else 0
        
        return jsonify({
            "status": "running" if bot_initialized and is_running else "stopped",
            "initialized": bot_initialized,
            "running": is_running,
            "uptime_seconds": int(uptime),
            "last_analysis": last_analysis_time.isoformat() if last_analysis_time else None,
            "analysis_count": analysis_count,
            "scheduler_thread_alive": scheduler_thread.is_alive() if scheduler_thread else False,
            "keep_alive_thread_alive": keep_alive_thread.is_alive() if keep_alive_thread else False,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/test-notification')
def test_notification():
    """Test notification endpoint"""
    try:
        test_message = f"🧪 Test notification from EMA Crossover Bot\nTime: {datetime.now().strftime('%H:%M UTC')}\nStatus: Bot is working!"
        
        ios_sent = send_ios_notification(test_message)
        telegram_sent = send_telegram_notification(test_message)
        
        return jsonify({
            "message": "Test notification sent",
            "ios_sent": ios_sent,
            "telegram_sent": telegram_sent,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Test notification error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/test-analysis')
def test_analysis():
    """Test market analysis endpoint"""
    try:
        logger.info("Manual analysis test requested")
        analyze_markets()
        
        return jsonify({
            "message": "Market analysis completed",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Test analysis error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/test-enhanced-signal')
def test_enhanced_signal():
    """Test enhanced signal generation with CHOCH + BOS"""
    try:
        logger.info("Starting enhanced signal test...")
        
        # Test with BTC data
        symbol = "BTC"
        market_data = fetch_market_data_robust(symbol)
        
        if market_data is None:
            return jsonify({"error": "Failed to fetch market data"}), 500
        
        # Calculate EMAs
        ema_9 = calculate_ema(market_data, 9)
        ema_20 = calculate_ema(market_data, 20)
        
        if ema_9 is None or ema_20 is None:
            return jsonify({"error": "Failed to calculate EMAs"}), 500
        
        # Simulate a bullish signal
        current_price = market_data['close'].iloc[-1]
        current_ema_9 = ema_9[-1]
        current_ema_20 = ema_20[-1]
        strength = abs(current_ema_9 - current_ema_20) / current_ema_20 * 100
        
        # Detect CHOCH and BOS
        choch_signal = detect_choch(market_data)
        bos_signal = detect_bos(market_data)
        
        # Calculate confidence
        confidence_level = calculate_confidence_level(
            ("BULLISH", strength), choch_signal, bos_signal
        )
        
        # Create enhanced message
        message = create_signal_message(
            symbol, "BULLISH", current_price,
            current_ema_9, current_ema_20, strength,
            confidence_level, choch_signal, bos_signal
        )
        
        return jsonify({
            "message": "Enhanced signal test completed",
            "symbol": symbol,
            "signal_type": "BULLISH",
            "confidence_level": confidence_level,
            "choch_signal": choch_signal,
            "bos_signal": bos_signal,
            "enhanced_message": message,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Enhanced signal test error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/webhook/ios', methods=['POST'])
def ios_webhook():
    """iOS Shortcuts webhook endpoint"""
    try:
        data = request.get_json()
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

@app.route('/configure', methods=['POST'])
def configure_bot():
    """Configure bot settings"""
    try:
        data = request.get_json() or {}
        global RENDER_URL
        
        if 'render_url' in data:
            RENDER_URL = data['render_url']
            logger.info(f"Render URL configured: {RENDER_URL}")
        
        return jsonify({
            "message": "Configuration updated",
            "render_url": RENDER_URL,
            "render_detected": RENDER,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/wake-up', methods=['GET', 'POST'])
def wake_up():
    """Wake up the bot and trigger immediate analysis"""
    try:
        logger.info("Wake-up request received - triggering immediate analysis")
        
        # Trigger immediate market analysis
        analyze_markets()
        
        return jsonify({
            "message": "Bot awakened successfully",
            "status": "running" if bot_initialized and is_running else "starting",
            "render_detected": RENDER,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Wake-up error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def root():
    """Root endpoint"""
    return jsonify({
        "name": "EMA Crossover Alert Bot",
        "version": "2.0.0",
        "status": "running" if bot_initialized and is_running else "starting",
        "render_detected": RENDER,
        "render_url": RENDER_URL or "auto-detecting",
        "endpoints": {
            "/health": "Health check",
            "/ping": "Simple ping",
            "/initialize": "Manual initialization",
            "/status": "Bot status",
            "/configure": "Configure bot settings",
            "/wake-up": "Wake up bot and trigger analysis",
            "/test-notification": "Test notifications",
            "/test-analysis": "Test market analysis",
            "/test-enhanced-signal": "Test enhanced signals (CHOCH + BOS)",
            "/webhook/ios": "iOS webhook"
        },
        "timestamp": datetime.now().isoformat()
    })

# Bulletproof initialization - multiple fallback mechanisms
@app.before_request
def check_and_initialize():
    """Check and initialize bot before each request with multiple fallbacks"""
    global bot_initialized, initialization_attempts
    
    try:
        # First fallback: Check if bot is initialized
        if not bot_initialized:
            logger.info("Bot not initialized, starting initialization...")
            initialize_bot()
        
        # Second fallback: Check if background threads are alive
        if bot_initialized and (scheduler_thread is None or not scheduler_thread.is_alive()):
            logger.warning("Scheduler thread dead, restarting...")
            initialize_bot()
        
        # Third fallback: Check if keep-alive thread is alive
        if bot_initialized and (keep_alive_thread is None or not keep_alive_thread.is_alive()):
            logger.warning("Keep-alive thread dead, restarting...")
            initialize_bot()
        
        # Fourth fallback: Force re-initialization if too many failures
        if initialization_attempts >= max_initialization_attempts:
            logger.error("Too many initialization failures, forcing restart...")
            bot_initialized = False
            initialization_attempts = 0
            initialize_bot()
            
    except Exception as e:
        logger.error(f"Initialization check error: {e}")
        # Don't let initialization errors crash the request

# Initialize bot on startup
if __name__ == "__main__":
    logger.info("Starting EMA Crossover Bot...")
    initialize_bot()
    app.run(host='0.0.0.0', port=PORT, debug=False)
