#!/bin/bash

# EMA Crossover Bot Deployment Script
# This script prepares the bot for production deployment

set -e

echo "🚀 Preparing EMA Crossover Bot for production deployment..."

# Check if we're in the right directory
if [ ! -f "main_bot_cloud.py" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Clean up development files
echo "🧹 Cleaning up development files..."
rm -rf __pycache__/
rm -rf venv/
rm -f bot.log
rm -f alert_history.json
rm -f start_bot.sh
rm -f start_bot_mac.sh
rm -f test_bot.py
rm -f requirements-compatible.txt

# Check if .env file exists and warn about it
if [ -f ".env" ]; then
    echo "⚠️  Warning: .env file found. Make sure it's not committed to Git!"
    echo "   Your .env file should contain your production secrets."
fi

# Verify production files exist
echo "✅ Verifying production files..."
required_files=("main_bot_cloud.py" "config.py" "data_fetcher.py" "technical_indicators.py" "alert_manager.py" "notifications/" "requirements.txt" "Dockerfile" "render.yaml" ".gitignore" "README.md")

for file in "${required_files[@]}"; do
    if [ -e "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file (missing)"
        exit 1
    fi
done

# Test Python imports
echo "🐍 Testing Python imports..."
python3 -c "
try:
    from main_bot_cloud import app
    from config import *
    from data_fetcher import DataFetcher
    from technical_indicators import TechnicalIndicators
    from alert_manager import AlertManager
    from notifications.notification_manager import NotificationManager
    print('✅ All imports successful')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📁 Initializing Git repository..."
    git init
    git add .
    git commit -m "Initial commit: EMA Crossover Bot production ready"
else
    echo "📁 Git repository already exists"
fi

echo ""
echo "🎉 Production preparation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Add your GitHub remote: git remote add origin https://github.com/314yush/ema-cross.git"
echo "2. Push to GitHub: git push -u origin main"
echo "3. Connect your GitHub repo to Render.com"
echo "4. Set environment variables in Render dashboard"
echo ""
echo "🔑 Required environment variables for Render:"
echo "   - IOS_WEBHOOK_URL"
echo "   - TELEGRAM_BOT_TOKEN"
echo "   - TELEGRAM_CHAT_ID"
echo "   - BINANCE_API_KEY (optional)"
echo "   - BINANCE_SECRET_KEY (optional)"
echo ""
echo "🚀 Your bot will be available at: https://ema-crossover-bot.onrender.com"
