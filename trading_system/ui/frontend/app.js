/**
 * Trading System Dashboard - Main Application
 * Handles WebSocket connections, data updates, and UI interactions
 */

// Global state
const state = {
    ws: null,
    connected: false,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    chartManager: null,
    currentSymbol: null,
    symbols: {},
    performance: {},
    botStatus: {},
    openPositions: [],
    closedOrders: [],
    indicators: [],
    events: []
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Trading System Dashboard Loading...');
    
    // Initialize chart
    state.chartManager = new ChartManager('chart-container');
    
    // Connect to WebSocket
    connectWebSocket();
    
    // Set up periodic health checks
    setInterval(checkConnection, 30000); // Every 30 seconds
});

// ========== WebSocket Management ==========

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    console.log(`Connecting to WebSocket: ${wsUrl}`);
    updateConnectionStatus('connecting');
    
    try {
        state.ws = new WebSocket(wsUrl);
        
        state.ws.onopen = handleWebSocketOpen;
        state.ws.onmessage = handleWebSocketMessage;
        state.ws.onerror = handleWebSocketError;
        state.ws.onclose = handleWebSocketClose;
    } catch (error) {
        console.error('WebSocket connection error:', error);
        updateConnectionStatus('error');
        scheduleReconnect();
    }
}

function handleWebSocketOpen() {
    console.log('✅ WebSocket connected');
    state.connected = true;
    state.reconnectAttempts = 0;
    updateConnectionStatus('connected');
    
    // Request initial full state
    sendMessage({ command: 'get_state' });
}

function handleWebSocketMessage(event) {
    try {
        const message = JSON.parse(event.data);
        
        switch (message.type) {
            case 'full_state':
                handleFullState(message.data);
                break;
            
            case 'update':
                handleUpdate(message.data);
                break;
            
            case 'symbol_update':
                handleSymbolUpdate(message.symbol, message.data);
                break;
            
            case 'chart_data':
                handleChartData(message.symbol, message.data);
                break;
            
            case 'trade':
                handleTradeEvent(message.data);
                break;
            
            case 'positions_update':
                handlePositionsUpdate(message.open_positions, message.closed_orders);
                break;
            
            case 'ping':
                sendMessage({ command: 'pong' });
                break;
            
            case 'pong':
                // Keepalive response
                break;
            
            default:
                console.log('Unknown message type:', message.type);
        }
        
        updateLastUpdate();
    } catch (error) {
        console.error('Error parsing WebSocket message:', error);
    }
}

function handleWebSocketError(error) {
    console.error('WebSocket error:', error);
    updateConnectionStatus('error');
}

function handleWebSocketClose() {
    console.warn('WebSocket disconnected');
    state.connected = false;
    updateConnectionStatus('disconnected');
    scheduleReconnect();
}

function scheduleReconnect() {
    if (state.reconnectAttempts < state.maxReconnectAttempts) {
        state.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, state.reconnectAttempts), 30000);
        console.log(`Reconnecting in ${delay/1000}s (attempt ${state.reconnectAttempts}/${state.maxReconnectAttempts})`);
        setTimeout(connectWebSocket, delay);
    } else {
        console.error('Max reconnection attempts reached');
        updateConnectionStatus('failed');
    }
}

function checkConnection() {
    if (state.connected) {
        sendMessage({ command: 'ping' });
    } else {
        console.log('Connection lost, attempting reconnect...');
        state.reconnectAttempts = 0;
        connectWebSocket();
    }
}

function sendMessage(message) {
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify(message));
    }
}

// ========== Data Handlers ==========

function handleFullState(data) {
    console.log('📦 Received full state');
    
    // Update state
    state.botStatus = data.bot_status || {};
    state.symbols = data.symbols || {};
    state.performance = data.performance || {};
    state.openPositions = data.open_positions || [];
    state.closedOrders = data.closed_orders || [];
    state.indicators = data.indicators || [];
    state.events = data.events || [];
    
    // Update UI
    updateBotStatus();
    updatePerformanceMetrics();
    updateMetricsTable();
    updateComprehensiveSymbolsTable();
    updateSymbolList();
    updateIndicatorsList();
    updateOpenPositions();
    updateClosedTrades();
    updateEventLog();
    
    // Load first symbol if available
    const symbols = Object.keys(state.symbols);
    if (symbols.length > 0 && !state.currentSymbol) {
        selectSymbol(symbols[0]);
    }
}

