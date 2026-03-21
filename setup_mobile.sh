#!/bin/bash

# Face Attendance - Mobile App Quick Setup Script
# This script helps you set up the mobile app with your laptop's IP address

echo "============================================"
echo "Face Attendance Mobile App - Quick Setup"
echo "============================================"
echo ""

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
else
    OS="Unknown"
fi

echo "📱 Step 1: Finding your laptop's IP address..."
echo ""

if [[ "$OS" == "macOS" ]]; then
    # macOS
    IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1)
elif [[ "$OS" == "Linux" ]]; then
    # Linux
    IP=$(hostname -I | awk '{print $1}')
else
    echo "⚠️  Unable to auto-detect IP on this OS"
    echo "Please find your IP manually and update api_config.dart"
    exit 1
fi

if [ -z "$IP" ]; then
    echo "❌ Could not find IP address"
    echo "Please check your network connection"
    exit 1
fi

echo "✅ Found IP address: $IP"
echo ""

# Update the config file
CONFIG_FILE="mobile_app/lib/config/api_config.dart"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Config file not found: $CONFIG_FILE"
    echo "Make sure you're running this script from the face_attendance directory"
    exit 1
fi

echo "📝 Step 2: Updating mobile app configuration..."
echo ""

# Backup original file
cp "$CONFIG_FILE" "${CONFIG_FILE}.backup"

# Update the baseUrl line
sed -i.tmp "s|static const String baseUrl = 'http://.*:8000';|static const String baseUrl = 'http://$IP:8000';|" "$CONFIG_FILE"
rm "${CONFIG_FILE}.tmp"

echo "✅ Updated $CONFIG_FILE"
echo ""

echo "============================================"
echo "✅ Configuration Complete!"
echo "============================================"
echo ""
echo "Your mobile app is configured to connect to:"
echo "  http://$IP:8000"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Start the backend server:"
echo "   cd $(pwd)"
echo "   source .venv/bin/activate"
echo "   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "2. Test connection from your phone's browser:"
echo "   Open: http://$IP:8000/docs"
echo ""
echo "3. Run the Flutter app:"
echo "   cd mobile_app"
echo "   flutter pub get"
echo "   flutter run"
echo ""
echo "4. Make sure your phone and laptop are on the SAME WiFi!"
echo ""
echo "📖 For detailed instructions, see: MOBILE_SETUP_GUIDE.md"
echo ""
