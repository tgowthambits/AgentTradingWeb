# Trading System Web UI

Modern, real-time web dashboard for the Markov Market Trading System.

## 🚀 Quick Start

### Start UI Server + Bot Together

```bash
# From project root
./start_bot_with_ui.sh
```

### Start UI Server Only

```bash
# From project root
./start_web_ui.sh
```

Then open: **http://localhost:8000**

## 📁 Structure

```
ui/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── data_bridge.py       # Data management
│   └── __init__.py
├── frontend/
│   ├── index.html           # Dashboard UI
│   ├── app.js               # Main application
│   ├── chart.js             # TradingView charts
│   └── styles.css           # Styling
├── bot_integration.py       # Bot-UI connector
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## 🔧 Manual Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Server

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Start Bot (in another terminal)

```bash
cd ../..
python run_live_bot.py
```

Bot will automatically detect and connect to UI.

## 🌟 Features

- ✅ Real-time data via WebSocket
- ✅ TradingView Lightweight Charts
- ✅ Live PnL tracking
- ✅ Position monitoring
- ✅ Indicator status
- ✅ Event logging
- ✅ Responsive design

## 📊 Dashboard Components

1. **Key Metrics**: PnL, Win Rate, Trades, Uptime
2. **Candlestick Chart**: Interactive TradingView chart
3. **Symbol Selector**: Click to view different symbols
4. **Signal Details**: Current signals and indicators
5. **Open Positions**: Active trades with unrealized PnL
6. **Recent Trades**: Trade history with realized PnL
7. **Indicators**: Active indicator list
8. **Event Log**: Real-time bot activity

## 🔌 API Endpoints

### REST API
- `GET /` - Dashboard page
- `GET /api/status` - Bot status
- `GET /api/symbols` - Symbol list
- `GET /api/chart/{symbol}` - Chart data
- `GET /api/performance` - Metrics
- `GET /api/positions` - Positions
- `GET /health` - Health check

### WebSocket
- `ws://localhost:8000/ws` - Real-time data stream

## 🎨 Customization

### Colors

Edit `frontend/styles.css`:
```css
:root {
    --bg-primary: #0d1117;
    --accent-green: #3fb950;
    --accent-red: #f85149;
}
```

### Metrics

Add new cards in `frontend/index.html`  
Update logic in `frontend/app.js`

### Charts

Modify `frontend/chart.js` for chart styling

## 🛠️ Development

### Enable Debug Mode

In `backend/main.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Hot Reload

Server auto-reloads on file changes when using `--reload` flag.

### Browser DevTools

Press `F12` to:
- View console logs
- Check WebSocket connection
- Debug JavaScript

## 📈 Performance

### Optimization Tips

1. **Limit candles**: Adjust `max_candles` in `data_bridge.py`
2. **Reduce updates**: Increase `refresh_interval` in config
3. **Disable verbose**: Set `verbose=False` in bot

### Resource Usage

- **CPU**: <5% (idle), <15% (active)
- **Memory**: ~100MB
- **Network**: <10KB/s per client

## 🔐 Security

**⚠️ Current setup is for LOCAL USE only!**

For production:
1. Enable HTTPS
2. Add authentication
3. Restrict CORS
4. Use reverse proxy (Nginx)

See `WEB_UI_GUIDE.md` for details.

## 🐛 Troubleshooting

### Server won't start
```bash
# Check port availability
lsof -i :8000

# Kill existing process
kill -9 <PID>
```

### No data in dashboard
- Ensure bot is running
- Check WebSocket connection (browser console)
- Verify bot shows "Web UI integration enabled"

### Chart not displaying
- Click on a symbol
- Check browser console for errors
- Verify data has OHLCV columns

## 📚 Documentation

See **[WEB_UI_GUIDE.md](../../WEB_UI_GUIDE.md)** for comprehensive guide.

## 🚀 Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Uvicorn** - Lightning-fast ASGI server
- **WebSockets** - Real-time communication

### Frontend
- **TradingView Lightweight Charts** - Professional charting
- **Bootstrap 5** - Responsive UI framework
- **Vanilla JavaScript** - No heavy frameworks

### Integration
- **Data Bridge** - Thread-safe data sharing
- **Bot Integration** - Non-invasive observing

## 📞 Support

Check logs:
```bash
# Server logs
tail -f /tmp/trading_ui.log

# Bot output
# (visible in bot terminal)
```

Enable debug:
```python
# In main.py
log_level="debug"
```

## ✅ Checklist

- [ ] Install dependencies
- [ ] Start server
- [ ] Open dashboard
- [ ] Start bot
- [ ] Verify connection
- [ ] Select symbol
- [ ] View chart
- [ ] Monitor positions

## 🎯 Next Steps

1. **Start the system**: `./start_bot_with_ui.sh`
2. **Open dashboard**: http://localhost:8000
3. **Monitor trades**: Watch real-time updates
4. **Customize**: Edit frontend files
5. **Deploy**: Follow security guidelines

---

**Built with ❤️ for Markov Market Trading System**