function handleUpdate(data) {
    // Handle incremental updates
    if (data.symbols) {
        Object.assign(state.symbols, data.symbols);
        updateComprehensiveSymbolsTable();
        updateSymbolList();
    }
    
    if (data.performance) {
        Object.assign(state.performance, data.performance);
        updatePerformanceMetrics();
        updateMetricsTable();
    }
    
    if (data.bot_status) {
        Object.assign(state.botStatus, data.bot_status);
        updateBotStatus();
    }
}

function handleSymbolUpdate(symbol, data) {
    // Handle real-time symbol updates
    console.log(`Symbol update: ${symbol} - ${data.latest_price}`);
    
    // Update state
    state.symbols[symbol] = data;
    
    // Update UI
    updateComprehensiveSymbolsTable();
    updateSymbolList();
    
    // If this is the currently selected symbol, update details
    if (symbol === state.currentSymbol) {
        updateSignalDetails(symbol);
    }
}

function handleChartData(symbol, data) {
    console.log(`📊 Received chart data for ${symbol}:`, data.length, 'candles');
    
    if (state.chartManager && data && data.length > 0) {
        state.chartManager.updateData(symbol, data);
        updateChartTitle(symbol);
    }
}

function handleTradeEvent(data) {
    console.log('💰 Trade event:', data);
    // Could show notification or update UI
}

function handlePositionsUpdate(openPositions, closedOrders) {
    console.log(`📊 Positions update: ${openPositions.length} open, ${closedOrders.length} closed`);
    
    // Update state
    state.openPositions = openPositions || [];
    state.closedOrders = closedOrders || [];
    
    // Update UI
    updateComprehensiveSymbolsTable();
    updateOpenPositions();
    updateClosedTrades();
    updatePerformanceMetrics();
}

// ========== UI Update Functions ==========

function updateConnectionStatus(status) {
    const statusEl = document.getElementById('connection-status');
    const wsStatusEl = document.getElementById('ws-status');
    const wsIconEl = document.getElementById('ws-icon');
    
    const statusConfig = {
        connecting: {
            text: 'Connecting...',
            wsText: 'Connecting',
            class: 'bg-warning',
            icon: 'bi-hourglass-split'
        },
        connected: {
            text: 'Connected',
            wsText: 'Connected',
            class: 'bg-success status-online',
            icon: 'bi-wifi'
        },
        disconnected: {
            text: 'Disconnected',
            wsText: 'Disconnected',
            class: 'bg-danger',
            icon: 'bi-wifi-off'
        },
        error: {
            text: 'Error',
            wsText: 'Error',
            class: 'bg-danger status-error',
            icon: 'bi-exclamation-triangle'
        },
        failed: {
            text: 'Failed',
            wsText: 'Failed',
            class: 'bg-danger status-error',
            icon: 'bi-x-circle'
        }
    };
    
    const config = statusConfig[status] || statusConfig.disconnected;
    
    if (statusEl) {
        statusEl.className = `badge ${config.class}`;
        statusEl.innerHTML = `<i class="bi ${config.icon}"></i> ${config.text}`;
    }
    
    if (wsStatusEl) {
        wsStatusEl.textContent = config.wsText;
    }
    
    if (wsIconEl) {
        wsIconEl.className = `bi ${config.icon}`;
    }
}

function updateBotStatus() {
    const botStatusEl = document.getElementById('bot-status');
    const autoTradeEl = document.getElementById('auto-trade-status');
    const uptimeEl = document.getElementById('bot-uptime');
    const refreshCountEl = document.getElementById('refresh-count');
    
    // Bot running status
    if (botStatusEl) {
        const running = state.botStatus.running;
        botStatusEl.className = running ? 'badge bg-success' : 'badge bg-secondary';
        botStatusEl.innerHTML = running ? 
            '<i class="bi bi-robot"></i> Running' : 
            '<i class="bi bi-robot"></i> Stopped';
    }
    
    // Auto-trade status
    if (autoTradeEl) {
        const autoTrade = state.botStatus.auto_trade;
        const allowBuy = state.botStatus.allow_buy;
        const allowSell = state.botStatus.allow_sell;
        
        const directions = [];
        if (allowBuy) directions.push('BUY');
        if (allowSell) directions.push('SELL');
        const dirText = directions.length > 0 ? ` (${directions.join('/')})` : '';
        
        autoTradeEl.className = autoTrade ? 'badge bg-success' : 'badge bg-secondary';
        autoTradeEl.innerHTML = autoTrade ? 
            `<i class="bi bi-toggle-on"></i> Auto: ON${dirText}` : 
            '<i class="bi bi-toggle-off"></i> Auto: OFF';
    }
    
    // Uptime
    if (uptimeEl && state.botStatus.uptime_seconds !== undefined) {
        uptimeEl.textContent = formatDuration(state.botStatus.uptime_seconds);
        uptimeEl.className = 'card-title mb-0';
        uptimeEl.style.color = 'var(--text-primary)';
    }
    
    // Refresh count
    if (refreshCountEl && state.botStatus.refresh_count !== undefined) {
        refreshCountEl.textContent = `Refreshes: ${state.botStatus.refresh_count}`;
        refreshCountEl.className = 'text-muted';
    }
}

