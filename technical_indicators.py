"""
Technical Indicators Module
Handles EMA crossover detection, Break of Structure (BOS), and Change of Character (CHOCH) analysis
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from config import (
    FAST_EMA, SLOW_EMA, BOS_LOOKBACK, CHOCH_LOOKBACK,
    VOLUME_THRESHOLD, MIN_SIGNAL_STRENGTH
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """Technical analysis calculations for EMA crossover strategy"""
    
    def __init__(self):
        self.fast_ema = FAST_EMA
        self.slow_ema = SLOW_EMA
        self.bos_lookback = BOS_LOOKBACK
        self.choch_lookback = CHOCH_LOOKBACK
        self.volume_threshold = VOLUME_THRESHOLD
        self.min_signal_strength = MIN_SIGNAL_STRENGTH
        
    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        try:
            ema = data.ewm(span=period, adjust=False).mean()
            return ema
        except Exception as e:
            logger.error(f"Error calculating EMA with period {period}: {e}")
            return pd.Series(dtype=float)
    
    def detect_ema_crossover(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect EMA crossover signals"""
        try:
            if len(df) < max(self.fast_ema, self.slow_ema) + 2:
                logger.warning("Insufficient data for EMA crossover analysis")
                return {"signal": "insufficient_data", "strength": 0.0, "confidence": 0}
            
            # Calculate EMAs
            df['fast_ema'] = self.calculate_ema(df['close'], self.fast_ema)
            df['slow_ema'] = self.calculate_ema(df['close'], self.slow_ema)
            
            # Get current and previous values
            current_fast = df['fast_ema'].iloc[-1]
            current_slow = df['slow_ema'].iloc[-1]
            prev_fast = df['fast_ema'].iloc[-2]
            prev_slow = df['slow_ema'].iloc[-2]
            
            # Check for crossover
            bullish_cross = (prev_fast <= prev_slow) and (current_fast > current_slow)
            bearish_cross = (prev_fast >= prev_slow) and (current_fast < current_slow)
            
            if bullish_cross:
                signal_type = "bullish_crossover"
                signal_direction = "long"
            elif bearish_cross:
                signal_type = "bearish_crossover"
                signal_direction = "short"
            else:
                signal_type = "no_crossover"
                signal_direction = "none"
            
            # Calculate signal strength based on EMA separation
            if signal_type != "no_crossover":
                ema_separation = abs(current_fast - current_slow) / current_slow
                strength = min(ema_separation * 100, 1.0)  # Normalize to 0-1
            else:
                strength = 0.0
            
            result = {
                "signal": signal_type,
                "direction": signal_direction,
                "strength": strength,
                "confidence": 2,  # Base confidence for EMA crossover
                "fast_ema": current_fast,
                "slow_ema": current_slow,
                "price": df['close'].iloc[-1],
                "timestamp": df.index[-1]
            }
            
            logger.info(f"EMA crossover analysis: {signal_type}, strength: {strength:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"Error in EMA crossover detection: {e}")
            return {"signal": "error", "strength": 0.0, "confidence": 0}
    
    def detect_break_of_structure(self, df: pd.DataFrame, direction: str) -> Dict[str, Any]:
        """Detect Break of Structure (BOS) patterns"""
        try:
            if len(df) < self.bos_lookback + 5:
                logger.warning("Insufficient data for BOS analysis")
                return {"detected": False, "strength": 0.0, "volume_confirmed": False}
            
            # Get recent price action
            recent_highs = df['high'].rolling(window=self.bos_lookback).max()
            recent_lows = df['low'].rolling(window=self.bos_lookback).min()
            
            current_price = df['close'].iloc[-1]
            current_volume = df['volume'].iloc[-1] if 'volume' in df.columns else 0
            
            # Calculate average volume for comparison
            avg_volume = df['volume'].tail(20).mean() if 'volume' in df.columns else 0
            
            bos_detected = False
            bos_strength = 0.0
            volume_confirmed = False
            
            if direction == "long":
                # Check for bullish BOS (break above recent highs)
                resistance_level = recent_highs.iloc[-2]  # Previous period's high
                if current_price > resistance_level:
                    bos_detected = True
                    # Calculate strength based on how much price broke above resistance
                    break_distance = (current_price - resistance_level) / resistance_level
                    bos_strength = min(break_distance * 10, 1.0)  # Normalize to 0-1
                    
            elif direction == "short":
                # Check for bearish BOS (break below recent lows)
                support_level = recent_lows.iloc[-2]  # Previous period's low
                if current_price < support_level:
                    bos_detected = True
                    # Calculate strength based on how much price broke below support
                    break_distance = (support_level - current_price) / support_level
                    bos_strength = min(break_distance * 10, 1.0)  # Normalize to 0-1
            
            # Check volume confirmation
            if bos_detected and avg_volume > 0:
                volume_confirmed = current_volume >= (avg_volume * self.volume_threshold)
            
            result = {
                "detected": bos_detected,
                "strength": bos_strength,
                "volume_confirmed": volume_confirmed,
                "resistance_level": recent_highs.iloc[-2] if direction == "long" else None,
                "support_level": recent_lows.iloc[-2] if direction == "short" else None,
                "break_distance": abs(current_price - (recent_highs.iloc[-2] if direction == "long" else recent_lows.iloc[-2]))
            }
            
            if bos_detected:
                logger.info(f"BOS detected for {direction}: strength={bos_strength:.3f}, volume_confirmed={volume_confirmed}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in BOS detection: {e}")
            return {"detected": False, "strength": 0.0, "volume_confirmed": False}
    
    def detect_change_of_character(self, df: pd.DataFrame, direction: str) -> Dict[str, Any]:
        """Detect Change of Character (CHOCH) patterns"""
        try:
            if len(df) < self.choch_lookback + 10:
                logger.warning("Insufficient data for CHOCH analysis")
                return {"detected": False, "strength": 0.0, "volume_confirmed": False}
            
            # Calculate EMA momentum
            df['ema_momentum'] = df['close'].diff()
            df['ema_momentum_ma'] = df['ema_momentum'].rolling(window=5).mean()
            
            # Get recent momentum data
            recent_momentum = df['ema_momentum_ma'].tail(self.choch_lookback)
            current_momentum = recent_momentum.iloc[-1]
            avg_momentum = recent_momentum.mean()
            
            # Check for momentum reversal
            choch_detected = False
            choch_strength = 0.0
            volume_confirmed = False
            
            if direction == "long":
                # Check for bullish CHOCH (momentum turning positive)
                if current_momentum > 0 and avg_momentum < 0:
                    choch_detected = True
                    # Calculate strength based on momentum change
                    momentum_change = (current_momentum - avg_momentum) / abs(avg_momentum) if avg_momentum != 0 else 0
                    choch_strength = min(momentum_change, 1.0)
                    
            elif direction == "short":
                # Check for bearish CHOCH (momentum turning negative)
                if current_momentum < 0 and avg_momentum > 0:
                    choch_detected = True
                    # Calculate strength based on momentum change
                    momentum_change = (avg_momentum - current_momentum) / abs(avg_momentum) if avg_momentum != 0 else 0
                    choch_strength = min(momentum_change, 1.0)
            
            # Check volume confirmation
            if choch_detected and 'volume' in df.columns:
                current_volume = df['volume'].iloc[-1]
                avg_volume = df['volume'].tail(20).mean()
                volume_confirmed = current_volume >= (avg_volume * self.volume_threshold)
            
            result = {
                "detected": choch_detected,
                "strength": choch_strength,
                "volume_confirmed": volume_confirmed,
                "current_momentum": current_momentum,
                "avg_momentum": avg_momentum,
                "momentum_change": abs(current_momentum - avg_momentum)
            }
            
            if choch_detected:
                logger.info(f"CHOCH detected for {direction}: strength={choch_strength:.3f}, volume_confirmed={volume_confirmed}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in CHOCH detection: {e}")
            return {"detected": False, "strength": 0.0, "volume_confirmed": False}
    
    def calculate_signal_strength(self, ema_result: Dict, bos_result: Dict, choch_result: Dict) -> float:
        """Calculate overall signal strength based on all indicators"""
        try:
            # Base strength from EMA crossover
            base_strength = ema_result.get("strength", 0.0)
            
            # Add BOS confirmation
            bos_contribution = 0.0
            if bos_result.get("detected", False):
                bos_contribution = bos_result.get("strength", 0.0) * 0.3  # 30% weight
                if bos_result.get("volume_confirmed", False):
                    bos_contribution *= 1.2  # 20% bonus for volume confirmation
            
            # Add CHOCH confirmation
            choch_contribution = 0.0
            if choch_result.get("detected", False):
                choch_contribution = choch_result.get("strength", 0.0) * 0.3  # 30% weight
                if choch_result.get("volume_confirmed", False):
                    choch_contribution *= 1.2  # 20% bonus for volume confirmation
            
            # Calculate total strength
            total_strength = base_strength + bos_contribution + choch_contribution
            
            # Normalize to 0-1 range
            total_strength = min(max(total_strength, 0.0), 1.0)
            
            logger.info(f"Signal strength calculation: base={base_strength:.3f}, BOS={bos_contribution:.3f}, CHOCH={choch_contribution:.3f}, total={total_strength:.3f}")
            
            return total_strength
            
        except Exception as e:
            logger.error(f"Error calculating signal strength: {e}")
            return 0.0
    
    def calculate_confidence_level(self, signal_strength: float, confirmations: int) -> int:
        """Calculate confidence level (0-5) based on signal strength and confirmations"""
        try:
            # Base confidence from signal strength
            if signal_strength >= 0.9:
                base_confidence = 5
            elif signal_strength >= 0.8:
                base_confidence = 4
            elif signal_strength >= 0.7:
                base_confidence = 3
            elif signal_strength >= 0.6:
                base_confidence = 2
            else:
                base_confidence = 1
            
            # Add confidence for confirmations
            confirmation_bonus = min(confirmations, 2)  # Max 2 bonus points
            
            total_confidence = min(base_confidence + confirmation_bonus, 5)
            
            logger.info(f"Confidence calculation: strength={signal_strength:.3f}, confirmations={confirmations}, confidence={total_confidence}")
            
            return total_confidence
            
        except Exception as e:
            logger.error(f"Error calculating confidence level: {e}")
            return 1
    
    def analyze_market(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Complete market analysis combining all technical indicators"""
        try:
            # Step 1: EMA Crossover Analysis
            ema_result = self.detect_ema_crossover(df)
            
            if ema_result["signal"] == "no_crossover":
                return {
                    "signal": "no_signal",
                    "strength": 0.0,
                    "confidence": 0,
                    "details": ema_result
                }
            
            # Step 2: Break of Structure Analysis
            bos_result = self.detect_break_of_structure(df, ema_result["direction"])
            
            # Step 3: Change of Character Analysis
            choch_result = self.detect_change_of_character(df, ema_result["direction"])
            
            # Step 4: Calculate Overall Signal Strength
            signal_strength = self.calculate_signal_strength(ema_result, bos_result, choch_result)
            
            # Step 5: Calculate Confidence Level
            confirmations = sum([
                bos_result.get("detected", False),
                choch_result.get("detected", False)
            ])
            confidence = self.calculate_confidence_level(signal_strength, confirmations)
            
            # Step 6: Determine Signal Type
            if signal_strength >= self.min_signal_strength and confirmations >= 1:
                signal_type = "confirmed_signal"
            elif ema_result["signal"] != "no_crossover":
                signal_type = "base_signal"
            else:
                signal_type = "no_signal"
            
            result = {
                "signal": signal_type,
                "direction": ema_result["direction"],
                "strength": signal_strength,
                "confidence": confidence,
                "ema_analysis": ema_result,
                "bos_analysis": bos_result,
                "choch_analysis": choch_result,
                "confirmations": confirmations,
                "timestamp": df.index[-1],
                "price": df['close'].iloc[-1]
            }
            
            logger.info(f"Market analysis completed: {signal_type}, strength={signal_strength:.3f}, confidence={confidence}")
            return result
            
        except Exception as e:
            logger.error(f"Error in market analysis: {e}")
            return {
                "signal": "error",
                "strength": 0.0,
                "confidence": 0,
                "error": str(e)
            }

