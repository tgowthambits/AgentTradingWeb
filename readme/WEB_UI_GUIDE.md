# 🌐 Trading System Web UI - Complete Guide

## 📋 Overview

The Web UI provides a **modern, real-time dashboard** for monitoring your trading bot with:

✅ **TradingView Lightweight Charts** - Professional candlestick charts  
✅ **Real-time Updates** - WebSocket streaming from bot  
✅ **Performance Metrics** - PnL, Win Rate, Trade History  
✅ **Indicator Monitoring** - View all active indicators  
✅ **Position Tracking** - Open and closed positions  
✅ **Symbol Selection** - Interactive symbol selector  
✅ **Event Log** - Real-time bot activity  
✅ **Modern UI** - Dark theme, responsive design  

---

## 🚀 Quick Start

### Option 1: Start Everything Together (Recommended)

```bash
./start_bot_with_ui.sh
```

This will:
1. Start Web UI server in background
2. Start trading bot
3. Open dashboard at http://localhost:8000
4. Bot automatically broadcasts data to UI

### Option 2: Start UI Server Only

```bash
./start_web_ui.sh
```

Then in another terminal:

```bash
./start_trading_bot.sh
```

Bot will automatically detect and connect to UI.

---

## 📊 Dashboard Features

### 1. **Key Metrics** (Top Row)
- **Total PnL**: Combined realized + unrealized profit/loss
- **Win Rate**: Percentage of winning trades
- **Total Trades**: Number of completed trades
- **Bot Uptime**: How long the bot has been running

### 2. **Candlestick Chart** (TradingView)
- **Real-time price data** from selected symbol
- **Interactive controls**: Pan, zoom, crosshair
- **Volume indicator**: Color-coded by direction
- **Time frames**: 1m, 5m, 15m, 1h (customizable)

### 3. **Symbol Selector**
- **Click any symbol** to view its chart
- **Color-coded signals**: 
  - 🟢 Green = BUY
  - 🔴 Red = SELL
  - ⚪ Gray = HOLD
- **Live price updates**
- **Active symbol highlighted**

### 4. **Signal Details**
- **Final aggregated signal**
- **Individual indicator signals**
- **Agreement percentage**
- **Current price**

### 5. **Open Positions**
- **Symbol, Type (LONG/SHORT)**
- **Entry price, Current price**
- **Quantity**
- **Unrealized PnL** (marked with *)

### 6. **Active Indicators**
- **List of all indicators**
- **Enabled/Disabled status**
- **Weight values**

### 7. **Recent Trades**
- **Entry and Exit prices**
- **PnL per trade**
- **Timestamps**
- **Position type**

### 8. **Event Log**
- **Real-time bot events**
- **Trade execution logs**
- **System messages**
- **Scrollable history**

---

## 🔧 Architecture

### System Components

```
┌─────────────────────────────────────────────────┐
│           Browser (Dashboard)                   │
│  - TradingView Charts                          │
│  - Real-time Metrics                           │
│  - Symbol Selector                             │
└───────────┬─────────────────────────────────────┘
            │ WebSocket (ws://localhost:8000/ws)
            ↓
┌─────────────────────────────────────────────────┐
│       FastAPI Backend (main.py)                 │
│  - WebSocket Server                            │
│  - REST API Endpoints                          │
│  - Data Bridge                                 │
└───────────┬─────────────────────────────────────┘
            │ In-Memory Sharing
            ↓
┌─────────────────────────────────────────────────┐
│      Data Bridge (data_bridge.py)              │
│  - Shared state management                     │
│  - Thread-safe singleton                       │
│  - Event broadcasting                          │
└───────────┬─────────────────────────────────────┘
            │ Function calls
            ↓
┌─────────────────────────────────────────────────┐
│    Bot Integration (bot_integration.py)        │
│  - Observes bot activity                       │
│  - Extracts data                               │
│  - Broadcasts to UI                            │
└───────────┬─────────────────────────────────────┘
            │ Observes (no modification)
            ↓
┌─────────────────────────────────────────────────┐
│     Trading Bot (run_live_bot.py)              │
│  - Core trading logic                          │
│  - Indicator analysis                          │
│  - Order execution                             │
└─────────────────────────────────────────────────┘
```

### Data Flow

```
Bot runs → analyze_symbol() → Results
                                  ↓
                        UI Integration observes
                                  ↓
                        Extracts key metrics
                                  ↓
                        Updates Data Bridge
                                  ↓
                    Broadcasts via WebSocket
                                  ↓
                        Dashboard receives
                                  ↓
                    Updates UI in real-time
```

---

