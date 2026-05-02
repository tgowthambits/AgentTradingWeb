(() => {
  const UNDERLYINGS = [
    { label: "SENSEX", symbol: "BSE:SENSEX-INDEX" },
    { label: "NIFTY", symbol: "NSE:NIFTY50-INDEX" },
    { label: "BANKNIFTY", symbol: "NSE:NIFTYBANK-INDEX" },
  ];

  function getCookie(name) {
    const v = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return v ? v.pop() : "";
  }

  let dlg;
  let body;
  let summary;
  let errEl;
  let expirySel;
  let indexWrap;
  let strikeInput;
  let selectionEl;

  let selectedCe = null;
  let selectedPe = null;
  let lastData = null;
  let activeSymbol = UNDERLYINGS[0].symbol;
  let targetTextareaId = "bt-symbols";

  function fmtPct(x) {
    if (x == null || !Number.isFinite(Number(x))) return "–";
    const n = Number(x);
    return (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
  }

  function fmtLakh(n) {
    if (n == null || !Number.isFinite(Number(n))) return "–";
    const v = Number(n);
    if (v >= 1e7) return (v / 1e7).toFixed(2) + "Cr";
    if (v >= 1e5) return (v / 1e5).toFixed(2) + "L";
    if (v >= 1e3) return (v / 1e3).toFixed(2) + "k";
    return String(Math.round(v));
  }

  function barW(val, max) {
    if (!max || !Number.isFinite(val) || val <= 0) return "0%";
    return Math.min(100, Math.round((val / max) * 100)) + "%";
  }

  function updateSelectionText() {
    if (!selectionEl) return;
    selectionEl.textContent = [
      selectedPe ? "PE: " + selectedPe : "PE: (click a put column cell)",
      selectedCe ? "CE: " + selectedCe : "CE: (click a call column cell)",
    ].join(" · ");
  }

  function pickLeg(side, sym) {
    if (!sym) return;
    if (side === "ce") selectedCe = sym;
    else selectedPe = sym;
    if (lastData) renderTable(lastData);
    else updateSelectionText();
  }

  function mkLtpCell(leg, side, rowClsCe, rowClsPe) {
    const td = document.createElement("td");
    const rowCls = side === "ce" ? rowClsCe : rowClsPe;
    td.className =
      "text-right align-top cursor-pointer hover:bg-base-200/80 oc-num text-xs " + rowCls;
    td.dataset.symbol = leg.symbol || "";
    td.dataset.side = side;
    if (selectedCe && leg.symbol === selectedCe) td.classList.add("oc-cell-sel-ce");
    if (selectedPe && leg.symbol === selectedPe) td.classList.add("oc-cell-sel-pe");
    if (!leg.symbol) {
      td.textContent = "–";
      return td;
    }
    const col = Number(leg.ltpchp) >= 0 ? "pnl-positive" : "pnl-negative";
    td.innerHTML =
      "<div>" +
      (leg.ltp != null ? leg.ltp : "–") +
      "</div><div class='text-[10px] " +
      col +
      "'>" +
      fmtPct(leg.ltpchp) +
      "</div>";
    td.addEventListener("click", () => pickLeg(side, leg.symbol));
    return td;
  }

  function mkOiVolCell(leg, side, kind, maxCeVol, maxPeVol, rowClsCe, rowClsPe) {
    const td = document.createElement("td");
    const rowCls = side === "ce" ? rowClsCe : rowClsPe;
    td.className =
      "text-right align-top cursor-pointer hover:bg-base-200/80 text-xs " + rowCls;
    td.dataset.symbol = leg.symbol || "";
    td.dataset.side = side;
    if (selectedCe && leg.symbol === selectedCe) td.classList.add("oc-cell-sel-ce");
    if (selectedPe && leg.symbol === selectedPe) td.classList.add("oc-cell-sel-pe");
    if (!leg.symbol) {
      td.textContent = "–";
      return td;
    }
    const v = kind === "vol" ? Number(leg.volume || 0) : Number(leg.oi || 0);
    const maxV = side === "ce" ? maxCeVol : maxPeVol;
    const bar =
      kind === "vol"
        ? "<div class='oc-bar " +
          (side === "ce" ? "oc-bar-ce" : "oc-bar-pe") +
          " mt-0.5' style='width:" +
          barW(v, maxV) +
          "'></div>"
        : "";
    const txt = kind === "vol" ? fmtLakh(leg.volume) : fmtLakh(leg.oi);
    td.innerHTML = "<div class='oc-num'>" + txt + "</div>" + bar;
    td.addEventListener("click", () => pickLeg(side, leg.symbol));
    return td;
  }

  function renderTable(data) {
    const rows = data.strikes || [];
    const spot = data.spot || 0;
    let maxCeVol = 0;
    let maxPeVol = 0;
    rows.forEach((r) => {
      if (r.ce && r.ce.volume) maxCeVol = Math.max(maxCeVol, Number(r.ce.volume));
      if (r.pe && r.pe.volume) maxPeVol = Math.max(maxPeVol, Number(r.pe.volume));
    });
    body.innerHTML = "";
    rows.forEach((r) => {
      const strike = r.strike;
      const itmCe = spot > 0 && strike < spot;
      const itmPe = spot > 0 && strike > spot;
      const rowClsCe = itmCe ? "oc-itm-ce" : "";
      const rowClsPe = itmPe ? "oc-itm-pe" : "";

      const tr = document.createElement("tr");
      if (r.atm) tr.classList.add("oc-row-atm");

      const ce = r.ce || {};
      const pe = r.pe || {};

      tr.appendChild(mkOiVolCell(ce, "ce", "oi", maxCeVol, maxPeVol, rowClsCe, rowClsPe));
      tr.appendChild(mkOiVolCell(ce, "ce", "vol", maxCeVol, maxPeVol, rowClsCe, rowClsPe));
      tr.appendChild(mkLtpCell(ce, "ce", rowClsCe, rowClsPe));

      const tdStrike = document.createElement("td");
      tdStrike.className =
        "text-center font-mono font-medium bg-base-300/40 align-middle " +
        (r.atm ? "text-primary" : "");
      tdStrike.textContent = String(strike);
      tr.appendChild(tdStrike);

      tr.appendChild(mkLtpCell(pe, "pe", rowClsCe, rowClsPe));
      tr.appendChild(mkOiVolCell(pe, "pe", "vol", maxCeVol, maxPeVol, rowClsCe, rowClsPe));
      tr.appendChild(mkOiVolCell(pe, "pe", "oi", maxCeVol, maxPeVol, rowClsCe, rowClsPe));

      body.appendChild(tr);
    });

    const atmRow = body.querySelector("tr.oc-row-atm");
    if (atmRow) {
      try {
        atmRow.scrollIntoView({ block: "center", behavior: "smooth" });
      } catch {
        atmRow.scrollIntoView(true);
      }
    }
    updateSelectionText();
  }

  function renderSummary(data) {
    const u = data.underlying || {};
    const vx = data.indiavix || {};
    const parts = [];
    parts.push(
      "<span class='opacity-60'>" +
        (u.symbol || activeSymbol) +
        "</span> <span class='oc-num'>" +
        (u.ltp != null ? u.ltp : "–") +
        "</span>"
    );
    if (u.ltpchp != null) {
      const c = Number(u.ltpchp) >= 0 ? "pnl-positive" : "pnl-negative";
      parts.push("<span class='" + c + "'>" + fmtPct(u.ltpchp) + "</span>");
    }
    if (u.fp != null) {
      const fpch = u.fpchp != null ? " <span class='" + (Number(u.fpchp) >= 0 ? "pnl-positive" : "pnl-negative") + "'>" + fmtPct(u.fpchp) + "</span>" : "";
      parts.push("Fut <span class='oc-num'>" + u.fp + "</span>" + fpch);
    }
    if (vx.ltp != null) {
      const vc = Number(vx.ltpchp) >= 0 ? "pnl-positive" : "pnl-negative";
      parts.push(
        "VIX <span class='oc-num'>" +
          vx.ltp +
          "</span> <span class='" +
          vc +
          "'>" +
          fmtPct(vx.ltpchp) +
          "</span>"
      );
    }
    if (data.callOi != null && data.putOi != null && Number(data.callOi) > 0) {
      const pcr = Number(data.putOi) / Number(data.callOi);
      parts.push("PCR <span class='oc-num'>" + pcr.toFixed(2) + "</span>");
    }
    summary.innerHTML = parts.join(" · ");
  }

  function buildExpiryOptions(expiryData, reset) {
    if (reset) expirySel.innerHTML = "";
    if (!expiryData || !expiryData.length) {
      if (!expirySel.options.length) {
        const o = document.createElement("option");
        o.value = "";
        o.textContent = "Expiry";
        expirySel.appendChild(o);
      }
      return;
    }
    if (reset || expirySel.dataset.chainSymbol !== activeSymbol) {
      expirySel.innerHTML = "";
      expiryData.forEach((ex) => {
        const o = document.createElement("option");
        o.value = String(ex.expiry || "");
        const d = (ex.date || "").replace(/-/g, " ");
        o.textContent = d + (ex.expiry_flag ? " (" + ex.expiry_flag + ")" : "");
        expirySel.appendChild(o);
      });
      expirySel.dataset.chainSymbol = activeSymbol;
    }
  }

  async function loadChain(resetExpiry) {
    errEl.classList.add("hidden");
    errEl.textContent = "";
    body.innerHTML =
      "<tr><td colspan='7' class='text-center opacity-50 py-6'>Loading…</td></tr>";
    const ts = (expirySel.value || "").trim();
    const scRaw = (strikeInput.value || "").trim();
    let url = "/api/fyers/options-chain/?symbol=" + encodeURIComponent(activeSymbol);
    if (ts) url += "&timestamp=" + encodeURIComponent(ts);
    if (scRaw) url += "&strikecount=" + encodeURIComponent(scRaw);
    try {
      const resp = await fetch(url);
      const data = await resp.json();
      if (!data.ok) {
        body.innerHTML = "";
        errEl.textContent = data.error || "Failed to load chain";
        errEl.classList.remove("hidden");
        return;
      }
      lastData = data;
      buildExpiryOptions(data.expiryData, !!resetExpiry);
      renderTable(data);
      renderSummary(data);
    } catch (e) {
      errEl.textContent = String(e);
      errEl.classList.remove("hidden");
      body.innerHTML = "";
    }
  }

  function renderIndexTabs() {
    indexWrap.innerHTML = "";
    UNDERLYINGS.forEach((u) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className =
        "join-item btn btn-xs" + (u.symbol === activeSymbol ? " btn-active" : "");
      b.textContent = u.label;
      b.addEventListener("click", () => {
        activeSymbol = u.symbol;
        delete expirySel.dataset.chainSymbol;
        renderIndexTabs();
        loadChain(true);
      });
      indexWrap.appendChild(b);
    });
  }

  function openForTextarea(id) {
    targetTextareaId = id || "bt-symbols";
    selectedCe = null;
    selectedPe = null;
    lastData = null;
    dlg.showModal();
    renderIndexTabs();
    loadChain(true);
  }

  function init() {
    dlg = document.getElementById("dlg-option-chain");
    if (!dlg) return;
    body = document.getElementById("oc-body");
    summary = document.getElementById("oc-summary");
    errEl = document.getElementById("oc-error");
    expirySel = document.getElementById("oc-expiry");
    indexWrap = document.getElementById("oc-index-tabs");
    strikeInput = document.getElementById("oc-strikecount");
    selectionEl = document.getElementById("oc-selection");

    document.querySelectorAll(".js-open-option-chain").forEach((btn) => {
      btn.addEventListener("click", () => {
        openForTextarea(btn.getAttribute("data-textarea-id"));
      });
    });

    dlg.querySelectorAll(".oc-close").forEach((b) => {
      b.addEventListener("click", () => dlg.close());
    });
    document.getElementById("oc-reload").addEventListener("click", () => loadChain(false));
    expirySel.addEventListener("change", () => loadChain(false));

    document.getElementById("oc-apply").addEventListener("click", () => {
      if (!selectedCe || !selectedPe) {
        errEl.textContent = "Select one call cell and one put cell.";
        errEl.classList.remove("hidden");
        return;
      }
      errEl.classList.add("hidden");
      const ta = document.getElementById(targetTextareaId);
      if (ta) ta.value = selectedPe + "\n" + selectedCe;
      dlg.close();
    });

    document.getElementById("oc-save-yaml").addEventListener("click", async () => {
      if (!selectedCe || !selectedPe) {
        errEl.textContent = "Select one call and one put before saving.";
        errEl.classList.remove("hidden");
        return;
      }
      const lotPe = parseInt(document.getElementById("oc-lot-pe").value, 10) || 20;
      const lotCe = parseInt(document.getElementById("oc-lot-ce").value, 10) || 20;
      try {
        const resp = await fetch("/api/trading-config/symbols/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken"),
          },
          body: JSON.stringify({
            put_symbol: selectedPe,
            call_symbol: selectedCe,
            lot_put: lotPe,
            lot_call: lotCe,
          }),
        });
        const out = await resp.json().catch(() => ({}));
        if (!resp.ok || !out.ok) {
          errEl.textContent = out.error || out.message || "Save failed";
          errEl.classList.remove("hidden");
          return;
        }
        errEl.classList.add("hidden");
        const ta = document.getElementById(targetTextareaId);
        if (ta) ta.value = selectedPe + "\n" + selectedCe;
        dlg.close();
      } catch (e) {
        errEl.textContent = String(e);
        errEl.classList.remove("hidden");
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
