"""
FastAPI Backend for Trading System Web UI
Provides REST API and WebSocket endpoints for real-time data
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json
from typing import List, Dict, Any
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_bridge import data_bridge

# Initialize FastAPI app
app = FastAPI(
    title="Trading System UI API",
    description="Real-time trading bot monitoring and control",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get paths
UI_DIR = Path(__file__).parent.parent
FRONTEND_DIR = UI_DIR / "frontend"
STATIC_DIR = UI_DIR / "static"

# Mount static files if directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ========== HTTP Endpoints ==========

@app.get("/")
async def root():
    """Serve the main dashboard page."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return HTMLResponse("<h1>Trading System UI</h1><p>Frontend not found. Please check frontend directory.</p>")


@app.get("/styles.css")
async def get_styles():
    """Serve CSS file."""
    css_file = FRONTEND_DIR / "styles.css"
    if css_file.exists():
        return FileResponse(str(css_file), media_type="text/css")
    raise HTTPException(status_code=404, detail="CSS file not found")


@app.get("/chart.js")
async def get_chart_js():
    """Serve chart.js file."""
    js_file = FRONTEND_DIR / "chart.js"
    if js_file.exists():
        return FileResponse(str(js_file), media_type="application/javascript")
    raise HTTPException(status_code=404, detail="chart.js not found")


@app.get("/app.js")
async def get_app_js():
    """Serve app.js file."""
    js_file = FRONTEND_DIR / "app.js"
    if js_file.exists():
        return FileResponse(str(js_file), media_type="application/javascript")
    raise HTTPException(status_code=404, detail="app.js not found")


@app.get("/api/status")
async def get_status():
    """Get current bot status."""
    return {
        "status": "online",
        "bot": data_bridge.bot_status,
        "timestamp": data_bridge.bot_status.get('last_update')
    }


@app.post("/api/update/bot-status")
async def update_bot_status(status: Dict[str, Any]):
    """Update bot status (called by bot)."""
    data_bridge.update_bot_status(status)
    return {"status": "ok"}


@app.post("/api/update/symbol")
async def update_symbol(data: Dict[str, Any]):
    """Update symbol data (called by bot)."""
    symbol = data.get('symbol')
    if symbol:
        data_bridge.update_symbol_analysis(symbol, data)
        # Broadcast to WebSocket clients
        await data_bridge.broadcast({
            'type': 'symbol_update',
            'symbol': symbol,
            'data': data
        })
    return {"status": "ok"}


@app.post("/api/update/performance")
async def update_performance(metrics: Dict[str, Any]):
    """Update performance metrics (called by bot)."""
    data_bridge.update_performance(metrics)
    return {"status": "ok"}


@app.post("/api/update/positions")
async def update_positions(positions: Dict[str, Any]):
    """Update positions (called by bot)."""
    open_pos = positions.get('open', [])
    closed = positions.get('closed', [])
    data_bridge.update_positions(open_pos, closed)
    
    # Broadcast position updates to all clients
    await data_bridge.broadcast({
        'type': 'positions_update',
        'open_positions': open_pos,
        'closed_orders': closed
    })
    
    return {"status": "ok"}


@app.post("/api/update/indicators")
async def update_indicators(indicators: List[Dict[str, Any]]):
    """Update indicators list (called by bot)."""
    data_bridge.set_indicators(indicators)
    return {"status": "ok"}


@app.get("/api/symbols")
async def get_symbols():
    """Get list of active symbols."""
    return {
        "symbols": data_bridge.get_symbols(),
        "count": len(data_bridge.get_symbols())
    }


@app.get("/api/symbol/{symbol}")
async def get_symbol_data(symbol: str):
    """Get latest analysis data for a symbol."""
    if symbol not in data_bridge.symbol_data:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    
    return {
        "symbol": symbol,
        "data": data_bridge.symbol_data[symbol]
    }


