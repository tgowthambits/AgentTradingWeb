#!/bin/bash

# Start Web UI Server for Trading System
# This script starts the FastAPI backend server

echo "=================================================="
echo "   🚀 Starting Trading System Web UI Server"
echo "=================================================="

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    echo "✅ Activating virtual environment..."
    source .venv/bin/activate
else
    echo "❌ Virtual environment not found! Please run: python -m venv .venv"
    exit 1
fi

# Install UI requirements if needed
echo "📦 Checking UI dependencies..."
pip install -q -r trading_system/ui/requirements.txt

echo ""
echo "🌐 Starting Web UI Server..."
echo "   Dashboard: http://localhost:8000"
echo "   WebSocket: ws://localhost:8000/ws"
echo ""
echo "⚠️  Keep this terminal open!"
echo "   Press Ctrl+C to stop the server"
echo ""

# Start the FastAPI server
cd trading_system/ui/backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

