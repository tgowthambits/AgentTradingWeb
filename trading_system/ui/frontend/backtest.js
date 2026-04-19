// Backtest Results UI

const API_BASE = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

let websocket = null;
let reconnectInterval = null;

// Load backtest results on page load
document.addEventListener('DOMContentLoaded', function() {
    loadBacktestResults();
    connectWebSocket();
    
    // Poll for backtest state every 2 seconds as backup
    setInterval(pollBacktestState, 2000);
});

async function pollBacktestState() {
    try {
        const response = await fetch(`${API_BASE}/api/backtest/state`);
        if (response.ok) {
            const state = await response.json();
            if (state.active) {
                handleBacktestUpdate(state);
            }
        }
    } catch (error) {
        // Silent fail - WebSocket is primary method
    }
}

async function loadBacktestResults() {
    try {
        // First check if there's an active backtest
        const stateResponse = await fetch(`${API_BASE}/api/backtest/state`);
        if (stateResponse.ok) {
            const state = await stateResponse.json();
            if (state.active && state.data.status === 'running') {
                console.log('Active backtest detected, waiting for real-time updates...');
                // Show loading state and wait for WebSocket updates
                return;
            }
        }
        
        // No active backtest, try to load completed results
        const response = await fetch(`${API_BASE}/api/backtest/results`);
        
        if (!response.ok) {
            throw new Error('No backtest results available');
        }
        
        const data = await response.json();
        
        if (!data || !data.summary) {
            showNoData();
            return;
        }
        
        // Hide loading, show content
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('mainContent').style.display = 'block';
        
        // Populate all sections
        populateSummaryHeader(data.summary);
        populateMetricsTable(data.metrics);
        populateTradesTable(data.trades);
        populateCircuitBreakerSection(data.circuit_breaker);
        populateConfigSection(data.config);
        populateTimelineSection(data.timeline);
        
        // Populate loss recovery section if available
        if (data.loss_recovery) {
            populateLossRecoverySection(data.loss_recovery);
        }
        
    } catch (error) {
        console.error('Error loading backtest results:', error);
        // Don't show "no data" immediately - WebSocket might provide updates
        console.log('Waiting for WebSocket backtest updates...');
    }
}

function showNoData() {
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('noDataState').style.display = 'block';
}

function populateSummaryHeader(summary) {
    const initial = summary.initial_capital || 0;
    const final_cap = summary.final_capital || 0;
    const pnl = summary.total_pnl || 0;
    const returns = summary.returns_pct || 0;
    
    document.getElementById('initialCapital').textContent = `₹${formatNumber(initial)}`;
    
    const finalCapEl = document.getElementById('finalCapital');
    finalCapEl.textContent = `₹${formatNumber(final_cap)}`;
    finalCapEl.className = final_cap >= initial ? 'text-success mb-0' : 'text-danger mb-0';
    
    const pnlEl = document.getElementById('totalPnL');
    pnlEl.textContent = `₹${formatNumber(pnl, true)}`;
    pnlEl.className = pnl >= 0 ? 'text-success mb-0' : 'text-danger mb-0';
    
    const returnEl = document.getElementById('returnPct');
    returnEl.textContent = `${formatNumber(returns, true)}%`;
    returnEl.className = returns >= 0 ? 'text-success mb-0' : 'text-danger mb-0';
}

function populateMetricsTable(metrics) {
    const tbody = document.getElementById('metricsTableBody');
    tbody.innerHTML = '';
    
    if (!metrics || metrics.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">No metrics available</td></tr>';
        return;
    }
    
    metrics.forEach(metric => {
        const row = document.createElement('tr');
        
        if (metric.is_category) {
            row.innerHTML = `
                <td colspan="3" class="metric-category">${metric.category}</td>
            `;
        } else if (metric.is_divider) {
            row.innerHTML = `
                <td colspan="3" class="metric-divider">────────────────</td>
            `;
        } else {
            const valueClass = getMetricValueClass(metric.value, metric.is_positive);
            row.innerHTML = `
                <td>${metric.category || ''}</td>
                <td>${metric.metric}</td>
                <td class="${valueClass}">${metric.value}</td>
            `;
        }
        
        tbody.appendChild(row);
    });
}