function updatePerformanceMetrics() {
    const perf = state.performance;
    
    // Total PnL
    const totalPnlEl = document.getElementById('total-pnl');
    if (totalPnlEl) {
        const totalPnl = perf.total_pnl || 0;
        const oldValue = totalPnlEl.textContent;
        const newValue = formatCurrency(totalPnl);
        
        // Only update if changed
        if (oldValue !== newValue) {
            totalPnlEl.textContent = newValue;
            // Ensure proper class with text color
            let pnlClass = 'neutral-pnl';
            if (totalPnl > 0) pnlClass = 'positive-pnl';
            if (totalPnl < 0) pnlClass = 'negative-pnl';
            totalPnlEl.className = `card-title mb-0 ${pnlClass}`;
            totalPnlEl.style.color = ''; // Let CSS handle it
        }
    }
    
    // PnL Breakdown
    const pnlBreakdownEl = document.getElementById('pnl-breakdown');
    if (pnlBreakdownEl) {
        const realized = perf.realized_pnl || 0;
        const unrealized = perf.unrealized_pnl || 0;
        pnlBreakdownEl.innerHTML = `R: ${formatCurrency(realized)} | U: ${formatCurrency(unrealized)}`;
        pnlBreakdownEl.className = 'text-muted';
    }
    
    // Win Rate
    const winRateEl = document.getElementById('win-rate');
    if (winRateEl) {
        winRateEl.textContent = `${(perf.win_rate || 0).toFixed(1)}%`;
        winRateEl.className = 'card-title mb-0';
        winRateEl.style.color = 'var(--text-primary)';
    }
    
    // Win/Loss
    const winLossEl = document.getElementById('win-loss');
    if (winLossEl) {
        winLossEl.textContent = `W: ${perf.win_trades || 0} | L: ${perf.loss_trades || 0}`;
        winLossEl.className = 'text-muted';
    }
    
    // Total Trades
    const totalTradesEl = document.getElementById('total-trades');
    if (totalTradesEl) {
        totalTradesEl.textContent = perf.total_trades || 0;
        totalTradesEl.className = 'card-title mb-0';
        totalTradesEl.style.color = 'var(--text-primary)';
    }
    
    // Open Positions
    const openPosEl = document.getElementById('open-positions');
    if (openPosEl) {
        openPosEl.textContent = `Open: ${state.openPositions.length}`;
        openPosEl.className = 'text-muted';
    }
}

