"""
Main EMA Crossover Alert Bot
Orchestrates market analysis, signal generation, and notifications
Optimized for Render cloud deployment with keep-alive functionality
"""

import logging
import time
import threading
import schedule
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from data_fetcher import DataFetcher
from technical_indicators import TechnicalIndicators
from alert_manager import AlertManager
from notifications.notification_manager import NotificationManager
from config import (
    PORT, ANALYSIS_INTERVAL_MINUTES, KEEP_ALIVE_INTERVAL_MINUTES,
    CRYPTO_PAIRS, FOREX_PAIRS, LOG_LEVEL, LOG_FORMAT
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Global bot components
data_fetcher = None
technical_indicators = None
alert_manager = None
notification_manager = None

# Bot state
bot_start_time = None
last_analysis_time = None
analysis_count = 0
error_count = 0
is_running = False

def initialize_bot():
    """Initialize all bot components"""
    global data_fetcher, technical_indicators, alert_manager, notification_manager
    
    try:
        logger.info("Initializing EMA Crossover Alert Bot...")
        
        # Initialize components
        data_fetcher = DataFetcher()
        technical_indicators = TechnicalIndicators()
        alert_manager = AlertManager()
        notification_manager = NotificationManager()
        
        logger.info("Bot components initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}")
        return False

def analyze_markets():
    """Perform market analysis for all configured pairs"""
    global last_analysis_time, analysis_count, error_count
    
    try:
        logger.info("Starting market analysis...")
        start_time = time.time()
        
        # Fetch market data
        market_data = data_fetcher.fetch_all_market_data()
        
        if not market_data:
            logger.warning("No market data received")
            return
        
        # Analyze each symbol
        analysis_results = {}
        signals_generated = 0
        
        for symbol, df in market_data.items():
            try:
                # Validate data quality
                if not data_fetcher.validate_data_quality(df, symbol):
                    logger.warning(f"Data quality validation failed for {symbol}")
                    continue
                
                # Perform technical analysis
                signal_data = technical_indicators.analyze_market(df)
                
                # Store results
                analysis_results[symbol] = signal_data
                
                # Process signals if any
                if signal_data["signal"] != "no_signal":
                    alert_result = alert_manager.process_signal(symbol, signal_data)
                    if alert_result.get("alert_sent"):
                        signals_generated += 1
                        logger.info(f"Signal processed for {symbol}: {signal_data['signal']}")
                
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                error_count += 1
                continue
        
        # Send market summary if signals were generated
        if signals_generated > 0:
            notification_manager.send_market_summary(analysis_results)
        
        # Update bot state
        last_analysis_time = datetime.now()
        analysis_count += 1
        
        analysis_duration = time.time() - start_time
        logger.info(f"Market analysis completed in {analysis_duration:.2f}s. "
                   f"Analyzed {len(analysis_results)} symbols, generated {signals_generated} signals.")
        
    except Exception as e:
        logger.error(f"Error in market analysis: {e}")
        error_count += 1

def keep_alive_ping():
    """Send keep-alive ping to prevent Render from sleeping"""
    try:
        # This endpoint will be called by external monitoring service
        # or by the bot itself to maintain wakefulness
        logger.debug("Keep-alive ping sent")
        return True
    except Exception as e:
        logger.error(f"Keep-alive ping failed: {e}")
        return False

def run_scheduler():
    """Run the scheduled tasks"""
    global is_running
    
    logger.info("Starting scheduled tasks...")
    
    # Schedule market analysis
    schedule.every(ANALYSIS_INTERVAL_MINUTES).minutes.do(analyze_markets)
    
    # Schedule keep-alive ping
    schedule.every(KEEP_ALIVE_INTERVAL_MINUTES).minutes.do(keep_alive_ping)
    
    is_running = True
    
    while is_running:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error in scheduler: {e}")
            time.sleep(5)

def start_background_tasks():
    """Start background tasks in separate threads"""
    # Start scheduler in background thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    logger.info("Background tasks started")

# Flask Routes

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring and keep-alive"""
    global bot_start_time, last_analysis_time, analysis_count, error_count, is_running
    
    try:
        # Perform keep-alive ping
        keep_alive_ping()
        
        health_status = {
            "status": "healthy" if is_running else "starting",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": int((datetime.now() - bot_start_time).total_seconds()) if bot_start_time else 0,
            "last_analysis": last_analysis_time.isoformat() if last_analysis_time else None,
            "analysis_count": analysis_count,
            "error_count": error_count,
            "is_running": is_running
        }
        
        return jsonify(health_status)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/status')
def bot_status():
    """Get comprehensive bot status and market summary"""
    try:
        # Get signal status
        signal_status = alert_manager.get_signal_status() if alert_manager else {}
        
        # Get notification status
        notification_status = notification_manager.get_notification_status() if notification_manager else {}
        
        status = {
            "bot_info": {
                "start_time": bot_start_time.isoformat() if bot_start_time else None,
                "uptime_seconds": int((datetime.now() - bot_start_time).total_seconds()) if bot_start_time else 0,
                "is_running": is_running,
                "last_analysis": last_analysis_time.isoformat() if last_analysis_time else None,
                "analysis_count": analysis_count,
                "error_count": error_count
            },
            "market_coverage": {
                "crypto_pairs": CRYPTO_PAIRS,
                "forex_pairs": FOREX_PAIRS,
                "total_pairs": len(CRYPTO_PAIRS) + len(FOREX_PAIRS)
            },
            "signal_status": signal_status,
            "notification_status": notification_status,
            "configuration": {
                "analysis_interval_minutes": ANALYSIS_INTERVAL_MINUTES,
                "keep_alive_interval_minutes": KEEP_ALIVE_INTERVAL_MINUTES
            }
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Status request failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/test-notification')
def test_notification():
    """Test notification system"""
    try:
        if not notification_manager:
            return jsonify({"error": "Notification manager not initialized"}), 500
        
        result = notification_manager.send_test_notifications()
        
        return jsonify({
            "message": "Test notifications sent",
            "results": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Test notification failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/test-ios')
def test_ios():
    """Test iOS Shortcuts specifically"""
    try:
        if not notification_manager:
            return jsonify({"error": "Notification manager not initialized"}), 500
        
        # Test iOS connection
        ios_status = notification_manager.ios_notifier.test_connection()
        
        # Send test notification if connection is good
        if ios_status.get("success"):
            test_result = notification_manager.ios_notifier.send_test_notification()
            return jsonify({
                "message": "iOS Shortcuts test completed",
                "connection_status": ios_status,
                "test_notification_sent": test_result,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "message": "iOS Shortcuts connection test failed",
                "connection_status": ios_status,
                "timestamp": datetime.now().isoformat()
            })
        
    except Exception as e:
        logger.error(f"iOS test failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/webhook/ios', methods=['POST', 'GET'])
def ios_webhook():
    """Production iOS webhook endpoint for notifications"""
    try:
        if not notification_manager:
            return jsonify({"error": "Notification manager not initialized"}), 500
        
        # Handle GET request (for testing)
        if request.method == 'GET':
            return jsonify({
                "message": "iOS Webhook endpoint active",
                "status": "ready",
                "endpoint": "/webhook/ios",
                "methods": ["GET", "POST"],
                "timestamp": datetime.now().isoformat()
            })
        
        # Handle POST request (for actual notifications)
        data = request.get_json() or {}
        
        # Extract notification data
        message = data.get('message', 'Trading signal received')
        signal_type = data.get('signal_type', 'alert')
        priority = data.get('priority', 'medium')
        price = data.get('price')
        
        # Send notification via iOS Shortcuts
        success = notification_manager.ios_notifier.send_notification(
            message=message,
            signal_type=signal_type,
            priority=priority,
            price=price
        )
        
        return jsonify({
            "message": "iOS notification sent",
            "success": success,
            "data_received": data,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"iOS webhook failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/notification-status')
def notification_status():
    """Get notification system health status"""
    try:
        if not notification_manager:
            return jsonify({"error": "Notification manager not initialized"}), 500
        
        status = notification_manager.get_notification_status()
        
        return jsonify({
            "message": "Notification system status",
            "status": status,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Notification status request failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/clear-cooldown/<symbol>')
def clear_cooldown(symbol):
    """Clear cooldown for a specific symbol (for testing)"""
    try:
        if not alert_manager:
            return jsonify({"error": "Alert manager not initialized"}), 500
        
        success = alert_manager.clear_cooldown(symbol)
        
        return jsonify({
            "message": f"Cooldown cleared for {symbol}" if success else f"No cooldown found for {symbol}",
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Clear cooldown failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def root():
    """Root endpoint with basic bot information"""
    return jsonify({
        "name": "EMA Crossover Alert Bot",
        "version": "1.0.0",
        "description": "Automated trading signal generator with EMA crossover strategy",
        "endpoints": {
            "/health": "Health check and keep-alive",
            "/status": "Bot status and market summary",
            "/test-notification": "Test notification system",
            "/test-ios": "Test iOS Shortcuts specifically",
            "/webhook/ios": "Production iOS webhook endpoint",
            "/notification-status": "Notification system health",
            "/clear-cooldown/<symbol>": "Clear cooldown for testing"
        },
        "timestamp": datetime.now().isoformat()
    })

def main():
    """Main bot entry point"""
    global bot_start_time
    
    try:
        # Initialize bot
        if not initialize_bot():
            logger.error("Bot initialization failed")
            return
        
        bot_start_time = datetime.now()
        logger.info(f"EMA Crossover Alert Bot started at {bot_start_time}")
        
        # Start background tasks
        start_background_tasks()
        
        # Run Flask app
        logger.info(f"Starting Flask server on port {PORT}")
        app.run(host='0.0.0.0', port=PORT, debug=False)
        
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.error(f"Bot startup failed: {e}")
    finally:
        # Cleanup
        logger.info("Cleaning up bot resources...")
        if data_fetcher:
            data_fetcher.cleanup()
        if alert_manager:
            alert_manager.cleanup()
        if notification_manager:
            notification_manager.cleanup()
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    main()

