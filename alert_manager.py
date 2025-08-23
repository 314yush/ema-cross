"""
Alert Manager Module
Processes trading signals and manages cooldowns to prevent signal spam
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from notifications.notification_manager import NotificationManager
from config import (
    BASE_SIGNAL_COOLDOWN, CONFIRMED_SIGNAL_COOLDOWN,
    MIN_SIGNAL_STRENGTH
)

logger = logging.getLogger(__name__)

class AlertManager:
    """Manages trading signal alerts and cooldowns"""
    
    def __init__(self):
        self.notification_manager = NotificationManager()
        
        # Signal tracking
        self.signal_history = []
        self.active_signals = {}  # Current active signals per symbol
        self.signal_cooldowns = {}  # Cooldown tracking per symbol
        
        # Cooldown periods (in minutes)
        self.base_cooldown = BASE_SIGNAL_COOLDOWN
        self.confirmed_cooldown = CONFIRMED_SIGNAL_COOLDOWN
        
        # Signal filtering
        self.min_signal_strength = MIN_SIGNAL_STRENGTH
        
    def process_signal(self, symbol: str, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a trading signal and determine if alert should be sent
        
        Args:
            symbol: Trading symbol
            signal_data: Signal analysis results
            
        Returns:
            Dict with processing results and alert status
        """
        try:
            # Validate signal data
            if not self._validate_signal_data(signal_data):
                return {
                    "processed": False,
                    "alert_sent": False,
                    "reason": "invalid_signal_data"
                }
            
            # Check if signal meets minimum strength requirement
            if signal_data.get("strength", 0) < self.min_signal_strength:
                return {
                    "processed": False,
                    "alert_sent": False,
                    "reason": "insufficient_strength",
                    "strength": signal_data.get("strength", 0)
                }
            
            # Check cooldown
            cooldown_status = self._check_cooldown(symbol, signal_data)
            if cooldown_status["in_cooldown"]:
                return {
                    "processed": True,
                    "alert_sent": False,
                    "reason": "cooldown",
                    "cooldown_remaining": cooldown_status["remaining_seconds"]
                }
            
            # Determine if this is a new or updated signal
            signal_update = self._analyze_signal_update(symbol, signal_data)
            
            # Send alert if conditions are met
            alert_sent = False
            if signal_update["should_alert"]:
                alert_result = self._send_alert(symbol, signal_data)
                alert_sent = alert_result["success"]
                
                if alert_sent:
                    # Set cooldown based on signal type
                    self._set_cooldown(symbol, signal_data)
                    
                    # Update active signals
                    self._update_active_signals(symbol, signal_data)
                    
                    # Record in history
                    self._record_signal(symbol, signal_data, alert_result)
            
            return {
                "processed": True,
                "alert_sent": alert_sent,
                "signal_update": signal_update,
                "alert_result": alert_result if alert_sent else None,
                "cooldown_set": alert_sent
            }
            
        except Exception as e:
            logger.error(f"Error processing signal for {symbol}: {e}")
            return {
                "processed": False,
                "alert_sent": False,
                "reason": "processing_error",
                "error": str(e)
            }
    
    def _validate_signal_data(self, signal_data: Dict[str, Any]) -> bool:
        """Validate signal data structure and required fields"""
        required_fields = ["signal", "direction", "strength", "confidence"]
        
        for field in required_fields:
            if field not in signal_data:
                logger.warning(f"Missing required field in signal data: {field}")
                return False
        
        # Validate signal type
        valid_signals = ["base_signal", "confirmed_signal", "no_signal"]
        if signal_data["signal"] not in valid_signals:
            logger.warning(f"Invalid signal type: {signal_data['signal']}")
            return False
        
        # Validate direction
        valid_directions = ["long", "short"]
        if signal_data["direction"] not in valid_directions:
            logger.warning(f"Invalid direction: {signal_data['direction']}")
            return False
        
        # Validate strength and confidence ranges
        if not (0 <= signal_data["strength"] <= 1):
            logger.warning(f"Invalid strength value: {signal_data['strength']}")
            return False
        
        if not (0 <= signal_data["confidence"] <= 5):
            logger.warning(f"Invalid confidence value: {signal_data['confidence']}")
            return False
        
        return True
    
    def _check_cooldown(self, symbol: str, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if symbol is currently in cooldown period"""
        if symbol not in self.signal_cooldowns:
            return {"in_cooldown": False, "remaining_seconds": 0}
        
        cooldown_info = self.signal_cooldowns[symbol]
        cooldown_end = cooldown_info["end_time"]
        
        if datetime.now() >= cooldown_end:
            # Cooldown expired, remove it
            del self.signal_cooldowns[symbol]
            return {"in_cooldown": False, "remaining_seconds": 0}
        
        remaining = cooldown_end - datetime.now()
        return {
            "in_cooldown": True,
            "remaining_seconds": int(remaining.total_seconds()),
            "cooldown_until": cooldown_end.isoformat()
        }
    
    def _analyze_signal_update(self, symbol: str, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze if signal is new, updated, or unchanged"""
        if symbol not in self.active_signals:
            return {
                "type": "new_signal",
                "should_alert": True,
                "previous_signal": None
            }
        
        previous_signal = self.active_signals[symbol]
        
        # Check if signal has changed significantly
        if (previous_signal["signal"] != signal_data["signal"] or
            previous_signal["direction"] != signal_data["direction"] or
            abs(previous_signal["strength"] - signal_data["strength"]) > 0.1 or
            previous_signal["confidence"] != signal_data["confidence"]):
            
            return {
                "type": "signal_update",
                "should_alert": True,
                "previous_signal": previous_signal,
                "changes": {
                    "signal_type": previous_signal["signal"] != signal_data["signal"],
                    "direction": previous_signal["direction"] != signal_data["direction"],
                    "strength": abs(previous_signal["strength"] - signal_data["strength"]),
                    "confidence": previous_signal["confidence"] != signal_data["confidence"]
                }
            }
        
        return {
            "type": "no_change",
            "should_alert": False,
            "previous_signal": previous_signal
        }
    
    def _send_alert(self, symbol: str, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send trading signal alert through notification system"""
        try:
            # Send trading signal notification
            result = self.notification_manager.send_trading_signal(symbol, signal_data)
            
            # Log alert details
            logger.info(f"Alert sent for {symbol}: {signal_data['signal']} {signal_data['direction']} "
                       f"(strength: {signal_data['strength']:.3f}, confidence: {signal_data['confidence']})")
            
            return {
                "success": any(r["sent"] for r in result.values()),
                "notification_results": result,
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error sending alert for {symbol}: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now()
            }
    
    def _set_cooldown(self, symbol: str, signal_data: Dict[str, Any]):
        """Set cooldown period based on signal type"""
        if signal_data["signal"] == "confirmed_signal":
            cooldown_minutes = self.confirmed_cooldown
        else:
            cooldown_minutes = self.base_cooldown
        
        cooldown_end = datetime.now() + timedelta(minutes=cooldown_minutes)
        
        self.signal_cooldowns[symbol] = {
            "end_time": cooldown_end,
            "duration_minutes": cooldown_minutes,
            "signal_type": signal_data["signal"]
        }
        
        logger.info(f"Cooldown set for {symbol}: {cooldown_minutes} minutes until {cooldown_end}")
    
    def _update_active_signals(self, symbol: str, signal_data: Dict[str, Any]):
        """Update active signals tracking"""
        self.active_signals[symbol] = {
            "signal": signal_data["signal"],
            "direction": signal_data["direction"],
            "strength": signal_data["strength"],
            "confidence": signal_data["confidence"],
            "timestamp": datetime.now(),
            "price": signal_data.get("price"),
            "confirmations": signal_data.get("confirmations", 0)
        }
    
    def _record_signal(self, symbol: str, signal_data: Dict[str, Any], alert_result: Dict[str, Any]):
        """Record signal in history"""
        record = {
            "timestamp": datetime.now(),
            "symbol": symbol,
            "signal_type": signal_data["signal"],
            "direction": signal_data["direction"],
            "strength": signal_data["strength"],
            "confidence": signal_data["confidence"],
            "price": signal_data.get("price"),
            "confirmations": signal_data.get("confirmations", 0),
            "alert_sent": alert_result["success"],
            "notification_results": alert_result.get("notification_results", {})
        }
        
        self.signal_history.append(record)
        
        # Limit history size
        if len(self.signal_history) > 1000:
            self.signal_history = self.signal_history[-1000:]
    
    def get_signal_status(self, symbol: str = None) -> Dict[str, Any]:
        """Get current signal status for a symbol or all symbols"""
        if symbol:
            # Return status for specific symbol
            active_signal = self.active_signals.get(symbol)
            cooldown_info = self.signal_cooldowns.get(symbol)
            
            return {
                "symbol": symbol,
                "active_signal": active_signal,
                "cooldown": cooldown_info,
                "in_cooldown": cooldown_info is not None and datetime.now() < cooldown_info["end_time"]
            }
        else:
            # Return status for all symbols
            return {
                "active_signals": self.active_signals,
                "cooldowns": self.signal_cooldowns,
                "total_active": len(self.active_signals),
                "total_in_cooldown": len([c for c in self.signal_cooldowns.values() 
                                        if datetime.now() < c["end_time"]])
            }
    
    def get_signal_history(self, symbol: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get signal history, optionally filtered by symbol"""
        if symbol:
            filtered_history = [record for record in self.signal_history if record["symbol"] == symbol]
            return filtered_history[-limit:] if limit else filtered_history
        else:
            return self.signal_history[-limit:] if limit else self.signal_history
    
    def clear_cooldown(self, symbol: str) -> bool:
        """Clear cooldown for a specific symbol (for testing purposes)"""
        if symbol in self.signal_cooldowns:
            del self.signal_cooldowns[symbol]
            logger.info(f"Cooldown cleared for {symbol}")
            return True
        return False
    
    def clear_all_cooldowns(self) -> int:
        """Clear all active cooldowns (for testing purposes)"""
        count = len(self.signal_cooldowns)
        self.signal_cooldowns.clear()
        logger.info(f"Cleared {count} cooldowns")
        return count
    
    def cleanup(self):
        """Cleanup resources"""
        self.notification_manager.cleanup()
        logger.info("Alert manager cleanup completed")

