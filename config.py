"""
Configuration file for EMA Crossover Alert Bot
Contains all trading parameters, market pairs, and technical indicator settings
"""

import os
from typing import List, Dict, Any

# EMA Configuration
FAST_EMA = 9
SLOW_EMA = 20
TIMEFRAME = "15m"

# Market Pairs
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

# Technical Analysis Parameters
BOS_LOOKBACK = 5  # Break of Structure lookback period
CHOCH_LOOKBACK = 10  # Change of Character lookback period
VOLUME_THRESHOLD = 1.5  # Volume confirmation multiplier
MIN_SIGNAL_STRENGTH = 0.7  # Minimum signal strength for confirmed signals

# Cooldown Periods (in minutes)
BASE_SIGNAL_COOLDOWN = 30
CONFIRMED_SIGNAL_COOLDOWN = 60

# Data Fetching
DATA_TIMEOUT = 10  # seconds
MAX_RETRIES = 3
CANDLE_LIMIT = 100  # Number of candles to fetch for analysis

# Notification Settings
NOTIFICATION_COOLDOWN = 300  # 5 minutes between notifications for same symbol
MAX_ALERT_HISTORY = 1000  # Maximum number of alerts to keep in memory

# Flask Configuration
PORT = int(os.getenv("PORT", 8080))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Environment Variables
IOS_WEBHOOK_URL = os.getenv("IOS_WEBHOOK_URL", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Binance API Configuration
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")

# Analysis Schedule
ANALYSIS_INTERVAL_MINUTES = 15
KEEP_ALIVE_INTERVAL_MINUTES = 2

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Signal Confidence Thresholds
CONFIDENCE_LEVELS = {
    "very_low": 0.0,
    "low": 0.2,
    "medium": 0.4,
    "high": 0.6,
    "very_high": 0.8
}

# Market Data Sources
DATA_SOURCES = {
    "crypto": "binance",
    "forex": "yahoo_finance"
}

# Error Handling
MAX_CONSECUTIVE_FAILURES = 5
FAILURE_COOLDOWN_MINUTES = 30