function updateMetricsTable() {
    const metricsTableEl = document.getElementById('metrics-table');
    if (!metricsTableEl) return;
    
    const perf = state.performance;
    const bot = state.botStatus;
    
    // Calculate signal distribution
    const symbols = Object.values(state.symbols);
    const buySignals = symbols.filter(s => s.final_signal === 'BUY').length;
    const sellSignals = symbols.filter(s => s.final_signal === 'SELL').length;
    const holdSignals = symbols.filter(s => s.final_signal === 'HOLD').length;
    
    // Calculate average agreement
    const avgAgreement = symbols.length > 0 
        ? (symbols.reduce((sum, s) => sum + (s.agreement_pct || 0), 0) / symbols.length).toFixed(1)
        : 0;
    
    const html = `
        <div class="metrics-grid">
            <!-- Trading Performance Section -->
            <div class="metrics-section">
                <h6 class="metrics-section-title">
                    <i class="bi bi-graph-up"></i> Trading Performance
                </h6>
                <table class="metrics-table-inner">
                    <tr>
                        <td class="metric-label">Total PnL:</td>
                        <td class="metric-value ${getPnLClass(perf.total_pnl || 0)}">
                            <strong>${formatCurrency(perf.total_pnl || 0)}</strong>
                        </td>
                        <td class="metric-label">Win Rate:</td>
                        <td class="metric-value">
                            <strong class="${(perf.win_rate || 0) >= 50 ? 'text-success' : 'text-danger'}">
                                ${(perf.win_rate || 0).toFixed(1)}%
                            </strong>
                        </td>
                    </tr>
                    <tr>
                        <td class="metric-label">Realized PnL:</td>
                        <td class="metric-value ${getPnLClass(perf.realized_pnl || 0)}">
                            ${formatCurrency(perf.realized_pnl || 0)}
                        </td>
                        <td class="metric-label">Total Trades:</td>
                        <td class="metric-value">
                            ${perf.total_trades || 0}
                        </td>
                    </tr>
                    <tr>
                        <td class="metric-label">Unrealized PnL:</td>
                        <td class="metric-value ${getPnLClass(perf.unrealized_pnl || 0)}">
                            ${formatCurrency(perf.unrealized_pnl || 0)}*
                        </td>
                        <td class="metric-label">Win / Loss:</td>
                        <td class="metric-value">
                            <span class="text-success">${perf.win_trades || 0}</span> / 
                            <span class="text-danger">${perf.loss_trades || 0}</span>
                        </td>
                    </tr>
                    <tr>
                        <td class="metric-label">Best Trade:</td>
                        <td class="metric-value text-success">
                            ${formatCurrency(perf.best_trade || 0)}
                        </td>
                        <td class="metric-label">Worst Trade:</td>
                        <td class="metric-value text-danger">
                            ${formatCurrency(perf.worst_trade || 0)}
                        </td>
                    </tr>
                    <tr>
                        <td class="metric-label">Avg PnL/Trade:</td>
                        <td class="metric-value ${getPnLClass(perf.avg_pnl || 0)}">
                            ${formatCurrency(perf.avg_pnl || 0)}
                        </td>
                        <td class="metric-label"></td>
                        <td class="metric-value"></td>
                    </tr>
                </table>
            </div>
            
            <!-- Current Status Section -->
            <div class="metrics-section">
                <h6 class="metrics-section-title">
                    <i class="bi bi-activity"></i> Current Status
                </h6>
                <table class="metrics-table-inner">
                    <tr>
                        <td class="metric-label">Open Positions:</td>
                        <td class="metric-value">
                            <strong>${state.openPositions.length}</strong>
                        </td>
                        <td class="metric-label">Bot Status:</td>
                        <td class="metric-value">
                            <span class="${bot.running ? 'text-success' : 'text-secondary'}">
                                ${bot.running ? '● Running' : '○ Stopped'}
                            </span>
                        </td>
                    </tr>
                    <tr>
                        <td class="metric-label">Signals Today:</td>
                        <td class="metric-value">
                            ${bot.signals_generated || 0}
                        </td>
                        <td class="metric-label">Auto-Trade:</td>
                        <td class="metric-value">
                            <span class="${bot.auto_trade ? 'text-success' : 'text-secondary'}">
                                ${bot.auto_trade ? '✓ Enabled' : '✗ Disabled'}
                            </span>
                        </td>
                    </tr>
                    <tr>
                        <td class="metric-label">Bot Uptime:</td>
                        <td class="metric-value">
                            ${formatDuration(bot.uptime_seconds || 0)}
                        </td>
                        <td class="metric-label">Refresh Count:</td>
                        <td class="metric-value">
                            ${bot.refresh_count || 0}
                        </td>
                    </tr>
                </table>
            </div>
            
            <!-- Signal Distribution Section -->
            <div class="metrics-section">
                <h6 class="metrics-section-title">
                    <i class="bi bi-pie-chart"></i> Signal Distribution
                </h6>
                <table class="metrics-table-inner">
                    <tr>
                        <td class="metric-label">BUY Signals:</td>
                        <td class="metric-value">
                            <span class="text-success"><strong>${buySignals}</strong></span>
                        </td>
                        <td class="metric-label">SELL Signals:</td>
                        <td class="metric-value">
                            <span class="text-danger"><strong>${sellSignals}</strong></span>
                        </td>
                    </tr>
                    <tr>
                        <td class="metric-label">HOLD Signals:</td>
                        <td class="metric-value">
                            <span class="text-warning"><strong>${holdSignals}</strong></span>
                        </td>
                        <td class="metric-label">Total Symbols:</td>
                        <td class="metric-value">
                            <strong>${symbols.length}</strong>
                        </td>
                    </tr>
                </table>
            </div>
            
            <!-- Indicator Performance Section -->
            <div class="metrics-section">
                <h6 class="metrics-section-title">
                    <i class="bi bi-lightbulb"></i> Indicator Performance
                </h6>
                <table class="metrics-table-inner">
                    <tr>
                        <td class="metric-label">Avg Agreement:</td>
                        <td class="metric-value">
                            <strong>${avgAgreement}%</strong>
                        </td>
                        <td class="metric-label">Active Indicators:</td>
                        <td class="metric-value">
                            <strong>${state.indicators.filter(i => i.enabled).length}</strong> / ${state.indicators.length}
                        </td>
                    </tr>
                    <tr>
                        <td class="metric-label">Monitored Symbols:</td>
                        <td class="metric-value">
                            ${symbols.length}
                        </td>
                        <td class="metric-label">Last Update:</td>
                        <td class="metric-value">
                            <small>${new Date().toLocaleTimeString()}</small>
                        </td>
                    </tr>
                </table>
            </div>
        </div>
        
        <div class="mt-3">
            <small class="text-muted">
                <i class="bi bi-info-circle"></i> 
                * Unrealized PnL is from open positions | 
                All amounts in INR (₹) | 
                Updates every ${bot.refresh_interval || 5}s
            </small>
        </div>
    `;
    
    metricsTableEl.innerHTML = html;
}

