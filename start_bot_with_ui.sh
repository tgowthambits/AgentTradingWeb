#!/bin/bash

# Start Trading Bot with Web UI
# This script starts both the Web UI server and the trading bot

echo "=================================================="
echo "   🚀 Starting Trading System with Web UI"
echo "=================================================="

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -f ".venv/bin/activate" ]; then
    echo "❌ Virtual environment not found! Please run: python -m venv .venv"
    exit 1
fi

echo "✅ Activating virtual environment..."
source .venv/bin/activate

# Install UI requirements
echo "📦 Installing UI dependencies..."
pip install -q -r trading_system/ui/requirements.txt

echo ""
echo "🌐 Starting Web UI Server in background..."
cd trading_system/ui/backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/trading_ui.log 2>&1 &
UI_PID=$!
cd ../../..

echo "   ✅ Web UI Server started (PID: $UI_PID)"
echo "   📊 Dashboard: http://localhost:8000"
echo "   🔌 WebSocket: ws://localhost:8000/ws"
echo "   📄 Logs: /tmp/trading_ui.log"

# Wait for server to start
echo ""
echo "⏳ Waiting for server to initialize..."
sleep 3

echo ""
echo "🤖 Starting Trading Bot..."
echo "   Bot will broadcast data to Web UI automatically"
echo ""
echo "=================================================="
echo ""

# Start the trading bot
python trading_system/run_live_bot.py

# Cleanup on exit
echo ""
echo "🛑 Stopping Web UI Server..."
kill $UI_PID 2>/dev/null
echo "✅ Cleanup complete"

