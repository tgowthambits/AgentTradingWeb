(() => {
  const root = document.getElementById("bt-detail-root");
  if (!root) return;

  const runId = parseInt(root.dataset.runId, 10);
  const initialStatus = root.dataset.status;

  const ACTIVE = new Set(["pending", "running", "paused", "stopping"]);
  const LEVEL_ORDER = { DEBUG: 10, INFO: 20, WARNING: 30, ERROR: 40, CRITICAL: 50 };
  const LEVEL_CLASS = {
    DEBUG: "opacity-50",
    INFO: "",
    WARNING: "text-warning",
    ERROR: "text-error",
    CRITICAL: "text-error font-semibold",
  };
  const MAX_LOG_LINES = 2000;

  const el = (id) => document.getElementById(id);
  const statusBadge = el("bt-status-badge");
  const progressPanel = el("bt-progress-panel");
  const progressBar = el("bt-progress-bar");
  const progressPct = el("bt-progress-pct");
  const progressBars = el("bt-progress-bars");
  const progressMsg = el("bt-progress-msg");
  const errorPanel = el("bt-error");
  const errorText = el("bt-error-text");
  const controls = el("bt-controls");
  const btnPause = el("btn-pause");
  const btnResume = el("btn-resume");
  const btnStop = el("btn-stop");
  const tradesBody = el("bt-trades-body");
  const tradesEmpty = el("bt-trades-empty");
  const tradeCountEl = el("bt-trade-count");
  const openBody = el("bt-open-body");
  const openCountEl = el("bt-open-count");
  const logBox = el("bt-log");
  const logConn = el("bt-log-conn");
  const logLevelSel = el("bt-log-level");
  const logAutoscroll = el("bt-log-autoscroll");
  const logClearBtn = el("bt-log-clear");

  const BADGE_CLASS = {
    pending:   "badge-info",
    running:   "badge-warning",
    paused:    "badge-ghost",
    stopping:  "badge-ghost",
    stopped:   "badge-ghost",
    completed: "badge-success",
    failed:    "badge-error",
  };

  let currentStatus = initialStatus;
  let ws = null;
  let pollTimer = null;
  let minLevel = LEVEL_ORDER[logLevelSel.value] || LEVEL_ORDER.INFO;
  let logWasClearedOnce = false;

  logLevelSel.addEventListener("change", () => {
    minLevel = LEVEL_ORDER[logLevelSel.value] || LEVEL_ORDER.INFO;
  });
  logClearBtn.addEventListener("click", () => { logBox.innerHTML = ""; });

  function getCookie(name) {
    const v = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return v ? v.pop() : "";
  }

  function fmtPnl(val) {
    if (val === null || val === undefined) return "--";
    const n = parseFloat(val) || 0;
    const cls = n >= 0 ? "pnl-positive" : "pnl-negative";
    const sign = n >= 0 ? "+" : "";
    return `<span class="${cls}">${sign}${n.toFixed(2)}</span>`;
  }

  function setStatus(status) {
    currentStatus = status;
    statusBadge.textContent = status;
    statusBadge.className = `badge badge-sm ${BADGE_CLASS[status] || "badge-ghost"}`;

    const active = ACTIVE.has(status);
    progressPanel.classList.toggle("hidden", !active && status !== "completed" && status !== "stopped");
    controls.classList.toggle("hidden", !active);
    btnStop.disabled = status === "stopping";

    if (status === "paused") {
      btnPause.classList.add("hidden");
      btnResume.classList.remove("hidden");
    } else {
      btnPause.classList.remove("hidden");
      btnResume.classList.add("hidden");
    }
  }

  function applyRun(run) {
    if (!run) return;
    setStatus(run.status);
    el("bt-total-bars").textContent = run.total_bars || 0;

    const total = run.total_bars || 0;
    const done = run.processed_bars || 0;
    const pct = total > 0 ? (done / total * 100) : 0;
    progressBar.value = pct;
    progressPct.textContent = `${pct.toFixed(1)}%`;
    progressBars.textContent = `${done} / ${total} bars`;

    renderSummary(run.summary_json);
    renderMetrics(run.metrics_json);

    if (run.error_message) {
      errorPanel.classList.remove("hidden");
      errorText.textContent = run.error_message;
    }
  }

  function renderSummary(s) {
    if (!s) return;
    if (s.initial_capital !== undefined && s.initial_capital !== null) {
      el("bt-initial-capital").textContent = Number(s.initial_capital).toFixed(2);
    }
    if (s.final_capital !== undefined && s.final_capital !== null) {
      el("bt-final-capital").textContent = Number(s.final_capital).toFixed(2);
    }
    if (s.total_pnl !== undefined && s.total_pnl !== null) {
      el("bt-total-pnl").innerHTML = fmtPnl(s.total_pnl);
    }
    if (s.returns_pct !== undefined && s.returns_pct !== null) {
      const ret = Number(s.returns_pct);
      el("bt-return-pct").innerHTML =
        `<span class="${ret >= 0 ? 'pnl-positive' : 'pnl-negative'}">${ret.toFixed(2)}%</span>`;
    }
  }

  function renderMetrics(m) {
    if (!m) return;
    el("bt-m-total-trades").textContent = m.total_trades ?? 0;
    el("bt-m-win-rate").textContent = m.win_rate !== undefined ? `${m.win_rate}%` : "--";
    el("bt-m-pf").textContent = m.profit_factor ?? "--";
    el("bt-m-avg-win").textContent = m.avg_win ?? "--";
    el("bt-m-avg-loss").textContent = m.avg_loss ?? "--";
    el("bt-m-max-win").textContent = m.max_win ?? "--";
    el("bt-m-max-loss").textContent = m.max_loss ?? "--";
    el("bt-m-expectancy").textContent = m.expectancy ?? "--";
    el("bt-m-wins").textContent = m.winning_trades ?? 0;
    el("bt-m-losses").textContent = m.losing_trades ?? 0;
  }

  // ─── Candlestick chart grid ─────────────────────────────
  const gridEl = el("bt-chart-grid");
  const pickerHost = el("bt-layout-picker");

  const SYMBOLS = (() => {
    try {
      const node = el("bt-symbols-data");
      const arr = node ? JSON.parse(node.textContent) : [];
      return Array.isArray(arr) ? arr : [];
    } catch { return []; }
  })();

  const barsBySymbol = new Map();           // symbol -> Array<bar>
  const barIndexBySymbol = new Map();       // symbol -> Map<time, barRef>
  const tradeMarkersBySymbol = new Map();   // symbol -> Array<marker>
  const tradeOrderIds = new Set();          // order_ids whose closed-trade markers are already rendered
  const openEntryMarkers = new Map();       // symbol -> Map<orderId, marker>
  const seededSymbols = new Set();          // symbols whose cached bars we already fetched

  let cells = [];                           // Array<Cell> - one per grid tile
  let currentLayout = (window.ChartLayouts && window.ChartLayouts.findLayout("1")) || null;

  // ── IST (Asia/Kolkata) formatters for the chart axis + crosshair ───
  const IST_TZ = "Asia/Kolkata";
  const istTime = new Intl.DateTimeFormat("en-GB", {
    timeZone: IST_TZ, hour: "2-digit", minute: "2-digit", hour12: false,
  });
  const istTimeSec = new Intl.DateTimeFormat("en-GB", {
    timeZone: IST_TZ, hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
  });
  const istDay = new Intl.DateTimeFormat("en-GB", {
    timeZone: IST_TZ, day: "2-digit", month: "short",
  });
  const istMonth = new Intl.DateTimeFormat("en-GB", {
    timeZone: IST_TZ, month: "short",
  });
  const istYear = new Intl.DateTimeFormat("en-GB", {
    timeZone: IST_TZ, year: "numeric",
  });
  const istDateTime = new Intl.DateTimeFormat("en-GB", {
    timeZone: IST_TZ, day: "2-digit", month: "short",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
  });

  function tickFormatterIST(time, tickMarkType) {
    const d = new Date(Number(time) * 1000);
    const TM = LightweightCharts.TickMarkType || {};
    if (tickMarkType === TM.Year) return istYear.format(d);
    if (tickMarkType === TM.Month) return istMonth.format(d);
    if (tickMarkType === TM.DayOfMonth) return istDay.format(d);
    if (tickMarkType === TM.TimeWithSeconds) return istTimeSec.format(d);
    return istTime.format(d);
  }

  function crosshairFormatterIST(time) {
    return `${istDateTime.format(new Date(Number(time) * 1000))} IST`;
  }

  function chartOptions() {
    return {
      layout: {
        background: { type: "solid", color: "transparent" },
        textColor: "#9ca3af",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(148,163,184,0.08)" },
        horzLines: { color: "rgba(148,163,184,0.08)" },
      },
      localization: { timeFormatter: crosshairFormatterIST },
      rightPriceScale: { borderColor: "rgba(148,163,184,0.2)" },
      timeScale: {
        borderColor: "rgba(148,163,184,0.2)",
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: tickFormatterIST,
      },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
      autoSize: true,
    };
  }

  function cellsForSymbol(symbol) {
    if (!symbol) return [];
    const out = [];
    for (const c of cells) if (c.activeSymbol === symbol) out.push(c);
    return out;
  }

  function fillLegend(cell, bar) {
    if (!cell || !cell.legend || !bar) return;
    const set = (k, v) => {
      const node = cell.legend.querySelector(`[data-f="${k}"]`);
      if (node) node.textContent = v;
    };
    set("o", Number(bar.open).toFixed(2));
    set("h", Number(bar.high).toFixed(2));
    set("l", Number(bar.low).toFixed(2));
    set("c", Number(bar.close).toFixed(2));
    set("v", bar.volume != null ? Math.round(bar.volume).toString() : "--");
  }

  function buildMarkers(symbol) {
    const trades = tradeMarkersBySymbol.get(symbol) || [];
    const opens = openEntryMarkers.get(symbol);
    const all = opens ? trades.concat(Array.from(opens.values())) : trades.slice();
    all.sort((a, b) => a.time - b.time);
    return all;
  }

  function redrawCell(cell) {
    if (!cell || !cell.series) return;
    const bars = cell.activeSymbol ? (barsBySymbol.get(cell.activeSymbol) || []) : [];
    cell.series.setData(bars);
    cell.series.setMarkers(buildMarkers(cell.activeSymbol));
    if (cell.barsLabel) cell.barsLabel.textContent = `${bars.length} bars`;
    if (bars.length) {
      fillLegend(cell, bars[bars.length - 1]);
      cell.chart.timeScale().scrollToRealTime();
    }
  }

  function createCell(id, initialSymbol, area) {
    const wrap = document.createElement("div");
    wrap.className = "flex flex-col border border-base-300 rounded bg-base-300/40 overflow-hidden min-h-0";
    wrap.dataset.cellId = id;
    wrap.style.gridArea = area;

    const header = document.createElement("div");
    header.className = "flex items-center gap-2 px-2 py-1.5 border-b border-base-300 flex-wrap";

    const sel = document.createElement("select");
    sel.className = "select select-xs select-bordered flex-1 min-w-24 max-w-56";
    for (const s of SYMBOLS) {
      const opt = document.createElement("option");
      opt.value = s; opt.textContent = s;
      if (s === initialSymbol) opt.selected = true;
      sel.appendChild(opt);
    }

    const barsLabel = document.createElement("span");
    barsLabel.className = "text-[10px] opacity-50 font-mono whitespace-nowrap";
    barsLabel.textContent = "0 bars";

    const legend = document.createElement("div");
    legend.className = "flex items-center gap-2 text-[10px] font-mono opacity-80 ml-auto";
    legend.innerHTML = `
      <span>O <span data-f="o">--</span></span>
      <span>H <span data-f="h">--</span></span>
      <span>L <span data-f="l">--</span></span>
      <span>C <span data-f="c">--</span></span>`;

    header.appendChild(sel);
    header.appendChild(barsLabel);
    header.appendChild(legend);

    const chartDiv = document.createElement("div");
    chartDiv.className = "w-full flex-1 min-h-0";

    wrap.appendChild(header);
    wrap.appendChild(chartDiv);
    gridEl.appendChild(wrap);

    const chart = LightweightCharts.createChart(chartDiv, chartOptions());
    const series = chart.addCandlestickSeries({
      upColor: "#10b981",
      downColor: "#ef4444",
      borderUpColor: "#10b981",
      borderDownColor: "#ef4444",
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });

    const cell = {
      id, wrap, sel, barsLabel, legend, chartDiv, chart, series,
      activeSymbol: initialSymbol || null,
    };

    chart.subscribeCrosshairMove(param => {
      let bar = null;
      if (param && param.seriesData && param.seriesData.size) {
        bar = param.seriesData.get(series) || null;
      }
      if (!bar) {
        const arr = barsBySymbol.get(cell.activeSymbol) || [];
        bar = arr[arr.length - 1] || null;
      }
      fillLegend(cell, bar);
    });

    sel.addEventListener("change", () => {
      cell.activeSymbol = sel.value || null;
      if (cell.activeSymbol) seedCachedBars(cell.activeSymbol);
      redrawCell(cell);
    });

    return cell;
  }

  function destroyCells() {
    for (const c of cells) {
      try { c.chart.remove(); } catch (_) { /* ignore */ }
    }
    cells = [];
    if (gridEl) gridEl.innerHTML = "";
  }

  function setLayout(layout) {
    if (!gridEl || typeof LightweightCharts === "undefined") return;
    if (!layout && window.ChartLayouts) layout = window.ChartLayouts.findLayout("1");
    if (!layout) return;
    currentLayout = layout;
    destroyCells();

    const style = window.ChartLayouts.gridStyle(layout);
    gridEl.style.display = "grid";
    gridEl.style.gridTemplateAreas = style.gridTemplateAreas;
    gridEl.style.gridTemplateColumns = style.gridTemplateColumns;
    gridEl.style.gridTemplateRows = style.gridTemplateRows;

    for (let i = 0; i < layout.count; i++) {
      const sym = SYMBOLS.length ? SYMBOLS[i % SYMBOLS.length] : null;
      cells.push(createCell(i, sym, window.ChartLayouts.cellArea(i)));
    }

    const seen = new Set();
    for (const c of cells) {
      if (c.activeSymbol && !seen.has(c.activeSymbol)) {
        seen.add(c.activeSymbol);
        seedCachedBars(c.activeSymbol);
      }
      redrawCell(c);
    }
  }

  if (pickerHost && window.ChartLayouts) {
    window.ChartLayouts.mountPicker(pickerHost, "1", setLayout);
  }

  async function seedCachedBars(symbol) {
    if (!symbol || seededSymbols.has(symbol)) return;
    seededSymbols.add(symbol);
    try {
      const url = `/api/backtest/runs/${runId}/bars/?symbol=${encodeURIComponent(symbol)}`;
      const resp = await fetch(url);
      if (!resp.ok) return;
      const data = await resp.json();
      if (!data || !Array.isArray(data.bars) || !data.bars.length) return;

      // Merge silently into the store (no per-bar series.update, because the
      // seed can arrive AFTER a newer WS bar and LightweightCharts rejects
      // out-of-order updates).
      let arr = barsBySymbol.get(symbol);
      let idx = barIndexBySymbol.get(symbol);
      if (!arr) { arr = []; barsBySymbol.set(symbol, arr); }
      if (!idx) { idx = new Map(); barIndexBySymbol.set(symbol, idx); }

      for (const bar of data.bars) {
        const t = Number(bar.time);
        if (!Number.isFinite(t) || idx.has(t)) continue;
        const rec = {
          time: t,
          open: bar.open, high: bar.high, low: bar.low,
          close: bar.close, volume: bar.volume,
        };
        idx.set(t, rec);
        arr.push(rec);
      }
      arr.sort((a, b) => a.time - b.time);

      for (const c of cellsForSymbol(symbol)) redrawCell(c);
    } catch (_) { /* ignore */ }
  }

  function ingestBars(barsBySym) {
    if (!barsBySym) return;
    for (const [sym, list] of Object.entries(barsBySym)) {
      if (!Array.isArray(list) || !list.length) continue;
      let arr = barsBySymbol.get(sym);
      let idx = barIndexBySymbol.get(sym);
      if (!arr) { arr = []; barsBySymbol.set(sym, arr); }
      if (!idx) { idx = new Map(); barIndexBySymbol.set(sym, idx); }

      const live = cellsForSymbol(sym);

      for (const bar of list) {
        const t = Number(bar.time);
        if (!Number.isFinite(t)) continue;
        const existing = idx.get(t);
        if (existing) {
          existing.open = bar.open;
          existing.high = bar.high;
          existing.low = bar.low;
          existing.close = bar.close;
          existing.volume = bar.volume;
          for (const c of live) c.series.update(existing);
          continue;
        }
        const rec = {
          time: t,
          open: bar.open, high: bar.high, low: bar.low,
          close: bar.close, volume: bar.volume,
        };
        // Keep bars sorted - in practice they arrive in order so push is fine.
        if (arr.length && t < arr[arr.length - 1].time) {
          let i = arr.length - 1;
          while (i >= 0 && arr[i].time > t) i--;
          arr.splice(i + 1, 0, rec);
        } else {
          arr.push(rec);
        }
        idx.set(t, rec);
        for (const c of live) c.series.update(rec);
      }

      if (live.length) {
        const last = arr[arr.length - 1];
        for (const c of live) {
          if (c.barsLabel) c.barsLabel.textContent = `${arr.length} bars`;
          fillLegend(c, last);
        }
      }
    }
  }

  function tsFromIso(iso) {
    if (!iso) return null;
    const d = new Date(iso);
    if (isNaN(d.getTime())) return null;
    return Math.floor(d.getTime() / 1000);
  }

  function addTradeMarkers(trades) {
    if (!Array.isArray(trades) || !trades.length) return;
    const touched = new Set();
    for (const t of trades) {
      const sym = t.symbol;
      if (!sym) continue;

      // Skip trades we've already plotted - refreshFromApi() re-sends the
      // full list every 5 s during a running backtest.
      const oid = t.order_id;
      if (oid != null) {
        if (tradeOrderIds.has(oid)) continue;
        tradeOrderIds.add(oid);
      }

      touched.add(sym);
      let list = tradeMarkersBySymbol.get(sym);
      if (!list) { list = []; tradeMarkersBySymbol.set(sym, list); }

      const isLong = (t.trade_type || "").toUpperCase() === "LONG";
      const entryTs = tsFromIso(t.entry_time);
      const exitTs = tsFromIso(t.exit_time);

      if (entryTs != null) {
        list.push({
          time: entryTs,
          position: isLong ? "belowBar" : "aboveBar",
          color: "#3b82f6",
          shape: isLong ? "arrowUp" : "arrowDown",
          text: `${isLong ? "BUY" : "SELL"} ${Number(t.entry_price).toFixed(2)}`,
        });
      }
      if (exitTs != null) {
        const pnl = Number(t.pnl || 0);
        list.push({
          time: exitTs,
          position: isLong ? "aboveBar" : "belowBar",
          color: pnl >= 0 ? "#10b981" : "#ef4444",
          shape: isLong ? "arrowDown" : "arrowUp",
          text: `EXIT ${Number(t.exit_price).toFixed(2)} (${pnl >= 0 ? "+" : ""}${pnl.toFixed(2)})`,
        });
      }

      // Drop any pending "open entry" marker for this order - the closed
      // trade marker replaces it.
      const openMap = openEntryMarkers.get(sym);
      if (openMap && oid != null) openMap.delete(oid);
    }
    for (const sym of touched) {
      const markers = buildMarkers(sym);
      for (const c of cellsForSymbol(sym)) c.series.setMarkers(markers);
    }
  }

  function syncOpenEntryMarkers(positions) {
    if (!Array.isArray(positions)) return;
    const seenPerSym = new Map();
    const touched = new Set();
    for (const p of positions) {
      const sym = p.symbol;
      if (!sym) continue;
      const ts = tsFromIso(p.entry_time);
      if (ts == null || p.order_id == null) continue;
      touched.add(sym);

      let symMap = openEntryMarkers.get(sym);
      if (!symMap) { symMap = new Map(); openEntryMarkers.set(sym, symMap); }

      const isLong = (p.type || "").toUpperCase() === "LONG";
      symMap.set(p.order_id, {
        time: ts,
        position: isLong ? "belowBar" : "aboveBar",
        color: "#f59e0b",
        shape: isLong ? "arrowUp" : "arrowDown",
        text: `OPEN ${isLong ? "LONG" : "SHORT"} ${Number(p.entry_price).toFixed(2)}`,
      });

      let set = seenPerSym.get(sym);
      if (!set) { set = new Set(); seenPerSym.set(sym, set); }
      set.add(p.order_id);
    }

    // Prune markers for positions that are no longer open on any symbol we saw.
    for (const [sym, symMap] of openEntryMarkers) {
      const seen = seenPerSym.get(sym);
      if (!seen) continue;
      for (const oid of Array.from(symMap.keys())) {
        if (!seen.has(oid)) {
          symMap.delete(oid);
          touched.add(sym);
        }
      }
    }

    for (const sym of touched) {
      const markers = buildMarkers(sym);
      for (const c of cellsForSymbol(sym)) c.series.setMarkers(markers);
    }
  }

  const symbolTicks = el("bt-symbol-ticks");
  const symbolRowCache = new Map();
  if (symbolTicks) {
    symbolTicks.querySelectorAll("[data-symbol]").forEach(row => {
      symbolRowCache.set(row.dataset.symbol, {
        row,
        time: row.querySelector('[data-field="time"]'),
        price: row.querySelector('[data-field="price"]'),
        signal: row.querySelector('[data-field="signal"]'),
      });
    });
  }
  const barTimeEl = el("bt-bar-time");
  const iterationEl = el("bt-iteration");

  const SIGNAL_BADGE = {
    BUY: "badge-success",
    SELL: "badge-error",
    HOLD: "badge-ghost",
  };

  function updateSymbolTicks(latest, barTime) {
    if (Array.isArray(latest)) {
      for (const t of latest) {
        const cell = symbolRowCache.get(t.symbol);
        if (!cell) continue;
        if (cell.price) cell.price.textContent = Number(t.price || 0).toFixed(2);
        if (cell.time) cell.time.textContent = fmtTradeTime(t.time);
        if (cell.signal) {
          const sig = (t.signal || "HOLD").toUpperCase();
          cell.signal.textContent = sig;
          cell.signal.className = `badge ${SIGNAL_BADGE[sig] || "badge-ghost"} badge-xs`;
        }
      }
    }
    if (barTimeEl) {
      barTimeEl.textContent = barTime ? `bar ${fmtTradeTime(barTime)}` : "";
    }
  }

  function updateProgress(msg) {
    progressPanel.classList.remove("hidden");
    const pct = msg.progress_pct || 0;
    progressBar.value = pct;
    progressPct.textContent = `${pct}%`;
    progressBars.textContent = `${msg.processed_bars || 0} / ${msg.total_bars || 0} bars`;
    const runPnl = Number(msg.running_pnl ?? 0);
    progressMsg.textContent = `iter ${msg.iteration || 0} · running PnL ${runPnl.toFixed(2)}`;
    if (iterationEl) iterationEl.textContent = msg.iteration ?? "--";

    updateSymbolTicks(msg.latest_results, msg.bar_time);

    if (msg.bars) ingestBars(msg.bars);

    renderSummary(msg.summary);
    renderMetrics(msg.metrics);

    // Fallbacks for when summary/metrics are missing (first few iterations).
    if (!msg.summary) el("bt-total-pnl").innerHTML = fmtPnl(msg.running_pnl);
    if (!msg.metrics) el("bt-m-total-trades").textContent = msg.trade_count ?? 0;
    tradeCountEl.textContent = msg.trade_count ?? 0;

    const open = msg.open_positions || [];
    openCountEl.textContent = open.length;
    syncOpenEntryMarkers(open);
    if (open.length > 0) {
      openBody.innerHTML = open.map(p => {
        const unreal = Number(p.unrealized_pnl || 0);
        const pct = Number(p.unrealized_pct || 0);
        const cls = unreal >= 0 ? "pnl-positive" : "pnl-negative";
        const typeCls = p.type === "LONG" ? "signal-buy" : "signal-sell";
        return `
        <tr>
          <td class="text-xs">${p.symbol}</td>
          <td><span class="${typeCls} text-xs">${p.type}</span></td>
          <td class="text-xs opacity-70 whitespace-nowrap">${fmtTradeTime(p.entry_time)}</td>
          <td class="font-mono text-xs">${parseFloat(p.entry_price).toFixed(2)}</td>
          <td class="font-mono text-xs">${parseFloat(p.ltp ?? p.entry_price).toFixed(2)}</td>
          <td class="font-mono text-xs">${p.quantity}</td>
          <td class="font-mono text-xs ${cls}">${unreal >= 0 ? "+" : ""}${unreal.toFixed(2)}</td>
          <td class="font-mono text-xs ${cls}">${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%</td>
        </tr>`;
      }).join("");
    } else {
      openBody.innerHTML = '<tr><td colspan="8" class="text-center py-6 opacity-30">None</td></tr>';
    }

    if (msg.new_trades && msg.new_trades.length) {
      appendTrades(msg.new_trades);
      addTradeMarkers(msg.new_trades);
    }
  }

  function fmtTradeTime(iso) {
    if (!iso) return "--";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "--";
    const mon = d.toLocaleString(undefined, { month: "short" });
    const day = String(d.getDate()).padStart(2, "0");
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    const ss = String(d.getSeconds()).padStart(2, "0");
    return `${mon} ${day} ${hh}:${mm}:${ss}`;
  }

  function appendTrades(rows) {
    if (tradesEmpty) {
      tradesEmpty.remove();
    }
    const existing = new Set(
      Array.from(tradesBody.querySelectorAll("tr[data-order-id]"))
        .map(tr => tr.dataset.orderId)
    );
    for (const t of rows) {
      const id = String(t.order_id);
      if (existing.has(id)) continue;
      existing.add(id);
      const pnlCls = t.pnl >= 0 ? "pnl-positive" : "pnl-negative";
      const retCls = t.return_pct >= 0 ? "pnl-positive" : "pnl-negative";
      const typeCls = t.trade_type === "LONG" ? "signal-buy" : "signal-sell";
      const modeBadge = t.is_paper
        ? '<span class="badge badge-warning badge-xs">PAPER</span>'
        : '<span class="badge badge-ghost badge-xs">REAL</span>';

      const tr = document.createElement("tr");
      tr.dataset.orderId = id;
      tr.innerHTML = `
        <td class="font-mono">${t.order_id}</td>
        <td class="text-xs">${t.symbol}</td>
        <td><span class="${typeCls} text-xs">${t.trade_type}</span></td>
        <td class="text-xs opacity-70 whitespace-nowrap">${fmtTradeTime(t.entry_time)}</td>
        <td class="font-mono text-xs">${Number(t.entry_price).toFixed(2)}</td>
        <td class="text-xs opacity-70 whitespace-nowrap">${fmtTradeTime(t.exit_time)}</td>
        <td class="font-mono text-xs">${Number(t.exit_price).toFixed(2)}</td>
        <td class="font-mono">${t.quantity}</td>
        <td class="font-mono text-xs ${pnlCls}">${t.pnl >= 0 ? "+" : ""}${Number(t.pnl).toFixed(2)}</td>
        <td class="font-mono text-xs ${retCls}">${Number(t.return_pct).toFixed(2)}%</td>
        <td>${modeBadge}</td>
        <td class="text-xs opacity-60">${t.duration || ""}</td>
        <td class="text-xs max-w-32 truncate opacity-60" title="${t.exit_reason || ""}">${t.exit_reason || ""}</td>`;
      tradesBody.appendChild(tr);
    }
    tradeCountEl.textContent = tradesBody.querySelectorAll("tr[data-order-id]").length;
  }

  // ─── Log panel ──────────────────────────────────────────
  function appendLogs(entries) {
    if (!entries || !entries.length) return;

    if (!logWasClearedOnce) {
      logBox.innerHTML = "";
      logWasClearedOnce = true;
    }

    const frag = document.createDocumentFragment();
    let added = 0;
    for (const entry of entries) {
      const level = entry.level || "INFO";
      if ((LEVEL_ORDER[level] || 0) < minLevel) continue;
      const line = document.createElement("div");
      line.className = LEVEL_CLASS[level] || "";
      line.textContent = entry.message || "";
      frag.appendChild(line);
      added++;
    }
    if (!added) return;
    logBox.appendChild(frag);

    while (logBox.childElementCount > MAX_LOG_LINES) {
      logBox.firstChild.remove();
    }
    if (logAutoscroll.checked) {
      logBox.scrollTop = logBox.scrollHeight;
    }
  }

  // ─── Controls ───────────────────────────────────────────
  btnPause.addEventListener("click", () => sendControl("pause"));
  btnResume.addEventListener("click", () => sendControl("resume"));
  btnStop.addEventListener("click", () => {
    if (!confirm("Stop this backtest? Already collected trades are preserved.")) return;
    sendControl("stop");
  });

  async function sendControl(action) {
    try {
      const resp = await fetch(`/api/backtest/runs/${runId}/${action}/`, {
        method: "POST",
        headers: { "X-CSRFToken": getCookie("csrftoken") },
      });
      if (!resp.ok) throw new Error(await resp.text());
    } catch (err) {
      alert(`${action} failed: ${err.message}`);
    }
  }

  // ─── WS ─────────────────────────────────────────────────
  function connectWS() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${proto}//${location.host}/ws/backtest/${runId}/`);

    ws.onopen = () => {
      logConn.textContent = "connected";
      logConn.className = "badge badge-success badge-xs";
    };
    ws.onclose = () => {
      logConn.textContent = "offline";
      logConn.className = "badge badge-ghost badge-xs";
    };
    ws.onmessage = (evt) => {
      const msg = JSON.parse(evt.data);
      handleMessage(msg);
    };
  }

  function handleMessage(msg) {
    switch (msg.type) {
      case "status":
        if (msg.status) setStatus(msg.status);
        if (msg.message) progressMsg.textContent = msg.message;
        if (msg.total_bars) {
          el("bt-total-bars").textContent = msg.total_bars;
          progressBars.textContent = `0 / ${msg.total_bars} bars`;
        }
        break;
      case "progress":
        updateProgress(msg);
        break;
      case "log":
        appendLogs([msg]);
        break;
      case "logs":
        appendLogs(msg.entries || []);
        break;
      case "completed":
      case "stopped":
        setStatus(msg.status || msg.type);
        renderSummary(msg.summary);
        renderMetrics(msg.metrics);
        // pull latest trades from the DB (they were persisted incrementally)
        refreshFromApi();
        stopPolling();
        break;
      case "error":
        errorPanel.classList.remove("hidden");
        errorText.textContent = msg.message || "Task failed";
        setStatus("failed");
        stopPolling();
        break;
    }
  }

  // ─── Polling fallback ───────────────────────────────────
  async function refreshFromApi() {
    try {
      const resp = await fetch(`/api/backtest/runs/${runId}/`);
      if (!resp.ok) return;
      const data = await resp.json();
      applyRun(data.run);
      if (data.trades && data.trades.length) {
        appendTrades(data.trades);
        addTradeMarkers(data.trades);
      }
    } catch (_) { /* ignore */ }
  }

  function startPolling() {
    stopPolling();
    pollTimer = setInterval(refreshFromApi, 5000);
  }
  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  }

  // ─── Init ───────────────────────────────────────────────
  setStatus(initialStatus);
  setLayout(currentLayout);

  // Pull the current run + trades once so completed runs show markers
  // immediately (live runs get the same data streamed in via WS).
  refreshFromApi();

  connectWS();
  if (ACTIVE.has(initialStatus)) startPolling();
})();