function updateComprehensiveSymbolsTable() {
    const tableEl = document.getElementById('comprehensive-symbols-table');
    if (!tableEl) return;
    
    const symbols = Object.keys(state.symbols);
    
    console.log(`[TABLE] Updating comprehensive table for ${symbols.length} symbols`);
    console.log(`[TABLE] Open positions count: ${state.openPositions.length}`);
    
    if (symbols.length === 0) {
        tableEl.innerHTML = '<div class="text-muted text-center py-4">No symbols available</div>';
        return;
    }
    
    // Get all unique indicators from symbols data
    const allIndicators = new Set();
    symbols.forEach(symbol => {
        const data = state.symbols[symbol];
        if (data.indicator_signals) {
            Object.keys(data.indicator_signals).forEach(ind => allIndicators.add(ind));
        }
    });
    const indicatorNames = Array.from(allIndicators).sort();
    
    // Abbreviate indicator names
    const abbreviateIndicator = (name) => {
        const abbrev = {
            'RSI': 'RSI',
            'MA_Crossover': 'MA',
            'MACD': 'MACD',
            'Bollinger_Bands': 'BB',
            'MysticPulse': 'MP',
            'Mystic_Pulse': 'MP',
            'Stochastic': 'STOCH',
            'EMA': 'EMA',
            'SMA': 'SMA',
        };
        if (abbrev[name]) return abbrev[name];
        const capitals = name.match(/[A-Z]/g);
        if (capitals && capitals.length >= 2) return capitals.slice(0, 5).join('');
        return name.slice(0, 5).toUpperCase();
    };
    
    // Format signal with icon
    const formatSignalIcon = (signal) => {
        if (signal === 'BUY') return '<span class="signal-icon signal-icon-buy" title="BUY">✓</span>';
        if (signal === 'SELL') return '<span class="signal-icon signal-icon-sell" title="SELL">✗</span>';
        return '<span class="signal-icon signal-icon-hold" title="HOLD">○</span>';
    };
    
    // Calculate totals from both symbol data and openPositions
    let totalUnrealizedPnL = 0;
    symbols.forEach(symbol => {
        const data = state.symbols[symbol];
        let pnl = 0;
        
        // Try symbol data first
        if (data.unrealized_pnl) {
            pnl = parseFloat(data.unrealized_pnl);
        } else {
            // Fall back to openPositions
            const position = state.openPositions.find(p => p.symbol === symbol);
            if (position && position.unrealized_pnl) {
                pnl = parseFloat(position.unrealized_pnl);
            }
        }
        
        totalUnrealizedPnL += pnl;
    });
    
    // Build table HTML
    let html = `
        <table class="comprehensive-table">
            <thead>
                <tr>
                    <th class="sticky-col">Symbol</th>
                    <th>LTP<br><small>(₹)</small></th>
                    <th>Final<br>Signal</th>`;
    
    // Add indicator columns
    indicatorNames.forEach(ind => {
        html += `<th title="${ind}">${abbreviateIndicator(ind)}</th>`;
    });
    
    html += `
                    <th>Agree<br>%</th>
                    <th>Position</th>
                    <th>Entry<br>(₹)</th>
                    <th>Qty</th>
                    <th>Unrealized<br>PnL (₹)</th>
                </tr>
            </thead>
            <tbody>`;
    
        // Add rows for each symbol
        symbols.forEach(symbol => {
            const data = state.symbols[symbol];
            const fullSymbol = symbol;  // Use full symbol name
        const price = data.latest_price || data.current_price || 0;
        const signal = data.final_signal || 'HOLD';
        const indicators = data.indicator_signals || {};
        const agreement = data.agreement_pct || 0;
        
        // Check if position exists - first check symbol data, then openPositions array
        let positionType = data.position || '-';
        let entryPrice = data.entry_price || 0;
        let quantity = data.quantity || 0;
        let unrealizedPnL = data.unrealized_pnl || 0;
        
        // If not in symbol data, try to find in openPositions array
        if (positionType === '-' || positionType === undefined) {
            const position = state.openPositions.find(p => p.symbol === symbol);
            if (position) {
                console.log(`[TABLE] Found position for ${symbol} in openPositions:`, position);
                positionType = position.position;
                entryPrice = position.entry_price;
                quantity = position.quantity;
                unrealizedPnL = position.unrealized_pnl || 0;
            }
        } else {
            console.log(`[TABLE] Found position for ${symbol} in symbol data:`, {positionType, entryPrice, quantity, unrealizedPnL});
        }
        
        const hasPosition = positionType && positionType !== '-';
        
        // Signal styling
        let signalClass = 'signal-hold';
        if (signal === 'BUY') signalClass = 'signal-buy';
        if (signal === 'SELL') signalClass = 'signal-sell';
        
        html += `
            <tr class="symbol-row" data-symbol="${symbol}" onclick="selectSymbol('${symbol}')">
                <td class="sticky-col symbol-name-col"><strong>${fullSymbol}</strong></td>
                <td class="price-col">${price.toFixed(2)}</td>
                <td><span class="symbol-signal ${signalClass}">${signal}</span></td>`;
        
        // Add indicator signals
        indicatorNames.forEach(indName => {
            const indSignal = indicators[indName] || 'HOLD';
            html += `<td class="indicator-col">${formatSignalIcon(indSignal)}</td>`;
        });
        
        // Position info
        const positionClass = positionType === 'LONG' ? 'text-success' : positionType === 'SHORT' ? 'text-danger' : 'text-muted';
        const pnlClass = getPnLClass(unrealizedPnL);
        const entryDisplay = hasPosition ? entryPrice.toFixed(2) : '-';
        const pnlDisplay = hasPosition ? `${formatCurrency(unrealizedPnL)}*` : '-';
        
        html += `
                <td>${agreement.toFixed(0)}%</td>
                <td class="${positionClass}"><strong>${positionType}</strong></td>
                <td>${entryDisplay}</td>
                <td>${quantity}</td>
                <td class="${pnlClass}"><strong>${pnlDisplay}</strong></td>
            </tr>`;
    });
    
    // Add total row if there are positions
    if (totalUnrealizedPnL !== 0) {
        const totalClass = getPnLClass(totalUnrealizedPnL);
        const numEmptyCols = 3 + indicatorNames.length + 4; // Signal + indicators + Agree/Pos/Entry/Qty
        html += `
            <tr class="total-row">
                <td class="sticky-col"><strong>TOTAL UNREALIZED</strong></td>
                <td colspan="${numEmptyCols}"></td>
                <td class="${totalClass}"><strong>${formatCurrency(totalUnrealizedPnL)}*</strong></td>
            </tr>`;
    }
    
    html += `
            </tbody>
        </table>
        <div class="mt-2">
            <small class="text-muted">
                <i class="bi bi-info-circle"></i> 
                Legend: ✓ = BUY | ✗ = SELL | ○ = HOLD | 
                * = Unrealized PnL (from open positions) | 
                Click row to view chart
            </small>
        </div>`;
    
    tableEl.innerHTML = html;
}