@app.get("/api/chart/{symbol}")
async def get_chart_data(symbol: str):
    """Get OHLCV chart data for a symbol."""
    chart_data = data_bridge.get_chart_data(symbol)
    
    if not chart_data:
        raise HTTPException(status_code=404, detail=f"No chart data for {symbol}")
    
    return {
        "symbol": symbol,
        "data": chart_data,
        "count": len(chart_data)
    }


@app.get("/api/performance")
async def get_performance():
    """Get performance metrics."""
    return {
        "metrics": data_bridge.performance,
        "positions": {
            "open": len(data_bridge.open_positions),
            "closed": len(data_bridge.closed_orders)
        }
    }


@app.get("/api/positions")
async def get_positions():
    """Get open positions and recent closed orders."""
    return {
        "open": data_bridge.open_positions,
        "closed": data_bridge.closed_orders[-20:]  # Last 20
    }


@app.get("/api/indicators")
async def get_indicators():
    """Get list of active indicators."""
    return {
        "indicators": data_bridge.indicators,
        "count": len(data_bridge.indicators)
    }


@app.get("/api/events")
async def get_events(limit: int = 50):
    """Get recent events."""
    events = list(data_bridge.events)[-limit:]
    return {
        "events": events,
        "count": len(events)
    }


@app.get("/api/full-state")
async def get_full_state():
    """Get complete current state."""
    return data_bridge.get_full_state()