function populateTradesTable(trades) {
    const tbody = document.getElementById('tradesTableBody');
    tbody.innerHTML = '';
    
    if (!trades || trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="14" class="text-center text-muted">No completed trades</td></tr>';
        return;
    }
    
    // Check if candle prices should be shown (from config if available, default to true)
    const showEntryHigh = window.tradingConfig?.output?.show_candle_prices?.show_entry_high !== false;
    const showExitLow = window.tradingConfig?.output?.show_candle_prices?.show_exit_low !== false;
    const showCandlePrices = window.tradingConfig?.output?.show_candle_prices?.enabled !== false;
    
    const actualShowEntryHigh = showCandlePrices && showEntryHigh;
    const actualShowExitLow = showCandlePrices && showExitLow;
    
    // Show/hide headers
    const entryHighHeader = document.getElementById('entryHighHeader');
    const exitLowHeader = document.getElementById('exitLowHeader');
    if (entryHighHeader) entryHighHeader.style.display = actualShowEntryHigh ? '' : 'none';
    if (exitLowHeader) exitLowHeader.style.display = actualShowExitLow ? '' : 'none';
    
    trades.forEach(trade => {
        const row = document.createElement('tr');
        
        const pnlClass = trade.pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
        const returnClass = trade.return_pct >= 0 ? 'pnl-positive' : 'pnl-negative';
        const typeClass = trade.type === 'LONG' ? 'trade-long' : 'trade-short';
        const modeClass = trade.mode === 'PAPER' ? 'mode-paper' : 'mode-real';
        
        // Get charges and net profit (with fallbacks)
        const totalCharges = trade.total_charges || 0;
        const netProfit = trade.net_profit !== undefined ? trade.net_profit : trade.pnl;
        const netProfitClass = netProfit >= 0 ? 'pnl-positive' : 'pnl-negative';
        
        // Get entry candle high and exit candle low
        const entryCandleHigh = trade.entry_candle_high !== undefined && trade.entry_candle_high !== null ? trade.entry_candle_high.toFixed(2) : 'N/A';
        const exitCandleLow = trade.exit_candle_low !== undefined && trade.exit_candle_low !== null ? trade.exit_candle_low.toFixed(2) : 'N/A';
        
        let rowHTML = `
            <td>${trade.order_id}</td>
            <td>${trade.symbol}</td>
            <td class="${typeClass}">${trade.type}</td>
            <td>${trade.entry_price.toFixed(2)}</td>`;
        
        if (actualShowEntryHigh) {
            rowHTML += `<td style="color: #999;">${entryCandleHigh}</td>`;
        }
        
        rowHTML += `<td>${trade.exit_price.toFixed(2)}</td>`;
        
        if (actualShowExitLow) {
            rowHTML += `<td style="color: #999;">${exitCandleLow}</td>`;
        }
        
        rowHTML += `
            <td>${trade.quantity}</td>
            <td class="${pnlClass}">${formatNumber(trade.pnl, true)}</td>
            <td class="${returnClass}">${formatNumber(trade.return_pct, true)}%</td>
            <td><span class="${modeClass}">${trade.mode}</span></td>
            <td>${trade.duration}</td>
            <td style="color: #ffa500;">${formatNumber(totalCharges, false)}</td>
            <td class="${netProfitClass}">${formatNumber(netProfit, true)}</td>
            <td class="entry-reason" title="${trade.entry_reason || 'N/A'}">${trade.entry_reason || 'N/A'}</td>
            <td class="exit-reason" title="${trade.exit_reason || 'N/A'}">${trade.exit_reason || 'N/A'}</td>
        `;
        
        row.innerHTML = rowHTML;
        tbody.appendChild(row);
    });
}

