(() => {
  const form = document.getElementById("backtest-form");
  const btnStart = document.getElementById("btn-start-backtest");
  const btnPause = document.getElementById("btn-pause-backtest");
  const btnResume = document.getElementById("btn-resume-backtest");
  const btnStop = document.getElementById("btn-stop-backtest");
  const controls = document.getElementById("bt-controls");
  const statusPanel = document.getElementById("bt-status-panel");
  const livePanel = document.getElementById("bt-live-panel");
  const completedPanel = document.getElementById("bt-completed-panel");
  const errorPanel = document.getElementById("bt-error-panel");

  let ws = null;
  let currentRunId = null;
  let pollTimer = null;

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

  function setBadge(text, variant) {
    const badge = document.getElementById("bt-status-badge");
    badge.textContent = text;
    badge.className = `badge ${variant} badge-xs`;
  }

  function showControlsFor(status) {
    if (["running", "paused", "stopping"].includes(status)) {
      controls.classList.remove("hidden");
    } else {
      controls.classList.add("hidden");
    }
    if (status === "paused") {
      btnPause.classList.add("hidden");
      btnResume.classList.remove("hidden");
    } else {
      btnPause.classList.remove("hidden");
      btnResume.classList.add("hidden");
    }
    btnStop.disabled = status === "stopping";
  }

  // ─── CSV Upload ─────────────────────────────────────────
  const uploadForm = document.getElementById("upload-form");
  if (uploadForm) {
    uploadForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const input = document.getElementById("csv-files");
      if (!input.files.length) return;

      const btn = document.getElementById("btn-upload");
      btn.disabled = true;
      btn.textContent = "Uploading...";

      const fd = new FormData();
      for (const f of input.files) fd.append("files", f);

      try {
        const resp = await fetch("/api/data/upload-multi/", {
          method: "POST",
          headers: { "X-CSRFToken": getCookie("csrftoken") },
          body: fd,
        });
        if (!resp.ok) throw new Error(await resp.text());
        const results = await resp.json();
        refreshDataFiles();
        input.value = "";

        const symbolsEl = document.getElementById("bt-symbols");
        const existing = symbolsEl.value.trim();
        const existingSet = new Set(existing.split("\n").map(s => s.trim()).filter(Boolean));
        for (const r of results) {
          if (!existingSet.has(r.symbol)) {
            symbolsEl.value = (symbolsEl.value.trim() ? symbolsEl.value.trim() + "\n" : "") + r.symbol;
          }
        }
      } catch (err) {
        alert("Upload failed: " + err.message);
      } finally {
        btn.disabled = false;
        btn.textContent = "Upload CSV Files";
      }
    });
  }

  async function refreshDataFiles() {
    try {
      const resp = await fetch("/api/data/files/");
      const files = await resp.json();
      const list = document.getElementById("data-files-list");
      const count = document.getElementById("data-file-count");
      count.textContent = files.length + " files";

      if (files.length === 0) {
        list.innerHTML = '<div class="text-xs opacity-40 py-2 text-center">No data files. Upload CSV below.</div>';
        return;
      }

      list.innerHTML = files.map(f =>
        `<div class="flex items-center justify-between text-xs bg-base-300 rounded px-2 py-1" data-symbol="${f.symbol}">
          <span class="font-mono truncate">${f.symbol}</span>
          <div class="flex items-center gap-2">
            <span class="opacity-50">${f.size_kb}KB</span>
            <button type="button" class="btn-delete-data opacity-40 hover:opacity-100" data-filename="${f.filename}">&times;</button>
          </div>
        </div>`
      ).join("");
      bindDeleteButtons();
    } catch (e) { /* ignore */ }
  }

  function bindDeleteButtons() {
    document.querySelectorAll(".btn-delete-data").forEach(btn => {
      btn.addEventListener("click", async () => {
        const fn = btn.dataset.filename;
        await fetch(`/api/data/files/${fn}/`, {
          method: "DELETE",
          headers: { "X-CSRFToken": getCookie("csrftoken") },
        });
        refreshDataFiles();
      });
    });
  }
  bindDeleteButtons();

  // ─── Backtest Start ─────────────────────────────────────
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    btnStart.disabled = true;
    btnStart.textContent = "Starting...";

    errorPanel.classList.add("hidden");
    completedPanel.classList.add("hidden");

    const symbolsRaw = document.getElementById("bt-symbols").value.trim();
    const symbols = symbolsRaw.split("\n").map(s => s.trim()).filter(Boolean);
    const startDate = document.getElementById("bt-start").value.replace("T", " ");
    const endDate = document.getElementById("bt-end").value.replace("T", " ");
    const resolution = document.getElementById("bt-resolution").value;
    const configId = document.getElementById("bt-config").value || null;

    statusPanel.classList.remove("hidden");
    setBadge("queued", "badge-info");
    document.getElementById("bt-message").textContent = "Submitting to Celery worker...";

    try {
      const resp = await fetch("/api/backtest/run/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({
          symbols,
          start_date: startDate,
          end_date: endDate,
          resolution,
          config_id: configId ? parseInt(configId) : null,
        }),
      });

      if (!resp.ok) throw new Error(await resp.text());

      const data = await resp.json();
      currentRunId = data.id;

      livePanel.classList.remove("hidden");
      setBadge("running", "badge-warning");
      showControlsFor("running");
      document.getElementById("bt-message").textContent = "Connecting to stream...";

      connectWS(currentRunId);
      startPolling(currentRunId);

    } catch (err) {
      showError(err.message || "Failed to start backtest");
    }
  });

  // ─── Control Buttons ────────────────────────────────────
  btnPause.addEventListener("click", () => sendControl("pause"));
  btnResume.addEventListener("click", () => sendControl("resume"));
  btnStop.addEventListener("click", () => {
    if (!confirm("Stop this backtest? Already collected trades will be preserved.")) return;
    sendControl("stop");
  });

  async function sendControl(action) {
    if (!currentRunId) return;
    try {
      const resp = await fetch(`/api/backtest/runs/${currentRunId}/${action}/`, {
        method: "POST",
        headers: { "X-CSRFToken": getCookie("csrftoken") },
      });
      if (!resp.ok) throw new Error(await resp.text());
    } catch (err) {
      alert(`${action} failed: ${err.message}`);
    }
  }

  function showError(msg) {
    errorPanel.classList.remove("hidden");
    document.getElementById("bt-error-text").textContent = msg;
    setBadge("failed", "badge-error");
    showControlsFor("failed");
    btnStart.disabled = false;
    btnStart.textContent = "Start Backtest";
    stopPolling();
  }

  // ─── WebSocket ──────────────────────────────────────────
  function connectWS(runId) {
    try {
      const proto = location.protocol === "https:" ? "wss:" : "ws:";
      ws = new WebSocket(`${proto}//${location.host}/ws/backtest/${runId}/`);

      ws.onopen = () => {
        document.getElementById("bt-message").textContent = "Connected. Waiting for engine...";
      };

      ws.onmessage = (evt) => {
        const msg = JSON.parse(evt.data);
        handleMessage(msg);
      };

      ws.onclose = () => {};
      ws.onerror = () => {};
    } catch (e) {
      // WS not available, polling will handle updates
    }
  }

  // ─── Polling Fallback (kept for resilience) ─────────────
  function startPolling(runId) {
    stopPolling();
    pollTimer = setInterval(() => pollStatus(runId), 3000);
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  async function pollStatus(runId) {
    try {
      const resp = await fetch(`/api/backtest/runs/${runId}/status/`);
      if (!resp.ok) return;
      const data = await resp.json();

      if (data.status === "completed") {
        stopPolling();
        handleMessage({
          type: "completed",
          status: "completed",
          summary: data.summary,
          metrics: data.metrics,
          trade_count: data.trade_count,
        });
      } else if (data.status === "stopped") {
        stopPolling();
        handleMessage({
          type: "stopped",
          status: "stopped",
          summary: data.summary,
          metrics: data.metrics,
          trade_count: data.trade_count,
        });
      } else if (data.status === "failed") {
        stopPolling();
        showError(data.error_message || "Backtest failed");
      }
    } catch (e) { /* ignore */ }
  }

  // ─── Message Handler ────────────────────────────────────
  function handleMessage(msg) {
    switch (msg.type) {
      case "status":
        document.getElementById("bt-message").textContent = msg.message || "";
        if (msg.status === "paused") {
          setBadge("paused", "badge-ghost");
          showControlsFor("paused");
        } else if (msg.status === "running") {
          setBadge("running", "badge-warning");
          showControlsFor("running");
        } else if (msg.status === "stopping") {
          setBadge("stopping", "badge-ghost");
          showControlsFor("stopping");
        }
        break;

      case "progress":
        livePanel.classList.remove("hidden");
        updateProgress(msg);
        break;

      case "completed":
        onComplete(msg, "completed");
        break;

      case "stopped":
        onComplete(msg, "stopped");
        break;

      case "error":
        showError(msg.message || "Backtest failed");
        break;
    }
  }

  function updateProgress(msg) {
    const pct = msg.progress_pct || 0;
    document.getElementById("bt-progress-bar").value = pct;
    document.getElementById("bt-progress-text").textContent = `${pct}%`;
    document.getElementById("bt-bars-text").textContent = `${msg.processed_bars || 0} / ${msg.total_bars || 0} bars`;
    document.getElementById("bt-running-pnl").innerHTML = formatPnl(msg.running_pnl);
    document.getElementById("bt-trade-count").textContent = msg.trade_count || 0;
    document.getElementById("bt-iteration").textContent = msg.iteration || 0;

    const positions = msg.open_positions || [];
    document.getElementById("bt-open-count").textContent = positions.length;

    const posBody = document.getElementById("bt-positions-body");
    if (positions.length > 0) {
      posBody.innerHTML = positions.map(p =>
        `<tr>
          <td class="text-xs">${p.symbol}</td>
          <td class="text-xs">${p.type}</td>
          <td class="font-mono text-xs">${parseFloat(p.entry_price).toFixed(2)}</td>
          <td class="font-mono text-xs">${p.quantity}</td>
        </tr>`
      ).join("");
    } else {
      posBody.innerHTML = '<tr><td colspan="4" class="text-center opacity-30 py-2">None</td></tr>';
    }

    const signals = msg.latest_results || [];
    const signalsList = document.getElementById("bt-signals-list");
    signalsList.innerHTML = signals.map(s => {
      const cls = s.signal === "BUY" ? "signal-buy" : s.signal === "SELL" ? "signal-sell" : "signal-hold";
      return `<span class="badge badge-ghost badge-sm font-mono"><span class="${cls}">${s.signal}</span> ${s.symbol.split(":").pop()} @ ${parseFloat(s.price).toFixed(2)}</span>`;
    }).join("");

    document.getElementById("bt-message").textContent = `Processing iteration ${msg.iteration}...`;
  }

  function onComplete(msg, finalStatus) {
    stopPolling();
    showControlsFor(finalStatus);

    if (finalStatus === "stopped") {
      setBadge("stopped", "badge-ghost");
      document.getElementById("bt-message").textContent = "Stopped by user.";
    } else {
      setBadge("completed", "badge-success");
      document.getElementById("bt-progress-bar").value = 100;
      document.getElementById("bt-progress-text").textContent = "100%";
      document.getElementById("bt-message").textContent = "Backtest complete.";
    }

    completedPanel.classList.remove("hidden");

    const s = msg.summary || {};
    const m = msg.metrics || {};

    document.getElementById("bt-final-pnl").innerHTML = formatPnl(s.total_pnl);
    document.getElementById("bt-final-return").textContent = `${s.returns_pct || 0}%`;
    document.getElementById("bt-final-winrate").textContent = `${m.win_rate || 0}%`;
    document.getElementById("bt-final-trades").textContent = m.total_trades || msg.trade_count || 0;
    document.getElementById("bt-final-avgwin").textContent = m.avg_win ?? "--";
    document.getElementById("bt-final-avgloss").textContent = m.avg_loss ?? "--";
    document.getElementById("bt-final-pf").textContent = m.profit_factor ?? "--";
    document.getElementById("bt-final-expectancy").textContent = m.expectancy ?? "--";

    if (currentRunId) {
      document.getElementById("bt-detail-link").href = `/backtest/results/${currentRunId}/`;
    }

    btnStart.disabled = false;
    btnStart.textContent = "Start Backtest";

    if (ws) ws.close();
  }
})();