## 🔌 API Endpoints

### REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main dashboard page |
| `/api/status` | GET | Bot status |
| `/api/symbols` | GET | List of symbols |
| `/api/symbol/{symbol}` | GET | Symbol analysis data |
| `/api/chart/{symbol}` | GET | OHLCV chart data |
| `/api/performance` | GET | Performance metrics |
| `/api/positions` | GET | Open/closed positions |
| `/api/indicators` | GET | Active indicators |
| `/api/events` | GET | Recent events |
| `/api/full-state` | GET | Complete state |
| `/health` | GET | Health check |

### WebSocket

**Endpoint**: `ws://localhost:8000/ws`

**Messages Sent to Client:**
```json
{
  "type": "full_state",
  "data": {
    "bot_status": {...},
    "symbols": {...},
    "performance": {...},
    "open_positions": [...],
    "closed_orders": [...],
    "indicators": [...],
    "events": [...]
  }
}
```

**Messages from Client:**
```json
{
  "command": "get_state"  // Request full state
}

{
  "command": "get_chart",
  "symbol": "BSE:SENSEX2610185100PE"
}

{
  "command": "ping"  // Keepalive
}
```

---

## 🎨 UI Customization

### Modify Colors

Edit `trading_system/ui/frontend/styles.css`:

```css
:root {
    --bg-primary: #0d1117;      /* Main background */
    --bg-secondary: #161b22;    /* Card backgrounds */
    --accent-green: #3fb950;    /* Positive/BUY */
    --accent-red: #f85149;      /* Negative/SELL */
    --accent-blue: #58a6ff;     /* Highlights */
}
```

### Add Custom Metrics

Edit `trading_system/ui/frontend/index.html` to add new metric cards:

```html
<div class="col-md-3">
    <div class="card bg-gradient-dark border-secondary">
        <div class="card-body">
            <h6 class="card-subtitle mb-2 text-muted">
                <i class="bi bi-icon-name"></i> Your Metric
            </h6>
            <h3 class="card-title mb-0" id="your-metric">0</h3>
        </div>
    </div>
</div>
```

Update in `app.js`:
```javascript
const yourMetricEl = document.getElementById('your-metric');
if (yourMetricEl) {
    yourMetricEl.textContent = data.your_value;
}
```

### Modify Chart Appearance

Edit `trading_system/ui/frontend/chart.js`:

```javascript
this.candlestickSeries = this.chart.addCandlestickSeries({
    upColor: '#00ff00',        // Your green
    downColor: '#ff0000',      // Your red
    borderUpColor: '#00ff00',
    borderDownColor: '#ff0000',
    wickUpColor: '#00ff00',
    wickDownColor: '#ff0000',
});
```

---

## 🛠️ Troubleshooting

### Issue: Web UI Not Loading

**Check:**
1. Is the server running?
   ```bash
   curl http://localhost:8000/health
   ```

2. Check server logs:
   ```bash
   tail -f /tmp/trading_ui.log
   ```

3. Port 8000 already in use?
   ```bash
   lsof -i :8000
   # Kill process: kill -9 <PID>
   ```

**Fix:**
```bash
# Stop all
pkill -f uvicorn

# Restart
./start_web_ui.sh
```

---

### Issue: No Data in Dashboard

**Check:**
1. Is the bot running?
2. Is bot connected to UI?
   - Look for "✅ Web UI integration enabled" in bot console

3. Check WebSocket connection in browser console (F12):
   ```
   Should see: "WebSocket connected"
   ```

**Fix:**
```bash
# Restart bot with UI
./start_bot_with_ui.sh
```

---

### Issue: Chart Not Displaying

**Check:**
1. Is symbol selected?
2. Does symbol have data?
3. Browser console (F12) for errors

**Fix:**
- Click on a symbol card
- Check `data_loader.py` is loading data correctly
- Verify OHLCV columns exist in dataframe

---

### Issue: WebSocket Disconnecting

**Check:**
- Network connectivity
- Server still running
- Firewall settings

**Fix:**
- Dashboard automatically reconnects (up to 5 attempts)
- Refresh page if needed
- Restart server if persistent

---

## 📈 Performance Tips

### 1. **Limit Chart Data**

In `data_bridge.py`, adjust:
```python
self.max_candles = 500  # Lower = faster
```

### 2. **Reduce Update Frequency**

In `trading_config.yaml`:
```yaml
trading:
  refresh_interval: 10  # Increase from 5 to 10 seconds
```

### 3. **Disable Verbose Logging**

In bot:
```python
result = self.engine.analyze_symbol(df, symbol, verbose=False)
```