function populateCircuitBreakerSection(cbData) {
    if (!cbData || !cbData.enabled) {
        document.getElementById('circuitBreakerSection').style.display = 'none';
        return;
    }
    
    document.getElementById('circuitBreakerSection').style.display = 'block';
    
    // Capital comparison
    document.getElementById('capitalWithout').textContent = `₹${formatNumber(cbData.capital_without)}`;
    document.getElementById('capitalWith').textContent = `₹${formatNumber(cbData.capital_with)}`;
    document.getElementById('capitalSaved').textContent = `₹${formatNumber(cbData.capital_saved, true)}`;
    
    // PnL comparison
    const pnlWithout = cbData.pnl_without || 0;
    const pnlWith = cbData.pnl_with || 0;
    const returnWithout = cbData.return_pct_without || 0;
    const returnWith = cbData.return_pct_with || 0;
    
    document.getElementById('pnlWithout').innerHTML = `PnL: <span class="${pnlWithout >= 0 ? 'text-success' : 'text-danger'}">₹${formatNumber(pnlWithout, true)} (${formatNumber(returnWithout, true)}%)</span>`;
    document.getElementById('pnlWith').innerHTML = `PnL: <span class="${pnlWith >= 0 ? 'text-success' : 'text-danger'}">₹${formatNumber(pnlWith, true)} (${formatNumber(returnWith, true)}%)</span>`;
    
    // Paper trades
    document.getElementById('paperTrades').textContent = `${cbData.paper_trades_count} Paper Trades`;
    
    // Trades comparison
    document.getElementById('tradesWithout').textContent = cbData.total_trades_without || 0;
    document.getElementById('tradesWith').textContent = cbData.total_trades_with || 0;
    document.getElementById('tradesAvoided').textContent = cbData.trades_avoided || 0;
    
    // Win rate comparison
    const winRateWithout = cbData.win_rate_without || 0;
    const winRateWith = cbData.win_rate_with || 0;
    const improvement = cbData.win_rate_improvement || 0;
    
    const wrWithoutEl = document.getElementById('winRateWithout');
    wrWithoutEl.textContent = `${(winRateWithout * 100).toFixed(2)}%`;
    wrWithoutEl.className = winRateWithout >= 0.5 ? 'text-success' : 'text-danger';
    
    const wrWithEl = document.getElementById('winRateWith');
    wrWithEl.textContent = `${(winRateWith * 100).toFixed(2)}%`;
    wrWithEl.className = winRateWith >= 0.5 ? 'text-success' : 'text-danger';
    
    document.getElementById('wlWithout').textContent = `(${cbData.wins_without}W/${cbData.losses_without}L)`;
    document.getElementById('wlWith').textContent = `(${cbData.wins_with}W/${cbData.losses_with}L)`;
    
    // Improvement
    if (Math.abs(improvement) > 0.0001) {
        document.getElementById('improvementSection').style.display = 'block';
        const improvementEl = document.getElementById('winRateImprovement');
        improvementEl.textContent = `${formatNumber(improvement * 100, true)}%`;
        improvementEl.className = improvement > 0 ? 'text-success' : 'text-danger';
    } else {
        document.getElementById('improvementSection').style.display = 'none';
    }
}

