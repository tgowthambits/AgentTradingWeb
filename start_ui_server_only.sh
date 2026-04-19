#!/bin/bash

# Start Web UI Server Only (No Bot)
# Use this when disk space is low or testing UI

echo "=================================================="
echo "   🌐 Starting Web UI Server Only"
echo "=================================================="

cd /home/sham/Desktop/MARKOV_MARKET

# Activate venv
source .venv/bin/activate

# Start server
cd trading_system/ui/backend
echo ""
echo "📊 Dashboard: http://localhost:8000"
echo "🔌 WebSocket: ws://localhost:8000/ws"
echo ""
echo "⚠️  Bot not running - Dashboard will show 'Waiting for data'"
echo "   Start bot separately after freeing disk space"
echo ""
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

