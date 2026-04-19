(() => {
  const form = document.getElementById("live-form");
  const btnStart = document.getElementById("btn-start-live");
  const btnPause = document.getElementById("btn-pause-live");
  const btnResume = document.getElementById("btn-resume-live");
  const btnStop = document.getElementById("btn-stop-live");
  const indicator = document.getElementById("live-indicator");
  const statusText = document.getElementById("live-status-text");

  let ws = null;
  let sessionId = null;

  // ─── Chart grid ────────────────────────────────────────
  const gridEl = document.getElementById("live-chart-grid");
  const pickerHost = document.getElementById("live-layout-picker");

  const barsBySymbol = new Map();
  const barIndexBySymbol = new Map();
  const markersBySymbol = new Map();
  const markersOrderIds = new Set();
  const openMarkersBySymbol = new Map(); // symbol -> Map<orderId, marker>
  const SYMBOLS = [];                     // discovered at runtime from bars

  let cells = [];
  let currentLayout = (window.ChartLayouts && window.ChartLayouts.findLayout("1")) || null;

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

  function cellsForSymbol(sym) {
    if (!sym) return [];
    const out = [];
    for (const c of cells) if (c.activeSymbol === sym) out.push(c);
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
    if (!SYMBOLS.length) {
      const opt = document.createElement("option");
      opt.value = ""; opt.textContent = "--";
      sel.appendChild(opt);
    } else {
      for (const s of SYMBOLS) {
        const opt = document.createElement("option");
        opt.value = s; opt.textContent = s;
        if (s === initialSymbol) opt.selected = true;
        sel.appendChild(opt);
      }
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
    for (const c of cells) redrawCell(c);
  }

  if (pickerHost && window.ChartLayouts) {
    window.ChartLayouts.mountPicker(pickerHost, "1", setLayout);
  }

  function registerSymbol(sym) {
    if (!sym || SYMBOLS.includes(sym)) return;
    SYMBOLS.push(sym);
    for (const c of cells) {
      if (c.sel.options.length === 1 && c.sel.options[0].value === "") {
        c.sel.options[0].remove();
      }
      const opt = document.createElement("option");
      opt.value = sym; opt.textContent = sym;
      c.sel.appendChild(opt);
      if (!c.activeSymbol) {
        c.activeSymbol = sym;
        c.sel.value = sym;
        redrawCell(c);
      }
    }
  }

  function ingestBars(barsBySym) {
    if (!barsBySym) return;
    for (const [sym, list] of Object.entries(barsBySym)) {
      if (!Array.isArray(list) || !list.length) continue;
      registerSymbol(sym);

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
          Object.assign(existing, {
            open: bar.open, high: bar.high, low: bar.low,
            close: bar.close, volume: bar.volume,
          });
          for (const c of live) c.series.update(existing);
          continue;
        }
        const rec = {
          time: t,
          open: bar.open, high: bar.high, low: bar.low,
          close: bar.close, volume: bar.volume,
        };
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

  function buildMarkers(sym) {
    const closed = markersBySymbol.get(sym) || [];
    const opens = openMarkersBySymbol.get(sym);
    const all = opens ? closed.concat(Array.from(opens.values())) : closed.slice();
    all.sort((a, b) => a.time - b.time);
    return all;
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

      const oid = t.order_id;
      if (oid != null) {
        if (markersOrderIds.has(oid)) continue;
        markersOrderIds.add(oid);
      }

      touched.add(sym);
      let list = markersBySymbol.get(sym);
      if (!list) { list = []; markersBySymbol.set(sym, list); }

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
      const opens = openMarkersBySymbol.get(sym);
      if (opens && t.order_id != null) opens.delete(t.order_id);
    }
    for (const sym of touched) {
      const markers = buildMarkers(sym);
      for (const c of cellsForSymbol(sym)) c.series.setMarkers(markers);
    }
  }

  function syncOpenMarkers(positions) {
    if (!Array.isArray(positions)) return;
    const seenPerSym = new Map();
    const touched = new Set();
    for (const p of positions) {
      const sym = p.symbol;
      const ts = tsFromIso(p.entry_time);
      if (!sym || ts == null || p.order_id == null) continue;
      touched.add(sym);
      let symMap = openMarkersBySymbol.get(sym);
      if (!symMap) { symMap = new Map(); openMarkersBySymbol.set(sym, symMap); }
      const isLong = (p.type || "").toUpperCase() === "LONG";
      symMap.set(p.order_id, {
        time: ts,
        position: isLong ? "belowBar" : "aboveBar",
        color: "#f59e0b",
        shape: isLong ? "arrowUp" : "arrowDown",
        text: `OPEN ${isLong ? "LONG" : "SHORT"} ${Number(p.entry_price).toFixed(2)}`,
      });
      let s = seenPerSym.get(sym);
      if (!s) { s = new Set(); seenPerSym.set(sym, s); }
      s.add(p.order_id);
    }
    for (const [sym, symMap] of openMarkersBySymbol) {
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

  setLayout(currentLayout);

  function getCookie(name) {
    const v = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return v ? v.pop() : "";
  }

  function formatPnl(val) {
    const n = parseFloat(val) || 0;
    const cls = n >= 0 ? "pnl-positive" : "pnl-negative";
    const sign = n >= 0 ? "+" : "";
    return `<span class="${cls}">${sign}${n.toFixed(2)}</span>`;
  }

  function appendLog(text) {
    const log = document.getElementById("live-log");
    const ts = new Date().toLocaleTimeString();
    const div = document.createElement("div");
    div.textContent = `[${ts}] ${text}`;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
  }

  function setState(state) {
    const map = {
      idle:     { cls: "status-neutral", text: "Idle" },
      running:  { cls: "status-success", text: "Running" },
      paused:   { cls: "status-warning", text: "Paused" },
      stopping: { cls: "status-warning", text: "Stopping..." },
      stopped:  { cls: "status-neutral", text: "Stopped" },
      error:    { cls: "status-error",   text: "Error" },
    };
    const m = map[state] || map.idle;
    indicator.className = `status status-sm ${m.cls}`;
    statusText.textContent = m.text;

    btnStart.classList.toggle("hidden", state !== "idle" && state !== "stopped" && state !== "error");
    btnPause.classList.toggle("hidden", state !== "running");
    btnResume.classList.toggle("hidden", state !== "paused");
    btnStop.classList.toggle("hidden", !["running", "paused", "stopping"].includes(state));
  }
  setState("idle");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    btnStart.disabled = true;

    const symbolsRaw = document.getElementById("live-symbols").value.trim();
    const symbols = symbolsRaw.split("\n").map(s => s.trim()).filter(Boolean);
    const configId = document.getElementById("live-config").value || null;

    try {
      const resp = await fetch("/api/live/start/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({
          symbols,
          config_id: configId ? parseInt(configId) : null,
        }),
      });

      if (!resp.ok) throw new Error(await resp.text());

      const data = await resp.json();
      sessionId = data.id;

      document.getElementById("live-session-id").textContent = sessionId;
      setState("running");
      appendLog(`Session #${sessionId} submitted to Celery with ${symbols.length} symbols`);
      appendLog(`Opening detail page…`);

      // Hand off to the full detail page (charts, trades, logs, controls).
      window.location.href = `/live/sessions/${sessionId}/`;

    } catch (err) {
      appendLog(`Error: ${err.message}`);
      setState("error");
      btnStart.disabled = false;
    }
  });

  btnPause.addEventListener("click", () => sendControl("pause"));
  btnResume.addEventListener("click", () => sendControl("resume"));
  btnStop.addEventListener("click", () => {
    if (!confirm("Stop this live session?")) return;
    sendControl("stop");
  });

  async function sendControl(action) {
    if (!sessionId) return;
    try {
      const resp = await fetch(`/api/live/${action}/${sessionId}/`, {
        method: "POST",
        headers: { "X-CSRFToken": getCookie("csrftoken") },
      });
      if (!resp.ok) throw new Error(await resp.text());
      if (action === "stop") setState("stopping");
      appendLog(`Control: ${action}`);
    } catch (err) {
      appendLog(`${action} error: ${err.message}`);
    }
  }

  function connectWS(id) {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${proto}//${location.host}/ws/live/${id}/`);

    ws.onopen = () => appendLog("WebSocket connected");
    ws.onmessage = (evt) => {
      const msg = JSON.parse(evt.data);
      handleMessage(msg);
    };
    ws.onclose = () => appendLog("WebSocket disconnected");
  }

  function handleMessage(msg) {
    switch (msg.type) {
      case "status":
        if (msg.status) setState(msg.status);
        appendLog(msg.message || `Status: ${msg.status}`);
        break;

      case "update":
        document.getElementById("live-pnl").innerHTML = formatPnl(msg.total_pnl);
        document.getElementById("live-trades").textContent = msg.trade_count || 0;
        document.getElementById("live-iteration").textContent = msg.iteration || 0;

        if (msg.bars) ingestBars(msg.bars);
        if (msg.open_positions) syncOpenMarkers(msg.open_positions);
        if (msg.new_trades) addTradeMarkers(msg.new_trades);

        const results = msg.results || [];
        const tbody = document.getElementById("live-signals-body");
        if (results.length > 0) {
          tbody.innerHTML = results.map(r => {
            const cls = r.signal === "BUY" ? "signal-buy" : r.signal === "SELL" ? "signal-sell" : "signal-hold";
            const timeStr = r.time
              ? new Date(r.time).toLocaleTimeString()
              : new Date().toLocaleTimeString();
            return `<tr>
              <td class="text-xs">${r.symbol}</td>
              <td class="${cls} text-xs">${r.signal}</td>
              <td class="font-mono text-xs">${parseFloat(r.price).toFixed(2)}</td>
              <td class="text-xs opacity-50">${timeStr}</td>
            </tr>`;
          }).join("");
        }

        if (msg.iteration % 5 === 0) {
          appendLog(`Iteration ${msg.iteration}: PnL ${msg.total_pnl}, Trades ${msg.trade_count}`);
        }
        break;

      case "stopped":
        appendLog(`Session stopped. Final PnL: ${msg.total_pnl}`);
        setState("stopped");
        btnStart.disabled = false;
        if (ws) ws.close();
        break;

      case "error":
        appendLog(`Error: ${msg.message}`);
        setState("error");
        btnStart.disabled = false;
        break;
    }
  }
})();