function populateConfigSection(config) {
    const tbody = document.getElementById('configTableBody');
    tbody.innerHTML = '';
    
    if (!config) {
        tbody.innerHTML = '<tr><td colspan="2" class="text-center text-muted">No configuration data</td></tr>';
        return;
    }
    
    const configItems = [
        { label: 'Symbols', value: config.symbols || 'N/A' },
        { label: 'Initial Capital', value: config.initial_capital ? `₹${formatNumber(config.initial_capital)}` : 'N/A' },
        { label: 'Risk Per Trade', value: config.risk_per_trade || 'N/A' },
        { label: 'Stop Loss Method', value: config.stop_loss_method || 'N/A' },
        { label: 'Max Loss Per Trade', value: config.max_loss_per_trade ? `₹${config.max_loss_per_trade}` : 'N/A' },
        { label: 'Circuit Breaker', value: config.circuit_breaker_enabled ? 'Enabled' : 'Disabled' },
        { label: 'CB Trigger', value: config.circuit_breaker_trigger ? `${config.circuit_breaker_trigger} losses` : 'N/A' },
        { label: 'Fixed Quantity', value: config.fixed_quantity || 'N/A' }
    ];
    
    configItems.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="text-muted">${item.label}</td>
            <td class="text-light"><strong>${item.value}</strong></td>
        `;
        tbody.appendChild(row);
    });
}

function populateLossRecoverySection(lossRecoveryData) {
    // Show the section
    document.getElementById('lossRecoverySection').style.display = 'block';
    
    // Populate Loss History
    const lossHistory = lossRecoveryData.loss_history || [];
    const lossHistoryBody = document.getElementById('lossHistoryBody');
    lossHistoryBody.innerHTML = '';
    
    if (lossHistory.length === 0) {
        lossHistoryBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No losses recorded</td></tr>';
    } else {
        lossHistory.forEach(loss => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${loss.trade_id}</td>
                <td>${loss.symbol}</td>
                <td class="text-danger">₹${formatNumber(loss.loss_amount, true)}</td>
                <td>₹${loss.entry_price.toFixed(2)}</td>
                <td>₹${loss.exit_price.toFixed(2)}</td>
                <td>${loss.quantity}</td>
                <td class="text-muted">${formatTimestamp(loss.timestamp)}</td>
            `;
            lossHistoryBody.appendChild(row);
        });
    }
    
    // Populate Recovery History
    const recoveryHistory = lossRecoveryData.recovery_history || [];
    const recoveryHistoryBody = document.getElementById('recoveryHistoryBody');
    recoveryHistoryBody.innerHTML = '';
    
    if (recoveryHistory.length === 0) {
        recoveryHistoryBody.innerHTML = '<tr><td colspan="10" class="text-center text-muted">No recoveries recorded</td></tr>';
    } else {
        recoveryHistory.forEach(recovery => {
            const row = document.createElement('tr');
            const statusClass = recovery.full_recovery ? 'text-success' : 'text-warning';
            const statusText = recovery.full_recovery ? 'FULL' : 'PARTIAL';
            row.innerHTML = `
                <td>${recovery.trade_id}</td>
                <td>${recovery.symbol}</td>
                <td class="text-danger">₹${formatNumber(recovery.loss_amount, true)}</td>
                <td class="text-success">₹${formatNumber(recovery.recovered_amount, true)}</td>
                <td class="text-warning">₹${formatNumber(recovery.remaining_loss, true)}</td>
                <td><span class="${statusClass}">${statusText}</span></td>
                <td>₹${recovery.entry_price.toFixed(2)}</td>
                <td>₹${recovery.exit_price.toFixed(2)}</td>
                <td>${recovery.quantity}</td>
                <td class="text-muted">${formatTimestamp(recovery.timestamp)}</td>
            `;
            recoveryHistoryBody.appendChild(row);
        });
    }
    
    // Populate Current Status
    const currentStatus = lossRecoveryData.current_status || {};
    const symbolsWithLoss = currentStatus.symbols_with_loss || [];
    const lossStatusBody = document.getElementById('lossStatusBody');
    lossStatusBody.innerHTML = '';
    
    if (symbolsWithLoss.length === 0) {
        lossStatusBody.innerHTML = '<tr><td colspan="2" class="text-center text-success"><strong>✅ All losses have been recovered!</strong></td></tr>';
    } else {
        symbolsWithLoss.forEach(symbol => {
            const lossAmount = currentStatus.symbol_losses[symbol] || 0;
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${symbol}</td>
                <td class="text-danger">₹${lossAmount.toFixed(2)}</td>
            `;
            lossStatusBody.appendChild(row);
        });
        
        // Add total row
        const totalRow = document.createElement('tr');
        totalRow.className = 'table-warning';
        totalRow.innerHTML = `
            <td><strong>TOTAL</strong></td>
            <td class="text-danger"><strong>₹${formatNumber(currentStatus.total_unrecovered_loss || 0, true)}</strong></td>
        `;
        lossStatusBody.appendChild(totalRow);
    }
}

function formatTimestamp(timestamp) {
    if (!timestamp) return 'N/A';
    try {
        const date = new Date(timestamp);
        return date.toLocaleString();
    } catch (e) {
        return String(timestamp);
    }
}

function populateTimelineSection(timeline) {
    const tbody = document.getElementById('timelineTableBody');
    tbody.innerHTML = '';
    
    if (!timeline) {
        tbody.innerHTML = '<tr><td colspan="2" class="text-center text-muted">No timeline data</td></tr>';
        return;
    }
    
    const timelineItems = [
        { label: 'Start Date', value: timeline.start_date || 'N/A' },
        { label: 'End Date', value: timeline.end_date || 'N/A' },
        { label: 'Duration', value: timeline.duration || 'N/A' },
        { label: 'Total Iterations', value: timeline.total_iterations || 'N/A' },
        { label: 'Backtest Started', value: timeline.backtest_started || 'N/A' },
        { label: 'Backtest Completed', value: timeline.backtest_completed || 'N/A' },
        { label: 'Execution Time', value: timeline.execution_time || 'N/A' }
    ];
    
    timelineItems.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="text-muted">${item.label}</td>
            <td class="text-light"><strong>${item.value}</strong></td>
        `;
        tbody.appendChild(row);
    });
}

