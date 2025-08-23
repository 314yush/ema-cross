"""
iOS Shortcuts Notification Module
Sends webhook notifications to iPhone Shortcuts for native iOS notifications
"""

import logging
import requests
import json
from typing import Dict, Any, Optional
from config import IOS_WEBHOOK_URL, DATA_TIMEOUT

logger = logging.getLogger(__name__)

class IOSShortcutsNotifier:
    """Handles iOS Shortcuts notifications via webhook"""
    
    def __init__(self):
        self.webhook_url = IOS_WEBHOOK_URL
        self.session = requests.Session()
        self.session.timeout = DATA_TIMEOUT
        
    def send_notification(self, message: str, signal_type: str = "alert", 
                         priority: str = "normal", price: Optional[float] = None) -> bool:
        """
        Send notification to iOS Shortcuts
        
        Args:
            message: The notification message
            signal_type: Type of signal (alert, info, warning)
            priority: Priority level (low, normal, high, urgent)
            price: Current price (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.webhook_url:
            logger.warning("iOS webhook URL not configured")
            return False
        
        try:
            # Prepare payload
            payload = {
                "message": message,
                "type": signal_type,
                "priority": priority,
                "timestamp": None,  # Will be set by iOS Shortcuts
                "price": price
            }
            
            # Send webhook
            response = self.session.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info(f"iOS Shortcuts notification sent successfully: {message[:50]}...")
                return True
            else:
                logger.error(f"iOS Shortcuts notification failed with status {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending iOS Shortcuts notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending iOS Shortcuts notification: {e}")
            return False
    
    def send_trading_signal(self, symbol: str, signal_data: Dict[str, Any]) -> bool:
        """
        Send formatted trading signal notification with detailed trading information
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            signal_data: Signal analysis results
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Format message based on signal type
            if signal_data["signal"] == "confirmed_signal":
                emoji = "🚀" if signal_data["direction"] == "long" else "📉"
                message = f"{emoji} {signal_data['direction'].upper()} SIGNAL: {symbol}"
                priority = "high"
            elif signal_data["signal"] == "base_signal":
                emoji = "⚠️" if signal_data["direction"] == "long" else "⚠️"
                message = f"{emoji} {signal_data['direction'].upper()} ALERT: {symbol}"
                priority = "normal"
            else:
                logger.warning(f"Unknown signal type: {signal_data['signal']}")
                return False
            
            # Add signal details
            message += f"\nStrength: {signal_data['strength']:.1%}"
            message += f"\nConfidence: {signal_data['confidence']}/5"
            
            # Add price information
            if signal_data.get("price"):
                message += f"\nPrice: ${signal_data['price']:.4f}"
            
            # Add EMA crossover details
            if signal_data.get("ema_analysis"):
                ema_data = signal_data["ema_analysis"]
                if ema_data.get("fast_ema") and ema_data.get("slow_ema"):
                    message += f"\nEMA 9: ${ema_data['fast_ema']:.4f}"
                    message += f"\nEMA 20: ${ema_data['slow_ema']:.4f}"
                    
                    # Calculate EMA separation
                    ema_sep = abs(ema_data['fast_ema'] - ema_data['slow_ema']) / ema_data['slow_ema'] * 100
                    message += f"\nEMA Separation: {ema_sep:.2f}%"
            
            # Add confirmation details with more context
            confirmations = []
            if signal_data.get("bos_analysis", {}).get("detected"):
                bos_data = signal_data["bos_analysis"]
                bos_info = "BOS"
                if bos_data.get("volume_confirmed"):
                    bos_info += "✅"  # Volume confirmed
                else:
                    bos_info += "⚠️"  # No volume confirmation
                confirmations.append(bos_info)
                
                # Add BOS details
                if bos_data.get("break_distance"):
                    message += f"\nBOS Distance: {bos_data['break_distance']:.4f}"
            
            if signal_data.get("choch_analysis", {}).get("detected"):
                choch_data = signal_data["choch_analysis"]
                choch_info = "CHOCH"
                if choch_data.get("volume_confirmed"):
                    choch_info += "✅"  # Volume confirmed
                else:
                    choch_info += "⚠️"  # No volume confirmation
                confirmations.append(choch_info)
                
                # Add CHOCH details
                if choch_data.get("momentum_change"):
                    message += f"\nMomentum Change: {choch_data['momentum_change']:.4f}"
            
            if confirmations:
                message += f"\nConfirmations: {' | '.join(confirmations)}"
            
            # Add actionable insights
            message += f"\n\n💡 ACTION: {signal_data['direction'].upper()}"
            if signal_data["confidence"] >= 4:
                message += " - HIGH CONFIDENCE"
            elif signal_data["confidence"] >= 3:
                message += " - MEDIUM CONFIDENCE"
            else:
                message += " - LOW CONFIDENCE"
            
            # Add timestamp
            if signal_data.get("timestamp"):
                timestamp_str = signal_data["timestamp"].strftime("%H:%M UTC")
                message += f"\n⏰ {timestamp_str}"
            
            return self.send_notification(
                message=message,
                signal_type="alert",
                priority=priority,
                price=signal_data.get("price")
            )
            
        except Exception as e:
            logger.error(f"Error formatting trading signal for iOS: {e}")
            return False
    
    def send_test_notification(self) -> bool:
        """Send test notification to verify iOS Shortcuts integration"""
        test_message = "🧪 Test notification from EMA Crossover Bot\nThis is a test message to verify iOS Shortcuts integration."
        
        return self.send_notification(
            message=test_message,
            signal_type="info",
            priority="normal"
        )
    
    def test_connection(self) -> Dict[str, Any]:
        """Test iOS Shortcuts webhook connection"""
        if not self.webhook_url:
            return {
                "status": "not_configured",
                "message": "iOS webhook URL not configured",
                "success": False
            }
        
        try:
            # Send a simple test request
            response = self.session.get(self.webhook_url, timeout=5)
            
            return {
                "status": "connected" if response.status_code == 200 else "error",
                "status_code": response.status_code,
                "message": f"Webhook responded with status {response.status_code}",
                "success": response.status_code == 200
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "status": "connection_failed",
                "message": f"Connection failed: {str(e)}",
                "success": False
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "success": False
            }
    
    def cleanup(self):
        """Cleanup resources"""
        if self.session:
            self.session.close()
        logger.info("iOS Shortcuts notifier cleanup completed")