# ========== WebSocket Endpoint ==========

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time data streaming.
    
    Message types sent to client:
    - full_state: Complete state on connection
    - update: Incremental updates
    - trade: Trade events
    - error: Error messages
    """
    await websocket.accept()
    data_bridge.register_connection(websocket)
    
    try:
        # Send initial full state
        full_state = data_bridge.get_full_state()
        await websocket.send_json(full_state)
        
        # Keep connection alive and listen for client messages
        while True:
            try:
                # Wait for messages from client (with timeout)
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # Handle client commands
                try:
                    data = json.loads(message)
                    command = data.get('command')
                    
                    if command == 'get_state':
                        await websocket.send_json(data_bridge.get_full_state())
                    
                    elif command == 'get_chart':
                        symbol = data.get('symbol')
                        if symbol:
                            chart_data = data_bridge.get_chart_data(symbol)
                            await websocket.send_json({
                                'type': 'chart_data',
                                'symbol': symbol,
                                'data': chart_data
                            })
                    
                    elif command == 'ping':
                        await websocket.send_json({'type': 'pong'})
                    
                except json.JSONDecodeError:
                    await websocket.send_json({
                        'type': 'error',
                        'message': 'Invalid JSON'
                    })
            
            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_json({'type': 'ping'})
                except:
                    break
    
    except WebSocketDisconnect:
        print("Client disconnected normally")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        data_bridge.unregister_connection(websocket)


# ========== Control Endpoints (Future) ==========

@app.post("/api/control/start")
async def start_bot():
    """Start the trading bot (if not running)."""
    # TODO: Implement bot control
    return {"message": "Bot start not implemented yet", "status": "pending"}


@app.post("/api/control/stop")
async def stop_bot():
    """Stop the trading bot."""
    # TODO: Implement bot control
    return {"message": "Bot stop not implemented yet", "status": "pending"}


@app.post("/api/control/toggle-auto-trade")
async def toggle_auto_trade():
    """Toggle auto-trading on/off."""
    # TODO: Implement auto-trade toggle
    return {"message": "Auto-trade toggle not implemented yet", "status": "pending"}


# ========== Health Check ==========

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "trading-ui-api",
        "connections": len(data_bridge.connections),
        "symbols": len(data_bridge.symbol_data)
    }


# ========== Startup Event ==========

async def broadcast_updates_periodically():
    """Broadcast updates to all connected WebSocket clients every 3 seconds."""
    while True:
        try:
            await asyncio.sleep(3)  # Broadcast every 3 seconds (smoother)
            
            if data_bridge.connections and data_bridge.symbol_data:
                # Broadcast full state to all connected clients
                message = {
                    'type': 'update',
                    'data': {
                        'symbols': data_bridge.symbol_data,
                        'bot_status': data_bridge.bot_status,
                        'performance': data_bridge.performance
                    }
                }
                await data_bridge.broadcast(message)
        except Exception as e:
            print(f"Broadcast error: {e}")


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    print("=" * 60)
    print("🚀 Trading System Web UI API Starting...")
    print("=" * 60)
    print(f"Frontend dir: {FRONTEND_DIR}")
    print(f"Static dir: {STATIC_DIR}")
    print("✅ API Ready!")
    print("📊 Dashboard: http://localhost:8000")
    print("🔌 WebSocket: ws://localhost:8000/ws")
    print("=" * 60)
    
    # Start background task for periodic broadcasts
    asyncio.create_task(broadcast_updates_periodically())
    asyncio.create_task(broadcast_backtest_updates())


@app.on_event("shutdown")
@app.get("/backtest")
async def get_backtest_page():
    """Serve the backtest results page."""
    backtest_html = FRONTEND_DIR / "backtest.html"
    if not backtest_html.exists():
        raise HTTPException(status_code=404, detail="Backtest page not found")
    return FileResponse(str(backtest_html))


@app.get("/backtest.html")
async def get_backtest_page_with_extension():
    """Serve the backtest results page (with .html extension)."""
    backtest_html = FRONTEND_DIR / "backtest.html"
    if not backtest_html.exists():
        raise HTTPException(status_code=404, detail="Backtest page not found")
    return FileResponse(str(backtest_html))


@app.get("/backtest.js")
async def get_backtest_js():
    """Serve the backtest JavaScript file."""
    backtest_js = FRONTEND_DIR / "backtest.js"
    if not backtest_js.exists():
        raise HTTPException(status_code=404, detail="Backtest JS not found")
    return FileResponse(str(backtest_js))


@app.get("/backtest-styles.css")
async def get_backtest_styles():
    """Serve the backtest styles file."""
    backtest_css = FRONTEND_DIR / "backtest-styles.css"
    if not backtest_css.exists():
        raise HTTPException(status_code=404, detail="Backtest styles not found")
    return FileResponse(str(backtest_css))


@app.get("/backtest-debug.html")
async def get_backtest_debug():
    """Serve the backtest debug page."""
    debug_html = FRONTEND_DIR / "backtest-debug.html"
    if not debug_html.exists():
        raise HTTPException(status_code=404, detail="Debug page not found")
    return FileResponse(str(debug_html))


@app.get("/api/backtest/results")
async def get_backtest_results():
    """Get the latest backtest results."""
    results_file = Path(__file__).parent.parent.parent / "backtest_results.json"
    
    if not results_file.exists():
        raise HTTPException(status_code=404, detail="No backtest results found. Please run a backtest first.")
    
    try:
        with open(results_file, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading backtest results: {str(e)}")


@app.get("/api/backtest/state")
async def get_backtest_state():
    """Get current real-time backtest state."""
    return data_bridge.get_backtest_state()


# Add backtest state broadcasting to WebSocket
async def broadcast_backtest_updates():
    """Periodically broadcast backtest updates to all connected clients."""
    import sys
    print("[Backend] Starting backtest broadcast task...", file=sys.stderr, flush=True)
    while True:
        try:
            if data_bridge.backtest_active:
                state = data_bridge.get_backtest_state()
                iteration = state['data'].get('current_iteration', 0)
                connections_count = len(data_bridge.connections)
                
                if connections_count > 0:
                    print(f"[Backend] Broadcasting backtest update - iteration: {iteration}, connections: {connections_count}", file=sys.stderr, flush=True)
                    await data_bridge.broadcast({
                        'type': 'backtest_update',
                        'data': state
                    })
                else:
                    # No connections, but backtest is active - log occasionally
                    if iteration % 10 == 0:
                        print(f"[Backend] Backtest active (iter: {iteration}) but no WebSocket connections", file=sys.stderr, flush=True)
            await asyncio.sleep(0.5)  # Update every 500ms
        except Exception as e:
            print(f"Error broadcasting backtest updates: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
            await asyncio.sleep(1)


async def shutdown_event():
    """Run on application shutdown."""
    print("🛑 Shutting down Trading System UI API...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

