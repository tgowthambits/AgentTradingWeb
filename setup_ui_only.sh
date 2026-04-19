#!/bin/bash

# Quick Setup - UI Dependencies Only
# Use this if core dependencies are already installed

echo "=================================================="
echo "   ⚡ Quick UI Setup (Dependencies Only)"
echo "=================================================="

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    echo "✅ Activating virtual environment..."
    source .venv/bin/activate
else
    echo "❌ Virtual environment not found! Run: python -m venv .venv"
    exit 1
fi

# Install UI dependencies only
echo ""
echo "🌐 Installing Web UI dependencies..."
echo ""

pip install -r trading_system/ui/requirements.txt

echo ""
echo "=================================================="
echo "   ✅ UI Dependencies Installed!"
echo "=================================================="
echo ""
echo "🚀 Ready to start:"
echo "   $ ./start_bot_with_ui.sh"
echo ""