// Helper functions
function formatNumber(value, showSign = false) {
    if (value === null || value === undefined) return '0';
    
    const num = parseFloat(value);
    if (isNaN(num)) return value;
    
    const formatted = num.toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    
    if (showSign && num > 0) {
        return '+' + formatted;
    }
    
    return formatted;
}

function getMetricValueClass(value, isPositive) {
    if (isPositive === undefined || isPositive === null) {
        return '';
    }
    
    // Check if value contains color indicators
    if (typeof value === 'string') {
        if (value.includes('+') || value.includes('↑')) {
            return 'pnl-positive';
        } else if (value.includes('-') || value.includes('↓')) {
            return 'pnl-negative';
        }
    }
    
    return isPositive ? 'pnl-positive' : (isPositive === false ? 'pnl-negative' : '');
}

// WebSocket Connection
function connectWebSocket() {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        return;
    }
    
    try {
        websocket = new WebSocket(WS_URL);
        
        websocket.onopen = function() {
            console.log('🔌 WebSocket connected for real-time backtest updates');
            clearInterval(reconnectInterval);
            
            // Update loading message
            const loadingMsg = document.getElementById('loadingMessage');
            if (loadingMsg) {
                loadingMsg.textContent = 'Connected! Waiting for backtest to start...';
                loadingMsg.className = 'mt-3 text-success';
            }
        };
        
        websocket.onmessage = function(event) {
            try {
                const message = JSON.parse(event.data);
                console.log('WebSocket message received:', message.type);
                
                if (message.type === 'backtest_update') {
                    console.log('Processing backtest update:', message.data);
                    handleBacktestUpdate(message.data);
                } else {
                    console.log('Other message type:', message.type);
                }
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
                console.error('Raw message:', event.data);
            }
        };
        
        websocket.onclose = function() {
            console.log('🔌 WebSocket disconnected, attempting to reconnect...');
            reconnectInterval = setInterval(connectWebSocket, 3000);
        };
        
        websocket.onerror = function(error) {
            console.error('WebSocket error:', error);
        };
    } catch (error) {
        console.error('Failed to connect WebSocket:', error);
        reconnectInterval = setInterval(connectWebSocket, 3000);
    }
}

function handleBacktestUpdate(state) {
    console.log('Received backtest update:', state);
    
    if (!state || !state.active) {
        console.log('No active backtest');
        return;
    }
    
    const data = state.data;
    console.log('Backtest data:', data);
    
    // If backtest is running, show main content and hide loading/no data
    if (data.status === 'running' || data.status === 'completed') {
        console.log('Showing main content for status:', data.status);
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('noDataState').style.display = 'none';
        document.getElementById('mainContent').style.display = 'block';
    }
    
    // Update summary header
    const initial = data.initial_capital || 0;
    const current = data.current_capital || initial;
    const pnl = data.total_pnl || 0;
    const returns = data.returns_pct || 0;
    
    const initialCapEl = document.getElementById('initialCapital');
    const finalCapEl = document.getElementById('finalCapital');
    const pnlEl = document.getElementById('totalPnL');
    const returnEl = document.getElementById('returnPct');
    
    if (initialCapEl) initialCapEl.textContent = `₹${formatNumber(initial)}`;
    
    if (finalCapEl) {
        finalCapEl.textContent = `₹${formatNumber(current)}`;
        finalCapEl.className = current >= initial ? 'text-success mb-0' : 'text-danger mb-0';
    }
    
    if (pnlEl) {
        pnlEl.textContent = `₹${formatNumber(pnl, true)}`;
        pnlEl.className = pnl >= 0 ? 'text-success mb-0' : 'text-danger mb-0';
    }
    
    if (returnEl) {
        returnEl.textContent = `${formatNumber(returns, true)}%`;
        returnEl.className = returns >= 0 ? 'text-success mb-0' : 'text-danger mb-0';
    }
    
    // Update progress if available
    if (data.progress !== undefined) {
        document.title = `Backtest: ${data.progress.toFixed(1)}% - Trading System`;
    }
    
    // Update all trades in table
    if (data.trades_list && data.trades_list.length > 0) {
        updateAllTrades(data.trades_list);
    } else if (data.last_trade) {
        updateTradeRow(data.last_trade);
    }
    
    // Update metrics table with current summary
    if (data.metrics) {
        updateMetricsTableLive(data);
    }
    
    // Update circuit breaker section if applicable
    if (data.circuit_breaker_active || data.paper_trades > 0) {
        updateCircuitBreakerLive(data);
    }
    
    // Update symbols & LTP table (live data during backtest)
    updateSymbolsLTPTable(data);
    
    // If completed, load full results
    if (data.status === 'completed') {
        document.title = 'Backtest Results - Trading System';
        setTimeout(() => loadBacktestResults(), 1000);
    }
}

