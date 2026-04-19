(() => {
  function getCookie(name) {
    const v = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return v ? v.pop() : "";
  }

  function gatherConfig() {
    const symbolsRaw = document.getElementById("cfg-symbols").value.trim();
    const symbols = symbolsRaw.split("\n").map(s => s.trim()).filter(Boolean);

    let lotSizes = {};
    try {
      lotSizes = JSON.parse(document.getElementById("cfg-lot-sizes").value || "{}");
    } catch (e) { /* ignore parse errors */ }

    const indicators = {};
    document.querySelectorAll("[data-indicator]").forEach(el => {
      const name = el.dataset.indicator;
      const toggle = el.querySelector(".ind-toggle");
      const enabled = toggle ? toggle.checked : false;

      const params = {};
      el.querySelectorAll("[data-param]").forEach(inp => {
        const key = inp.dataset.param;
        let val = inp.value;
        if (!isNaN(val) && val !== "") val = parseFloat(val);
        if (val === "true") val = true;
        if (val === "false") val = false;
        params[key] = val;
      });

      const weight = params.weight || 1.0;
      delete params.weight;

      indicators[name] = {
        enabled,
        weight,
        ...params,
      };
    });

    const val = (id) => document.getElementById(id)?.value || "";
    const num = (id) => parseFloat(document.getElementById(id)?.value) || 0;
    const checked = (id) => document.getElementById(id)?.checked || false;

    return {
      symbols,
      lot_sizes: lotSizes,
      aggregation_strategy: val("cfg-agg-strategy"),
      min_agreement: num("cfg-min-agreement"),
      resolution: "5S",
      indicators,
      trading: {
        default_quantity: num("cfg-default-qty"),
        refresh_interval: num("cfg-refresh"),
        allow_buy: checked("cfg-allow-buy"),
        allow_sell: checked("cfg-allow-sell"),
        paper_trading: checked("cfg-paper"),
        auto_trade: checked("cfg-auto-trade"),
        lookback_bars: num("cfg-trading-lookback"),
        lot_sizes: lotSizes,
      },
      risk_management: {
        risk_per_trade_pct: num("cfg-risk-pct"),
        max_position_size: num("cfg-max-pos-size"),
        max_positions: num("cfg-max-positions"),
        stop_loss: {
          method: val("cfg-sl-method"),
          max_loss_per_trade: num("cfg-sl-max-loss"),
          atr_multiplier: num("cfg-sl-atr"),
        },
        profit_targets: {
          enabled: checked("cfg-pt-enabled"),
          target_1: { ratio: num("cfg-pt1-ratio"), exit_pct: num("cfg-pt1-pct") },
        },
        trailing_stop: {
          enabled: checked("cfg-ts-enabled"),
          activation_ratio: num("cfg-ts-activation"),
          trail_atr_multiplier: num("cfg-ts-trail"),
        },
        daily_limits: {
          max_loss_amount: num("cfg-daily-max-loss"),
          max_trades_per_day: num("cfg-daily-max-trades"),
          max_positions: num("cfg-daily-max-pos"),
        },
        time_exit: {
          enabled: checked("cfg-te-enabled"),
          max_hold_minutes: num("cfg-te-hold"),
          force_close_eod: checked("cfg-te-eod"),
        },
      },
      backtest: {
        initial_capital: num("cfg-bt-capital"),
        entry_slippage: num("cfg-bt-entry-slip"),
        exit_slippage: num("cfg-bt-exit-slip"),
        speed: val("cfg-bt-speed"),
        resolution: val("cfg-bt-resolution"),
        lookback_bars: num("cfg-bt-lookback"),
      },
    };
  }

  // Save config
  document.getElementById("btn-save-config").addEventListener("click", () => {
    document.getElementById("save-config-modal").showModal();
  });

  document.getElementById("btn-confirm-save").addEventListener("click", async () => {
    const name = document.getElementById("save-config-name").value.trim();
    if (!name) return;

    const config = gatherConfig();

    try {
      const resp = await fetch("/api/configs/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({ name, config_json: config }),
      });

      if (!resp.ok) throw new Error(await resp.text());

      document.getElementById("save-config-modal").close();
      location.reload();
    } catch (err) {
      alert("Save failed: " + err.message);
    }
  });

  // Load preset
  document.getElementById("btn-load-preset").addEventListener("click", async () => {
    const id = document.getElementById("cfg-preset-select").value;
    if (!id) return;

    try {
      const resp = await fetch(`/api/configs/${id}/`);
      if (!resp.ok) throw new Error("Failed to load");
      const data = await resp.json();
      applyConfig(data.config_json);
    } catch (err) {
      alert("Load failed: " + err.message);
    }
  });

  // Load default
  document.getElementById("btn-load-default").addEventListener("click", async () => {
    try {
      const resp = await fetch("/api/configs/default/");
      if (!resp.ok) throw new Error("Failed to load default");
      const data = await resp.json();
      applyConfig(data.trading || {});
    } catch (err) {
      alert("Reset failed: " + err.message);
    }
  });

  function applyConfig(cfg) {
    if (cfg.symbols) {
      const syms = Array.isArray(cfg.symbols) ? cfg.symbols : [];
      document.getElementById("cfg-symbols").value = syms.join("\n");
    }

    if (cfg.lot_sizes) {
      document.getElementById("cfg-lot-sizes").value = JSON.stringify(cfg.lot_sizes, null, 2);
    }

    if (cfg.indicators) {
      for (const [name, ind] of Object.entries(cfg.indicators)) {
        const el = document.querySelector(`[data-indicator="${name}"]`);
        if (!el) continue;
        const toggle = el.querySelector(".ind-toggle");
        if (toggle) toggle.checked = !!ind.enabled;

        el.querySelectorAll("[data-param]").forEach(inp => {
          const key = inp.dataset.param;
          if (key === "weight") inp.value = ind.weight || 1.0;
          else if (ind[key] !== undefined) inp.value = ind[key];
        });
      }
    }

    const t = cfg.trading || {};
    if (t.default_quantity) document.getElementById("cfg-default-qty").value = t.default_quantity;
    if (t.refresh_interval) document.getElementById("cfg-refresh").value = t.refresh_interval;
    if (t.allow_buy !== undefined) document.getElementById("cfg-allow-buy").checked = t.allow_buy;
    if (t.allow_sell !== undefined) document.getElementById("cfg-allow-sell").checked = t.allow_sell;
    if (t.lookback_bars !== undefined) document.getElementById("cfg-trading-lookback").value = t.lookback_bars;

    const r = cfg.risk_management || {};
    if (r.risk_per_trade_pct) document.getElementById("cfg-risk-pct").value = r.risk_per_trade_pct;

    const bt = cfg.backtest || {};
    if (bt.initial_capital) document.getElementById("cfg-bt-capital").value = bt.initial_capital;
    if (bt.entry_slippage !== undefined) document.getElementById("cfg-bt-entry-slip").value = bt.entry_slippage;
    if (bt.exit_slippage !== undefined) document.getElementById("cfg-bt-exit-slip").value = bt.exit_slippage;
    if (bt.lookback_bars !== undefined) document.getElementById("cfg-bt-lookback").value = bt.lookback_bars;
  }

  // Min agreement range display
  const rangeInput = document.getElementById("cfg-min-agreement");
  if (rangeInput) {
    rangeInput.addEventListener("input", () => {
      document.getElementById("cfg-min-agreement-val").textContent = rangeInput.value;
    });
  }
})();