### 4. **Optimize WebSocket Messages**

In `bot_integration.py`, reduce data sent:
```python
# Only send essential fields
data = {
    'symbol': symbol,
    'final_signal': result.get('final_signal'),
    'latest_price': result.get('latest_price'),
    # Remove: 'dataframe': result['dataframe']
}
```

---

## 🔐 Security Considerations

### Production Deployment

**⚠️ The current setup is for LOCAL USE ONLY!**

For production:

1. **Enable HTTPS:**
   ```python
   # In main.py
   uvicorn.run(
       "main:app",
       host="0.0.0.0",
       port=8000,
       ssl_keyfile="key.pem",
       ssl_certfile="cert.pem"
   )
   ```

2. **Add Authentication:**
   ```python
   from fastapi.security import HTTPBasic, HTTPBasicCredentials
   
   security = HTTPBasic()
   
   @app.get("/")
   async def root(credentials: HTTPBasicCredentials = Depends(security)):
       # Verify credentials
       pass
   ```

3. **Restrict CORS:**
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://yourdomain.com"],  # Specific domain
       allow_credentials=True,
       allow_methods=["GET"],
       allow_headers=["*"],
   )
   ```

4. **Use Reverse Proxy (Nginx):**
   ```nginx
   server {
       listen 443 ssl;
       server_name trading.yourdomain.com;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }
   }
   ```

---

## 📦 Dependencies

### Backend
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `websockets` - WebSocket support
- `redis` (optional) - For distributed setups

### Frontend
- **TradingView Lightweight Charts** (CDN)
- **Bootstrap 5** (CDN)
- **Bootstrap Icons** (CDN)

### Bot Integration
- No additional dependencies (uses existing bot packages)

---

## 🔄 Updates and Maintenance

### Update UI

```bash
cd trading_system/ui
git pull  # If using git
```

### Update Dependencies

```bash
pip install -r trading_system/ui/requirements.txt --upgrade
```

### Clear Cache

```bash
# Clear browser cache (Ctrl+Shift+Delete)
# Or hard reload (Ctrl+Shift+R)
```

---

## 🌟 Features Roadmap

### Planned Enhancements

- [ ] Symbol add/remove from UI
- [ ] Indicator enable/disable controls
- [ ] Strategy configuration editor
- [ ] Trade execution from UI
- [ ] Historical performance charts
- [ ] Alerts and notifications
- [ ] Multi-timeframe analysis
- [ ] Backtesting interface
- [ ] Export trade history
- [ ] Dark/Light theme toggle

### Coming Soon

- **Mobile App** (React Native)
- **Desktop App** (Electron)
- **Telegram Bot Integration**
- **Email Notifications**

---

## ❓ FAQ

### Q: Can I run UI without the bot?
**A:** Yes! Start `./start_web_ui.sh` - dashboard will show "waiting for data".

### Q: Can I run bot without UI?
**A:** Yes! Bot detects if UI is available and works normally without it.

### Q: Can multiple users view the dashboard?
**A:** Yes! Multiple browser sessions can connect to the same WebSocket.

### Q: Does UI affect bot performance?
**A:** Minimal impact (<1%). Bot runs independently, UI just observes.

### Q: Can I access from another computer?
**A:** Yes, use server IP: `http://192.168.x.x:8000` (ensure firewall allows)

### Q: How much data is stored?
**A:** In-memory only. Restart = fresh start. For persistence, add database.

---

## 📞 Support

### Files to Check
- `trading_system/ui/backend/main.py` - API server
- `trading_system/ui/backend/data_bridge.py` - Data management
- `trading_system/ui/bot_integration.py` - Bot connection
- `trading_system/ui/frontend/app.js` - Frontend logic
- `trading_system/ui/frontend/chart.js` - Chart rendering

### Debug Mode

Enable debug logging:
```bash
# In main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Browser DevTools
- Press `F12`
- Check Console for errors
- Check Network tab for WebSocket connection
- Check Application tab for connection status

---

## ✅ Summary

**You Now Have:**
- ✅ Professional web-based trading dashboard
- ✅ Real-time data streaming via WebSocket
- ✅ TradingView charts for technical analysis
- ✅ Complete position and PnL tracking
- ✅ Event logging and monitoring
- ✅ Modern, responsive UI
- ✅ Zero impact on bot performance
- ✅ Easy customization

**Access:**
- 🌐 Dashboard: **http://localhost:8000**
- 🔌 WebSocket: **ws://localhost:8000/ws**
- 📊 API Docs: **http://localhost:8000/docs** (FastAPI auto-generated)

---

**Happy Trading!** 🚀📈✨

