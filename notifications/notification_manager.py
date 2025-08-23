"""
Unified Notification Manager
Coordinates iOS Shortcuts and Telegram notifications with fallback strategies
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from notifications.ios_shortcuts import IOSShortcutsNotifier
from notifications.telegram_bot import TelegramBotNotifier
from config import NOTIFICATION_COOLDOWN, MAX_ALERT_HISTORY

logger = logging.getLogger(__name__)

class NotificationManager:
    """Manages all notification channels with fallback strategies"""
    
    def __init__(self):
        self.ios_notifier = IOSShortcutsNotifier()
        self.telegram_notifier = TelegramBotNotifier()
        
        # Notification history and cooldown tracking
        self.alert_history = []
        self.symbol_cooldowns = {}  # Track cooldowns per symbol
        self.notification_cooldown = NOTIFICATION_COOLDOWN
        
    def send_notification(self, message: str, symbol: str = None, 
                         signal_type: str = "alert", priority: str = "normal",
                         price: Optional[float] = None) -> Dict[str, Any]:
        """
        Send notification through all available channels
        
        Args:
            message: Notification message
            symbol: Trading symbol (for cooldown tracking)
            signal_type: Type of signal
            priority: Priority level
            price: Current price
            
        Returns:
            Dict with delivery status for each channel
        """
        # Check cooldown if symbol is provided
        if symbol and self._is_in_cooldown(symbol):
            logger.info(f"Notification for {symbol} is in cooldown period")
            return {
                "ios": {"sent": False, "reason": "cooldown"},
                "telegram": {"sent": False, "reason": "cooldown"}
            }
        
        # Send notifications simultaneously to both channels
        ios_result = self.ios_notifier.send_notification(
            message, signal_type, priority, price
        )
        
        telegram_result = self.telegram_notifier.send_notification(
            message, signal_type, priority, price
        )
        
        # Record in history
        if symbol:
            self._record_notification(symbol, signal_type, priority)
        
        # Return results
        return {
            "ios": {"sent": ios_result, "reason": "success" if ios_result else "failed"},
            "telegram": {"sent": telegram_result, "reason": "success" if telegram_result else "failed"}
        }
    
    def send_trading_signal(self, symbol: str, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send formatted trading signal through all channels
        
        Args:
            symbol: Trading symbol
            signal_data: Signal analysis results
            
        Returns:
            Dict with delivery status for each channel
        """
        # Check cooldown
        if self._is_in_cooldown(symbol):
            logger.info(f"Trading signal for {symbol} is in cooldown period")
            return {
                "ios": {"sent": False, "reason": "cooldown"},
                "telegram": {"sent": False, "reason": "failed"}
            }
        
        # Send to both channels
        ios_result = self.ios_notifier.send_trading_signal(symbol, signal_data)
        telegram_result = self.telegram_notifier.send_trading_signal(symbol, signal_data)
        
        # Record in history
        self._record_notification(symbol, "trading_signal", "high" if signal_data.get("signal") == "confirmed_signal" else "normal")
        
        return {
            "ios": {"sent": ios_result, "reason": "success" if ios_result else "failed"},
            "telegram": {"sent": telegram_result, "reason": "success" if telegram_result else "failed"}
        }
    
    def send_market_summary(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send market summary through all channels
        
        Args:
            market_data: Market analysis results
            
        Returns:
            Dict with delivery status for each channel
        """
        # Send to both channels
        ios_result = self.ios_notifier.send_notification(
            "📊 Market summary available. Check Telegram for detailed view.",
            "info", "normal"
        )
        
        telegram_result = self.telegram_notifier.send_market_summary(market_data)
        
        return {
            "ios": {"sent": ios_result, "reason": "success" if ios_result else "failed"},
            "telegram": {"sent": telegram_result, "reason": "success" if telegram_result else "failed"}
        }
    
    def send_test_notifications(self) -> Dict[str, Any]:
        """Send test notifications to verify all channels"""
        logger.info("Sending test notifications to all channels")
        
        # Send test notifications
        ios_result = self.ios_notifier.send_test_notification()
        telegram_result = self.telegram_notifier.send_test_notification()
        
        return {
            "ios": {"sent": ios_result, "reason": "success" if ios_result else "failed"},
            "telegram": {"sent": telegram_result, "reason": "success" if telegram_result else "failed"}
        }
    
    def test_all_connections(self) -> Dict[str, Any]:
        """Test connections for all notification channels"""
        logger.info("Testing notification channel connections")
        
        ios_status = self.ios_notifier.test_connection()
        telegram_status = self.telegram_notifier.test_connection()
        
        return {
            "ios": ios_status,
            "telegram": telegram_status,
            "overall_status": "healthy" if (ios_status.get("success") or telegram_status.get("success")) else "unhealthy"
        }
    
    def get_notification_status(self) -> Dict[str, Any]:
        """Get comprehensive notification system status"""
        # Test connections
        connection_status = self.test_all_connections()
        
        # Get cooldown information
        active_cooldowns = []
        for symbol, cooldown_time in self.symbol_cooldowns.items():
            if cooldown_time > datetime.now():
                remaining = cooldown_time - datetime.now()
                active_cooldowns.append({
                    "symbol": symbol,
                    "remaining_seconds": int(remaining.total_seconds())
                })
        
        # Get recent notification history
        recent_notifications = self.alert_history[-10:] if self.alert_history else []
        
        return {
            "connections": connection_status,
            "active_cooldowns": active_cooldowns,
            "recent_notifications": recent_notifications,
            "total_notifications": len(self.alert_history),
            "cooldown_period_seconds": self.notification_cooldown
        }
    
    def _is_in_cooldown(self, symbol: str) -> bool:
        """Check if a symbol is currently in cooldown period"""
        if symbol not in self.symbol_cooldowns:
            return False
        
        cooldown_time = self.symbol_cooldowns[symbol]
        return datetime.now() < cooldown_time
    
    def _record_notification(self, symbol: str, signal_type: str, priority: str):
        """Record notification in history and set cooldown"""
        # Add to history
        notification_record = {
            "timestamp": datetime.now(),
            "symbol": symbol,
            "type": signal_type,
            "priority": priority
        }
        
        self.alert_history.append(notification_record)
        
        # Limit history size
        if len(self.alert_history) > MAX_ALERT_HISTORY:
            self.alert_history = self.alert_history[-MAX_ALERT_HISTORY:]
        
        # Set cooldown
        cooldown_end = datetime.now() + timedelta(seconds=self.notification_cooldown)
        self.symbol_cooldowns[symbol] = cooldown_end
        
        logger.info(f"Notification recorded for {symbol}, cooldown until {cooldown_end}")
    
    def clear_cooldown(self, symbol: str) -> bool:
        """Clear cooldown for a specific symbol (for testing purposes)"""
        if symbol in self.symbol_cooldowns:
            del self.symbol_cooldowns[symbol]
            logger.info(f"Cooldown cleared for {symbol}")
            return True
        return False
    
    def get_symbol_cooldown_status(self, symbol: str) -> Dict[str, Any]:
        """Get cooldown status for a specific symbol"""
        if symbol not in self.symbol_cooldowns:
            return {
                "symbol": symbol,
                "in_cooldown": False,
                "remaining_seconds": 0
            }
        
        cooldown_time = self.symbol_cooldowns[symbol]
        if datetime.now() >= cooldown_time:
            # Cooldown expired, remove it
            del self.symbol_cooldowns[symbol]
            return {
                "symbol": symbol,
                "in_cooldown": False,
                "remaining_seconds": 0
            }
        
        remaining = cooldown_time - datetime.now()
        return {
            "symbol": symbol,
            "in_cooldown": True,
            "remaining_seconds": int(remaining.total_seconds()),
            "cooldown_until": cooldown_time.isoformat()
        }
    
    def cleanup(self):
        """Cleanup all notification resources"""
        self.ios_notifier.cleanup()
        self.telegram_notifier.cleanup()
        logger.info("Notification manager cleanup completed")

