"""
Telegram Bot Notification Module
Sends formatted trading signals and alerts via Telegram Bot API
"""

import logging
import requests
import json
from typing import Dict, Any, Optional
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DATA_TIMEOUT

logger = logging.getLogger(__name__)

class TelegramBotNotifier:
    """Handles Telegram bot notifications"""
    
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.session = requests.Session()
        self.session.timeout = DATA_TIMEOUT
        
    def send_message(self, text: str, parse_mode: str = "HTML", 
                    disable_web_page_preview: bool = True) -> bool:
        """
        Send message via Telegram Bot API
        
        Args:
            text: Message text (supports HTML formatting)
            parse_mode: Text parsing mode (HTML or Markdown)
            disable_web_page_preview: Disable link previews
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram bot token or chat ID not configured")
            return False
        
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": disable_web_page_preview
            }
            
            response = self.session.post(
                f"{self.base_url}/sendMessage",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    logger.info(f"Telegram message sent successfully: {text[:50]}...")
                    return True
                else:
                    logger.error(f"Telegram API error: {result.get('description', 'Unknown error')}")
                    return False
            else:
                logger.error(f"Telegram API request failed with status {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {e}")
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
            # Format message with HTML
            if signal_data["signal"] == "confirmed_signal":
                emoji = "🚀" if signal_data["direction"] == "long" else "📉"
                title = f"<b>{emoji} {signal_data['direction'].upper()} SIGNAL: {symbol}</b>"
                priority_emoji = "🔥"
            elif signal_data["signal"] == "base_signal":
                emoji = "⚠️" if signal_data["direction"] == "long" else "⚠️"
                title = f"<b>{emoji} {signal_data['direction'].upper()} ALERT: {symbol}</b>"
                priority_emoji = "⚡"
            else:
                logger.warning(f"Unknown signal type: {signal_data['signal']}")
                return False
            
            # Build message
            message_parts = [title]
            
            # Signal details
            message_parts.append(f"<b>Strength:</b> {signal_data['strength']:.1%}")
            message_parts.append(f"<b>Confidence:</b> {signal_data['confidence']}/5 {priority_emoji}")
            
            if signal_data.get("price"):
                message_parts.append(f"<b>Price:</b> ${signal_data['price']:.4f}")
            
            # Add EMA crossover details
            if signal_data.get("ema_analysis"):
                ema_data = signal_data["ema_analysis"]
                if ema_data.get("fast_ema") and ema_data.get("slow_ema"):
                    message_parts.append(f"<b>EMA 9:</b> ${ema_data['fast_ema']:.4f}")
                    message_parts.append(f"<b>EMA 20:</b> ${ema_data['slow_ema']:.4f}")
                    
                    # Calculate EMA separation
                    ema_sep = abs(ema_data['fast_ema'] - ema_data['slow_ema']) / ema_data['slow_ema'] * 100
                    message_parts.append(f"<b>EMA Separation:</b> {ema_sep:.2f}%")
            
            # Add confirmation details with more context
            confirmations = []
            if signal_data.get("bos_analysis", {}).get("detected"):
                bos_data = signal_data["bos_analysis"]
                bos_info = "✅ BOS"
                if bos_data.get("volume_confirmed"):
                    bos_info += " (Volume Confirmed)"
                else:
                    bos_info += " ⚠️ (No Volume)"
                confirmations.append(bos_info)
                
                # Add BOS details
                if bos_data.get("break_distance"):
                    message_parts.append(f"<b>BOS Distance:</b> {bos_data['break_distance']:.4f}")
            
            if signal_data.get("choch_analysis", {}).get("detected"):
                choch_data = signal_data["choch_analysis"]
                choch_info = "✅ CHOCH"
                if choch_data.get("volume_confirmed"):
                    choch_info += " (Volume Confirmed)"
                else:
                    choch_info += " ⚠️ (No Volume)"
                confirmations.append(choch_info)
                
                # Add CHOCH details
                if choch_data.get("momentum_change"):
                    message_parts.append(f"<b>Momentum Change:</b> {choch_data['momentum_change']:.4f}")
            
            if confirmations:
                message_parts.append(f"<b>Confirmations:</b> {' | '.join(confirmations)}")
            
            # Add actionable insights
            message_parts.append("")
            message_parts.append(f"💡 <b>ACTION: {signal_data['direction'].upper()}")
            if signal_data["confidence"] >= 4:
                message_parts.append(" - HIGH CONFIDENCE</b> 🚀")
            elif signal_data["confidence"] >= 3:
                message_parts.append(" - MEDIUM CONFIDENCE</b> ⚡")
            else:
                message_parts.append(" - LOW CONFIDENCE</b> ⚠️")
            
            # Add timestamp
            if signal_data.get("timestamp"):
                timestamp_str = signal_data["timestamp"].strftime("%Y-%m-%d %H:%M:%S UTC")
                message_parts.append(f"<i>Generated: {timestamp_str}</i>")
            
            # Join message parts
            message = "\n".join(message_parts)
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error formatting trading signal for Telegram: {e}")
            return False
    
    def send_market_summary(self, market_data: Dict[str, Any]) -> bool:
        """
        Send market summary with current status
        
        Args:
            market_data: Dictionary containing market analysis results
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            title = "<b>📊 Market Summary</b>"
            message_parts = [title]
            
            # Count signals by type
            signal_counts = {"confirmed": 0, "base": 0, "total": 0}
            for symbol, data in market_data.items():
                if data.get("signal") == "confirmed_signal":
                    signal_counts["confirmed"] += 1
                elif data.get("signal") == "base_signal":
                    signal_counts["base"] += 1
                if data.get("signal") != "no_signal":
                    signal_counts["total"] += 1
            
            # Summary statistics
            message_parts.append(f"<b>Total Signals:</b> {signal_counts['total']}")
            message_parts.append(f"<b>Confirmed:</b> {signal_counts['confirmed']} 🔥")
            message_parts.append(f"<b>Base Alerts:</b> {signal_counts['base']} ⚡")
            
            # List active signals
            if signal_counts["total"] > 0:
                message_parts.append("\n<b>Active Signals:</b>")
                for symbol, data in market_data.items():
                    if data.get("signal") != "no_signal":
                        direction_emoji = "🟢" if data.get("direction") == "long" else "🔴"
                        signal_type = "CONFIRMED" if data.get("signal") == "confirmed_signal" else "BASE"
                        message_parts.append(f"{direction_emoji} {symbol}: {signal_type} {data.get('direction', '').upper()}")
            
            message = "\n".join(message_parts)
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error formatting market summary for Telegram: {e}")
            return False
    
    def send_test_notification(self) -> bool:
        """Send test notification to verify Telegram bot integration"""
        test_message = """🧪 <b>Test Notification</b>

This is a test message from the EMA Crossover Alert Bot to verify Telegram integration.

<b>Features:</b>
✅ Real-time trading signals
✅ Multi-confirmation analysis
✅ iOS Shortcuts integration
✅ Automated market monitoring

<i>Bot is ready for trading signals!</i>"""
        
        return self.send_message(test_message)
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Telegram bot connection and get bot info"""
        if not self.bot_token:
            return {
                "status": "not_configured",
                "message": "Telegram bot token not configured",
                "success": False
            }
        
        try:
            # Get bot info
            response = self.session.get(f"{self.base_url}/getMe")
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    bot_info = result.get("result", {})
                    return {
                        "status": "connected",
                        "message": f"Bot connected: @{bot_info.get('username', 'Unknown')}",
                        "bot_info": bot_info,
                        "success": True
                    }
                else:
                    return {
                        "status": "api_error",
                        "message": f"Telegram API error: {result.get('description', 'Unknown error')}",
                        "success": False
                    }
            else:
                return {
                    "status": "request_failed",
                    "message": f"Request failed with status {response.status_code}",
                    "success": False
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
        logger.info("Telegram bot notifier cleanup completed")

