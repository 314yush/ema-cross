"""
Configuration for EMA Crossover Alert Bot
Simplified and production-ready
"""

import os

# Bot Configuration
PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Notification Configuration
IOS_WEBHOOK_URL = os.getenv("IOS_WEBHOOK_URL", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Market Data Configuration
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")

# Trading Configuration
CRYPTO_PAIRS = [
    "BTCUSDT",
    "ETHUSDT", 
    "SOLUSDT",
    "XRPUSDT"
]

FOREX_PAIRS = [
    "EURUSD=X",
    "USDJPY=X",
    "GBPUSD=X"
]

# Timing Configuration
ANALYSIS_INTERVAL_MINUTES = 15  # Market analysis every 15 minutes
KEEP_ALIVE_INTERVAL_MINUTES = 1  # Keep-alive ping every minute
SIGNAL_COOLDOWN_HOURS = 1  # Prevent signal spam

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