function updateSymbolList() {
    const symbolListEl = document.getElementById('symbol-list');
    if (!symbolListEl) return;
    
    const symbols = Object.keys(state.symbols);
    
    if (symbols.length === 0) {
        symbolListEl.innerHTML = '<div class="text-muted text-center py-4">No symbols</div>';
        return;
    }
    
    // Check if we need to create the structure (first time or symbol list changed)
    const existingCards = symbolListEl.querySelectorAll('.symbol-card');
    const needsRebuild = existingCards.length !== symbols.length;
    
    if (needsRebuild) {
        // Full rebuild only when necessary
        symbolListEl.innerHTML = symbols.map(symbol => {
            const data = state.symbols[symbol];
            const signal = data.final_signal || 'HOLD';
            const price = data.latest_price || data.current_price || 0;
            const isActive = symbol === state.currentSymbol;
            
            return `
                <div class="symbol-card ${isActive ? 'active' : ''}" 
                     data-symbol="${symbol}"
                     onclick="selectSymbol('${symbol}')">
                    <div class="symbol-name" title="${symbol}">${symbol}</div>
                    <div class="symbol-price" data-price="${price}">${formatCurrency(price)}</div>
                    <span class="symbol-signal signal-${signal.toLowerCase()}">${signal}</span>
                </div>
            `;
        }).join('');
    } else {
        // Update only the values that changed (no blink!)
        symbols.forEach(symbol => {
            const data = state.symbols[symbol];
            const signal = data.final_signal || 'HOLD';
            const price = data.latest_price || data.current_price || 0;
            const isActive = symbol === state.currentSymbol;
            
            // Find the card for this symbol
            const card = symbolListEl.querySelector(`[data-symbol="${symbol}"]`);
            if (!card) return;
            
            // Update active state
            if (isActive) {
                card.classList.add('active');
            } else {
                card.classList.remove('active');
            }
            
            // Update price only if changed
            const priceEl = card.querySelector('.symbol-price');
            if (priceEl) {
                const oldPrice = parseFloat(priceEl.getAttribute('data-price'));
                if (oldPrice !== price) {
                    priceEl.setAttribute('data-price', price);
                    priceEl.textContent = formatCurrency(price);
                    // Add flash effect
                    priceEl.classList.add('price-update');
                    setTimeout(() => priceEl.classList.remove('price-update'), 500);
                }
            }
            
            // Update signal only if changed
            const signalEl = card.querySelector('.symbol-signal');
            if (signalEl) {
                const oldSignal = signalEl.textContent;
                if (oldSignal !== signal) {
                    // Remove old signal class
                    signalEl.classList.remove('signal-buy', 'signal-sell', 'signal-hold');
                    // Add new signal class
                    signalEl.classList.add(`signal-${signal.toLowerCase()}`);
                    signalEl.textContent = signal;
                }
            }
        });
    }
}

