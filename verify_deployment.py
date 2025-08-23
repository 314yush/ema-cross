#!/usr/bin/env python3
"""
Deployment Verification Script
Verifies all files are ready for Render deployment
"""

import os
import sys

def check_file_exists(filename, required=True):
    """Check if a file exists and optionally verify its size"""
    if os.path.exists(filename):
        size = os.path.getsize(filename)
        print(f"✅ {filename} ({size} bytes)")
        return True
    else:
        if required:
            print(f"❌ {filename} - MISSING!")
            return False
        else:
            print(f"⚠️  {filename} - Not found (optional)")
            return True

def check_file_content(filename, required_content=None):
    """Check if file contains required content"""
    if not os.path.exists(filename):
        return False
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if required_content:
            if required_content in content:
                print(f"   ✅ Contains required content: {required_content}")
                return True
            else:
                print(f"   ❌ Missing required content: {required_content}")
                return False
        
        # Check for empty files
        if len(content.strip()) == 0:
            print(f"   ❌ File is empty!")
            return False
            
        return True
        
    except Exception as e:
        print(f"   ❌ Error reading file: {e}")
        return False

def main():
    """Main verification function"""
    print("🚀 EMA Crossover Bot - Deployment Verification")
    print("=" * 50)
    
    all_good = True
    
    # Check critical files
    print("\n📁 Critical Files:")
    critical_files = [
        "Dockerfile",
        "render.yaml", 
        "requirements.txt",
        "main_bot_cloud.py",
        "config.py",
        "data_fetcher.py",
        "technical_indicators.py",
        "alert_manager.py"
    ]
    
    for filename in critical_files:
        if not check_file_exists(filename):
            all_good = False
    
    # Check Dockerfile specifically
    print("\n🐳 Dockerfile Verification:")
    if check_file_exists("Dockerfile"):
        check_file_content("Dockerfile", "FROM python:3.11-slim")
        check_file_content("Dockerfile", "CMD [\"gunicorn\"")
    
    # Check render.yaml
    print("\n⚙️  Render Configuration:")
    if check_file_exists("render.yaml"):
        check_file_content("render.yaml", "type: web")
        check_file_content("render.yaml", "env: docker")
    
    # Check requirements.txt
    print("\n📦 Dependencies:")
    if check_file_exists("requirements.txt"):
        check_file_content("requirements.txt", "Flask>=")
        check_file_content("requirements.txt", "gunicorn>=")
    
    # Check notifications directory
    print("\n🔔 Notifications Module:")
    if os.path.exists("notifications"):
        print("   ✅ notifications/ directory exists")
        notification_files = [
            "notifications/__init__.py",
            "notifications/ios_shortcuts.py", 
            "notifications/telegram_bot.py",
            "notifications/notification_manager.py"
        ]
        for nf in notification_files:
            check_file_exists(nf)
    else:
        print("   ❌ notifications/ directory missing!")
        all_good = False
    
    # Check .gitignore
    print("\n🔒 Git Configuration:")
    if check_file_exists(".gitignore"):
        check_file_content(".gitignore", "__pycache__")
        check_file_content(".gitignore", ".env")
    
    # Final status
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 ALL CHECKS PASSED! Your bot is ready for Render deployment!")
        print("\n📋 Next steps:")
        print("1. Go to https://dashboard.render.com")
        print("2. Create new Web Service")
        print("3. Connect your GitHub repo: https://github.com/314yush/ema-cross")
        print("4. Deploy!")
        print("\n🌐 Your bot will be available at: https://ema-crossover-bot.onrender.com")
    else:
        print("❌ Some checks failed. Please fix the issues above before deploying.")
        sys.exit(1)

if __name__ == "__main__":
    main()
