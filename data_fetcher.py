"""
Market Data Fetcher Module
Handles data retrieval from Binance (crypto) and Yahoo Finance (forex) APIs
"""

import time
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from binance.client import Client
import yfinance as yf
import requests
from config import (
    CRYPTO_PAIRS, FOREX_PAIRS, DATA_TIMEOUT, MAX_RETRIES,
    CANDLE_LIMIT, BINANCE_API_KEY, BINANCE_SECRET_KEY
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataFetcher:
    """Handles market data fetching from multiple sources"""
    
    def __init__(self):
        self.binance_client = None
        self.session = requests.Session()
        self.session.timeout = DATA_TIMEOUT
        
        # Initialize Binance client if credentials are available
        if BINANCE_API_KEY and BINANCE_SECRET_KEY:
            try:
                self.binance_client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
                logger.info("Binance client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Binance client: {e}")
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
    def _rate_limit(self):
        """Implement basic rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def _retry_request(self, func, *args, **kwargs) -> Optional[Any]:
        """Retry a function call with exponential backoff"""
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"All retry attempts failed for {func.__name__}")
                    return None
    
    def fetch_crypto_data(self, symbol: str, interval: str = "15m", limit: int = None) -> Optional[pd.DataFrame]:
        """Fetch cryptocurrency data from Binance"""
        if not self.binance_client:
            logger.error("Binance client not initialized")
            return None
        
        if limit is None:
            limit = CANDLE_LIMIT
            
        try:
            self._rate_limit()
            klines = self.binance_client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convert types
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            logger.info(f"Successfully fetched {len(df)} candles for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching crypto data for {symbol}: {e}")
            return None
    
    def fetch_forex_data(self, symbol: str, interval: str = "15m", period: str = "1d") -> Optional[pd.DataFrame]:
        """Fetch forex data from Yahoo Finance"""
        try:
            self._rate_limit()
            ticker = yf.Ticker(symbol)
            
            # Map interval to Yahoo Finance period
            interval_map = {
                "1m": "1m",
                "5m": "5m", 
                "15m": "15m",
                "30m": "30m",
                "1h": "1h",
                "1d": "1d"
            }
            
            yf_interval = interval_map.get(interval, "15m")
            
            # Fetch data
            df = ticker.history(
                period=period,
                interval=yf_interval,
                timeout=DATA_TIMEOUT
            )
            
            if df.empty:
                logger.warning(f"No data received for {symbol}")
                return None
            
            # Ensure we have enough data
            if len(df) < 50:  # Minimum required for analysis
                logger.warning(f"Insufficient data for {symbol}: {len(df)} candles")
                return None
            
            # Limit to requested number of candles
            if len(df) > CANDLE_LIMIT:
                df = df.tail(CANDLE_LIMIT)
            
            logger.info(f"Successfully fetched {len(df)} candles for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching forex data for {symbol}: {e}")
            return None
    
    def fetch_all_market_data(self) -> Dict[str, pd.DataFrame]:
        """Fetch data for all configured market pairs"""
        all_data = {}
        
        # Fetch crypto data
        for symbol in CRYPTO_PAIRS:
            data = self.fetch_crypto_data(symbol)
            if data is not None:
                all_data[symbol] = data
            else:
                logger.warning(f"Failed to fetch data for {symbol}")
        
        # Fetch forex data
        for symbol in FOREX_PAIRS:
            data = self.fetch_forex_data(symbol)
            if data is not None:
                all_data[symbol] = data
            else:
                logger.warning(f"Failed to fetch data for {symbol}")
        
        logger.info(f"Successfully fetched data for {len(all_data)} out of {len(CRYPTO_PAIRS) + len(FOREX_PAIRS)} symbols")
        return all_data
    
    def validate_data_quality(self, df: pd.DataFrame, symbol: str) -> bool:
        """Validate data quality and completeness"""
        if df is None or df.empty:
            logger.warning(f"Empty dataframe for {symbol}")
            return False
        
        # Check for sufficient data
        if len(df) < 50:
            logger.warning(f"Insufficient data for {symbol}: {len(df)} candles")
            return False
        
        # Check for missing values
        missing_values = df.isnull().sum().sum()
        if missing_values > 0:
            logger.warning(f"Missing values in {symbol}: {missing_values} total")
            return False
        
        # Check for zero or negative prices
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in df.columns and (df[col] <= 0).any():
                logger.warning(f"Invalid prices in {symbol} {col} column")
                return False
        
        # Check for reasonable volume
        if 'volume' in df.columns and (df['volume'] < 0).any():
            logger.warning(f"Negative volume in {symbol}")
            return False
        
        logger.info(f"Data quality validation passed for {symbol}")
        return True
    
    def get_symbol_info(self, symbol: str) -> Dict[str, str]:
        """Get basic information about a trading symbol"""
        if symbol in CRYPTO_PAIRS:
            return {
                "symbol": symbol,
                "type": "cryptocurrency",
                "source": "binance",
                "base_asset": symbol.replace("USDT", ""),
                "quote_asset": "USDT"
            }
        elif symbol in FOREX_PAIRS:
            return {
                "symbol": symbol,
                "type": "forex",
                "source": "yahoo_finance",
                "base_currency": symbol[:3],
                "quote_currency": symbol[3:6] if len(symbol) >= 6 else "USD"
            }
        else:
            return {
                "symbol": symbol,
                "type": "unknown",
                "source": "unknown"
            }
    
    def cleanup(self):
        """Cleanup resources"""
        if self.session:
            self.session.close()
        logger.info("DataFetcher cleanup completed")

