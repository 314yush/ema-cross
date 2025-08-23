#!/usr/bin/env python3
"""
Keep-Alive Script for EMA Crossover Bot
Pings the bot every minute to keep Render from sleeping
"""

import requests
import time
import datetime

# Bot URL
BOT_URL = "https://ema-cross.onrender.com"

def ping_bot():
    """Ping the bot to keep it awake"""
    try:
        # Try the ping endpoint first (lightweight)
        response = requests.get(f"{BOT_URL}/ping", timeout=10)
        if response.status_code == 200:
            print(f"✅ Ping successful: {response.json().get('message', 'pong')}")
            return True
        else:
            print(f"⚠️  Ping returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Ping failed: {e}")
        return False

def health_check():
    """Perform a health check on the bot"""
    try:
        response = requests.get(f"{BOT_URL}/health", timeout=15)
        if response.status_code == 200:
            data = response.json()
            status = data.get('status', 'unknown')
            uptime = data.get('uptime_seconds', 0)
            print(f"✅ Health check: {status} (uptime: {uptime}s)")
            return True
        else:
            print(f"⚠️  Health check returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check failed: {e}")
        return False

def main():
    """Main keep-alive loop"""
    print("🚀 EMA Crossover Bot - Keep-Alive Script")
    print(f"🌐 Bot URL: {BOT_URL}")
    print("⏰ Pinging every minute to keep bot awake...")
    print("=" * 50)
    
    ping_count = 0
    success_count = 0
    
    try:
        while True:
            ping_count += 1
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            
            print(f"\n[{timestamp}] Ping #{ping_count}")
            
            # Perform ping
            if ping_bot():
                success_count += 1
                
                # Every 5 pings, do a health check
                if ping_count % 5 == 0:
                    print("🔍 Performing health check...")
                    health_check()
            
            # Show success rate
            success_rate = (success_count / ping_count) * 100
            print(f"📊 Success rate: {success_rate:.1f}% ({success_count}/{ping_count})")
            
            # Wait 60 seconds before next ping
            print("⏳ Waiting 60 seconds...")
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Keep-alive script stopped by user")
        print(f"📊 Final stats: {success_count}/{ping_count} successful pings")
        print("💡 Bot should stay awake for ~15 minutes after last ping")

if __name__ == "__main__":
    main()