function updateAllTrades(trades) {
    const tbody = document.getElementById('tradesTableBody');
    if (!tbody) return;
    
    // Clear existing rows
    tbody.innerHTML = '';
    
    // Sort trades by order_id (most recent first)
    const sortedTrades = [...trades].sort((a, b) => b.order_id - a.order_id);
    
    // Add all trades
    sortedTrades.forEach(trade => {
        const row = document.createElement('tr');
        row.setAttribute('data-order-id', trade.order_id);
        
        const pnlClass = trade.pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
        const returnClass = trade.return_pct >= 0 ? 'pnl-positive' : 'pnl-negative';
        const typeClass = trade.type === 'LONG' ? 'trade-long' : 'trade-short';
        const modeClass = trade.mode === 'PAPER' ? 'mode-paper' : 'mode-real';
        
        // Get charges and net profit (with fallbacks)
        const totalCharges = trade.total_charges || 0;
        const netProfit = trade.net_profit !== undefined ? trade.net_profit : trade.pnl;
        const netProfitClass = netProfit >= 0 ? 'pnl-positive' : 'pnl-negative';
        
        row.innerHTML = `
            <td>${trade.order_id}</td>
            <td>${trade.symbol}</td>
            <td class="${typeClass}">${trade.type}</td>
            <td>${trade.entry_price.toFixed(2)}</td>
            <td>${trade.exit_price.toFixed(2)}</td>
            <td>${trade.quantity}</td>
            <td class="${pnlClass}">${formatNumber(trade.pnl, true)}</td>
            <td class="${returnClass}">${formatNumber(trade.return_pct, true)}%</td>
            <td><span class="${modeClass}">${trade.mode}</span></td>
            <td>${trade.duration || 'N/A'}</td>
            <td style="color: #ffa500;">${formatNumber(totalCharges, false)}</td>
            <td class="${netProfitClass}">${formatNumber(netProfit, true)}</td>
            <td class="exit-reason" title="${trade.exit_reason || 'N/A'}">${(trade.exit_reason || 'N/A').substring(0, 20)}</td>
        `;
        
        tbody.appendChild(row);
    });
    
    console.log(`Updated trades table with ${sortedTrades.length} trades`);
}

function updateTradeRow(trade) {
    const tbody = document.getElementById('tradesTableBody');
    if (!tbody) return;
    
    // Check if trade already exists
    const existingRow = document.querySelector(`#tradesTableBody tr[data-order-id="${trade.order_id}"]`);
    if (existingRow) {
        return; // Already added
    }
    
    const row = document.createElement('tr');
    row.setAttribute('data-order-id', trade.order_id);
    
    const pnlClass = trade.pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
    const returnClass = trade.return_pct >= 0 ? 'pnl-positive' : 'pnl-negative';
    const typeClass = trade.type === 'LONG' ? 'trade-long' : 'trade-short';
    const modeClass = trade.mode === 'PAPER' ? 'mode-paper' : 'mode-real';
    
    row.innerHTML = `
        <td>${trade.order_id}</td>
        <td>${trade.symbol}</td>
        <td class="${typeClass}">${trade.type}</td>
        <td>${trade.entry_price.toFixed(2)}</td>
        <td>${trade.exit_price.toFixed(2)}</td>
        <td>${trade.quantity}</td>
        <td class="${pnlClass}">${formatNumber(trade.pnl, true)}</td>
        <td class="${returnClass}">${formatNumber(trade.return_pct, true)}%</td>
        <td><span class="${modeClass}">${trade.mode}</span></td>
        <td>${trade.duration || 'N/A'}</td>
        <td class="exit-reason" title="${trade.exit_reason || 'N/A'}">${(trade.exit_reason || 'N/A').substring(0, 20)}</td>
    `;
    
    // Add to top of table for most recent first
    if (tbody.firstChild) {
        tbody.insertBefore(row, tbody.firstChild);
    } else {
        tbody.appendChild(row);
    }
    
    // Limit to last 50 trades to prevent table from growing too large
    while (tbody.children.length > 50) {
        tbody.removeChild(tbody.lastChild);
    }
}

