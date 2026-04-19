#!/bin/bash

# Live Trading Bot Launcher
# Starts the real-time trading bot with auto-refresh

echo "🤖 Starting Live Trading Bot..."
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
fi

# Run the live bot
python trading_system/run_live_bot.py

echo ""
echo "✅ Bot stopped"