function updateIndicatorsList() {
    const indicatorsListEl = document.getElementById('indicators-list');
    const indicatorsCountEl = document.getElementById('indicators-count');
    
    if (!indicatorsListEl) return;
    
    if (state.indicators.length === 0) {
        indicatorsListEl.innerHTML = '<div class="text-muted text-center py-3">No indicators</div>';
        if (indicatorsCountEl) indicatorsCountEl.textContent = '0';
        return;
    }
    
    indicatorsListEl.innerHTML = state.indicators.map(ind => {
        const enabled = ind.enabled ? '✓' : '✗';
        const enabledClass = ind.enabled ? 'text-success' : 'text-secondary';
        
        return `
            <div class="indicator-item fade-in">
                <div>
                    <span class="${enabledClass}" style="font-size: 1.2rem;">${enabled}</span>
                    <span class="indicator-name ms-2">${ind.name || 'Unknown'}</span>
                </div>
                <div>
                    <span class="badge bg-secondary">Weight: ${ind.weight || 1.0}</span>
                </div>
            </div>
        `;
    }).join('');
    
    if (indicatorsCountEl) {
        const enabledCount = state.indicators.filter(i => i.enabled).length;
        indicatorsCountEl.textContent = `${enabledCount}/${state.indicators.length}`;
    }
}

function updateOpenPositions() {
    const openPosTableEl = document.getElementById('open-positions-table');
    const openPosCountEl = document.getElementById('open-positions-count');
    
    if (!openPosTableEl) return;
    
    if (state.openPositions.length === 0) {
        openPosTableEl.innerHTML = '<div class="text-muted text-center py-3">No open positions</div>';
        if (openPosCountEl) openPosCountEl.textContent = '0';
        return;
    }
    
    const html = `
        <table class="positions-table">
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Type</th>
                    <th>Entry</th>
                    <th>Current</th>
                    <th>Qty</th>
                    <th>PnL</th>
                </tr>
            </thead>
            <tbody>
                ${state.openPositions.map(pos => {
                    const pnl = pos.unrealized_pnl || 0;
                    const pnlClass = getPnLClass(pnl);
                    return `
                        <tr class="fade-in">
                            <td><strong>${shortenSymbol(pos.symbol)}</strong></td>
                            <td><span class="badge ${pos.position === 'LONG' ? 'bg-success' : 'bg-danger'}">${pos.position}</span></td>
                            <td>${formatCurrency(pos.entry_price)}</td>
                            <td>${formatCurrency(pos.current_price)}</td>
                            <td>${pos.quantity}</td>
                            <td class="${pnlClass}"><strong>${formatCurrency(pnl)}*</strong></td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
    
    openPosTableEl.innerHTML = html;
    
    if (openPosCountEl) {
        openPosCountEl.textContent = state.openPositions.length;
    }
}

