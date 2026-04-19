#!/bin/bash

# Setup Script for Trading System Web UI
# Installs all dependencies and prepares the system

echo "=================================================="
echo "   📦 Setting Up Trading System Web UI"
echo "=================================================="

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check Python version
echo "🐍 Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "   Found: Python $python_version"

# Check/create virtual environment
if [ ! -d ".venv" ]; then
    echo ""
    echo "📦 Creating virtual environment..."
    python -m venv .venv
    echo "   ✅ Virtual environment created"
else
    echo "   ✅ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "✅ Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo ""
# echo "⬆️  Upgrading pip..."
# pip install --upgrade pip

# Install core dependencies
# echo ""
# echo "📦 Installing core trading system dependencies..."
# echo "   (This may take a few minutes...)"
# if [ -f "requirements.txt" ]; then
#     pip install -r requirements.txt --progress-bar on
#     echo "   ✅ Core dependencies installed"
# else
#     echo "   ⚠️  requirements.txt not found, skipping"
# fi

# Install UI dependencies
echo ""
echo "🌐 Installing Web UI dependencies..."
echo "   (Installing FastAPI, Uvicorn, WebSockets...)"
if [ -f "trading_system/ui/requirements.txt" ]; then
    pip install -r trading_system/ui/requirements.txt --progress-bar on
    echo "   ✅ Web UI dependencies installed"
else
    echo "   ❌ UI requirements not found!"
    exit 1
fi

# Make startup scripts executable
echo ""
echo "🔧 Making startup scripts executable..."
chmod +x start_web_ui.sh
chmod +x start_bot_with_ui.sh
chmod +x start_trading_bot.sh
echo "   ✅ Scripts ready"

# Verify installation
echo ""
echo "✅ Verifying installation..."

python -c "
import fastapi
import uvicorn
import websockets
print('   ✅ FastAPI:', fastapi.__version__)
print('   ✅ Uvicorn:', uvicorn.__version__)
print('   ✅ WebSockets:', websockets.__version__)
" 2>/dev/null

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo "   ✅ Setup Complete!"
    echo "=================================================="
    echo ""
    echo "🚀 Quick Start:"
    echo ""
    echo "   Start everything together:"
    echo "   $ ./start_bot_with_ui.sh"
    echo ""
    echo "   Or start separately:"
    echo "   $ ./start_web_ui.sh        # Terminal 1"
    echo "   $ ./start_trading_bot.sh   # Terminal 2"
    echo ""
    echo "📊 Dashboard: http://localhost:8000"
    echo "📖 Docs: WEB_UI_GUIDE.md"
    echo ""
    echo "=================================================="
else
    echo ""
    echo "❌ Verification failed. Please check errors above."
    exit 1
fi