function updateMetricsTableLive(data) {
    // Update key metrics in the table if they exist
    const metrics = data.metrics || {};
    
    // We'll update the summary header which is already being updated
    // The full metrics table will be populated when backtest completes
    // For now, just ensure the summary is visible
}

function updateSymbolsLTPTable(data) {
    const tbody = document.getElementById('symbolsLTPTableBody');
    if (!tbody) return;
    
    const symbolsData = data.symbols_ltp || {};
    const symbols = Object.keys(symbolsData);
    
    // Update iteration badge
    const iterationBadge = document.getElementById('backtestIteration');
    if (iterationBadge && data.current_iteration !== undefined) {
        iterationBadge.textContent = `Iteration: ${data.current_iteration}`;
    }
    
    // Update timestamp
    const timestampEl = document.getElementById('backtestTimestamp');
    if (timestampEl) {
        const now = new Date();
        timestampEl.textContent = now.toLocaleTimeString();
    }
    
    if (symbols.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" class="text-center text-muted">
            <i class="bi bi-hourglass-split"></i> No symbol data yet...
        </td></tr>`;
        return;
    }
    
    // Build table rows
    let html = '';
    symbols.forEach(symbol => {
        const symbolData = symbolsData[symbol];
        const ltp = symbolData.ltp || symbolData.close || 0;
        const open = symbolData.open || ltp;
        const high = symbolData.high || ltp;
        const low = symbolData.low || ltp;
        const volume = symbolData.volume || 0;
        const change = symbolData.change || (ltp - open);
        const changePct = symbolData.change_pct || (open > 0 ? ((ltp - open) / open) * 100 : 0);
        const signal = symbolData.signal || '-';
        const position = symbolData.position || '-';
        
        const changeClass = change >= 0 ? 'text-success' : 'text-danger';
        const changeIcon = change >= 0 ? '+' : '';
        
        let signalClass = 'text-muted';
        if (signal === 'BUY') signalClass = 'text-success';
        else if (signal === 'SELL') signalClass = 'text-danger';
        
        let positionClass = 'text-muted';
        let positionBadgeClass = '';
        if (position === 'LONG') {
            positionClass = 'text-success';
            positionBadgeClass = 'bg-success';
        } else if (position === 'SHORT') {
            positionClass = 'text-danger';
            positionBadgeClass = 'bg-danger';
        }
        
        html += `
            <tr>
                <td><strong>${symbol}</strong></td>
                <td class="text-info">${formatNumber(ltp)}</td>
                <td class="${changeClass}"><strong>${changeIcon}${formatNumber(change, true)}</strong></td>
                <td class="${changeClass}">${changeIcon}${changePct.toFixed(2)}%</td>
                <td>${formatNumber(open)}</td>
                <td>${formatNumber(high)}</td>
                <td>${formatNumber(low)}</td>
                <td>${volume.toLocaleString()}</td>
                <td class="${signalClass}"><strong>${signal}</strong></td>
                <td>${position !== '-' ? `<span class="badge ${positionBadgeClass}">${position}</span>` : '-'}</td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
}

function updateCircuitBreakerLive(data) {
    const section = document.getElementById('circuitBreakerSection');
    if (!section) return;
    
    section.style.display = 'block';
    
    // Update basic stats
    if (data.circuit_breaker_active) {
        const paperTradesEl = document.getElementById('paperTrades');
        if (paperTradesEl) {
            paperTradesEl.textContent = `${data.paper_trades || 0} Paper Trades (ACTIVE)`;
            paperTradesEl.className = 'mb-0 text-warning';
        }
    } else if (data.paper_trades > 0) {
        const paperTradesEl = document.getElementById('paperTrades');
        if (paperTradesEl) {
            paperTradesEl.textContent = `${data.paper_trades} Paper Trades`;
            paperTradesEl.className = 'mb-0 text-muted';
        }
    }
}