function updateClosedTrades() {
    const closedTradesEl = document.getElementById('closed-trades-table');
    
    if (!closedTradesEl) return;
    
    if (state.closedOrders.length === 0) {
        closedTradesEl.innerHTML = '<div class="text-muted text-center py-3">No completed trades</div>';
        return;
    }
    
    const html = `
        <table class="positions-table">
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Type</th>
                    <th>Entry</th>
                    <th>Exit</th>
                    <th>Qty</th>
                    <th>PnL</th>
                    <th>Time</th>
                </tr>
            </thead>
            <tbody>
                ${state.closedOrders.slice(-20).reverse().map(order => {
                    const pnl = order.pnl || 0;
                    const pnlClass = getPnLClass(pnl);
                    return `
                        <tr class="fade-in">
                            <td><strong>${shortenSymbol(order.symbol)}</strong></td>
                            <td><span class="badge ${order.position === 'LONG' ? 'bg-success' : 'bg-danger'}">${order.position}</span></td>
                            <td>${formatCurrency(order.entry_price)}</td>
                            <td>${formatCurrency(order.exit_price)}</td>
                            <td>${order.quantity}</td>
                            <td class="${pnlClass}"><strong>${formatCurrency(pnl)}</strong></td>
                            <td><small>${formatTime(order.exit_time)}</small></td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
    
    closedTradesEl.innerHTML = html;
}

function updateEventLog() {
    const eventLogEl = document.getElementById('event-log');
    
    if (!eventLogEl) return;
    
    if (state.events.length === 0) {
        eventLogEl.innerHTML = '<div class="text-muted">No events yet...</div>';
        return;
    }
    
    const html = state.events.slice(-30).reverse().map(event => `
        <div class="event-item fade-in">
            <span class="event-time">[${formatTime(event.timestamp)}]</span>
            <span class="event-message">${event.message}</span>
        </div>
    `).join('');
    
    eventLogEl.innerHTML = html;
}

function selectSymbol(symbol) {
    state.currentSymbol = symbol;
    updateSymbolList(); // Refresh to show active state
    updateSignalDetails(symbol);
    
    // Request chart data
    sendMessage({
        command: 'get_chart',
        symbol: symbol
    });
}

function updateSignalDetails(symbol) {
    const signalDetailsEl = document.getElementById('signal-details');
    if (!signalDetailsEl) return;
    
    const data = state.symbols[symbol];
    if (!data) {
        signalDetailsEl.innerHTML = '<div class="text-muted text-center py-3">No data</div>';
        return;
    }
    
    const signal = data.final_signal || 'HOLD';
    const indicators = data.indicator_signals || {};
    
    const html = `
        <div class="mb-3">
            <h5>Final Signal</h5>
            <span class="symbol-signal signal-${signal.toLowerCase()}" style="font-size: 1.2rem; padding: 0.5rem 1rem;">
                ${signal}
            </span>
        </div>
        
        <div class="signal-details-grid">
            <div class="signal-detail-item">
                <div class="signal-detail-label">Price</div>
                <div class="signal-detail-value">${formatCurrency(data.latest_price || data.current_price || 0)}</div>
            </div>
            
            <div class="signal-detail-item">
                <div class="signal-detail-label">Agreement</div>
                <div class="signal-detail-value">${(data.agreement_pct || 0)}%</div>
            </div>
        </div>
        
        <div class="mt-3">
            <h6>Indicator Signals</h6>
            ${Object.entries(indicators).map(([name, sig]) => `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span>${name}</span>
                    <span class="symbol-signal signal-${sig.toLowerCase()}">${sig}</span>
                </div>
            `).join('')}
        </div>
    `;
    
    signalDetailsEl.innerHTML = html;
}

function updateChartTitle(symbol) {
    const titleEl = document.getElementById('chart-symbol-title');
    if (titleEl) {
        titleEl.textContent = symbol;
    }
}

function updateLastUpdate() {
    const lastUpdateEl = document.getElementById('last-update');
    if (lastUpdateEl) {
        lastUpdateEl.textContent = new Date().toLocaleTimeString();
    }
}

// ========== Utility Functions ==========

function formatCurrency(value) {
    const num = parseFloat(value) || 0;
    const sign = num >= 0 ? '+' : '';
    return `₹${sign}${num.toFixed(2)}`;
}

function formatDuration(seconds) {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${mins}m`;
}

function formatTime(timestamp) {
    if (!timestamp) return '--';
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
}

function shortenSymbol(symbol) {
    // Return full symbol name - no shortening
    // Users want to see complete symbol names
    return symbol;
}

function getPnLClass(value) {
    const num = parseFloat(value) || 0;
    if (num > 0) return 'positive-pnl';
    if (num < 0) return 'negative-pnl';
    return 'neutral-pnl';
}

// ========== Control Functions ==========

function changeTimeframe(timeframe) {
    console.log('Changing timeframe to:', timeframe);
    // TODO: Implement timeframe change
    // This would require updating the data loader resolution
}

// Export for debugging
window.state = state;
window.selectSymbol = selectSymbol;
window.changeTimeframe = changeTimeframe;

