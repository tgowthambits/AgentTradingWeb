// TradingView-style multi-chart layout presets.
// Each layout is a grid-template-areas pattern built from single-letter tokens
// ('a', 'b', 'c', ...). A letter that spans multiple cells creates a larger
// region (e.g. big-left + 2-stacked-right uses [["a b"], ["a c"]]).
(function (window) {
  const LAYOUTS = [
    // 1 chart
    { id: "1",   count: 1, rows: ["a"] },

    // 2 charts
    { id: "2v",  count: 2, rows: ["a b"] },                       // side by side
    { id: "2h",  count: 2, rows: ["a", "b"] },                    // top / bottom

    // 3 charts
    { id: "3c",  count: 3, rows: ["a b c"] },                     // 3 columns
    { id: "3r",  count: 3, rows: ["a", "b", "c"] },               // 3 rows
    { id: "3lr", count: 3, rows: ["a b", "a c"] },                // big left, 2 stacked right
    { id: "3rl", count: 3, rows: ["a c", "b c"] },                // 2 stacked left, big right
    { id: "3tb", count: 3, rows: ["a a", "b c"] },                // big top, 2 bottom
    { id: "3bt", count: 3, rows: ["a b", "c c"] },                // 2 top, big bottom

    // 4 charts
    { id: "2x2", count: 4, rows: ["a b", "c d"] },                // 2×2
    { id: "4c",  count: 4, rows: ["a b c d"] },                   // 4 columns
    { id: "4r",  count: 4, rows: ["a", "b", "c", "d"] },          // 4 rows
    { id: "4lr", count: 4, rows: ["a b", "a c", "a d"] },         // big left, 3 stacked right
    { id: "4rl", count: 4, rows: ["a d", "b d", "c d"] },         // 3 stacked left, big right
    { id: "4tb", count: 4, rows: ["a a a", "b c d"] },            // big top, 3 bottom
    { id: "4bt", count: 4, rows: ["a b c", "d d d"] },            // 3 top, big bottom

    // 5 charts
    { id: "5c",  count: 5, rows: ["a b c d e"] },
    { id: "5r",  count: 5, rows: ["a", "b", "c", "d", "e"] },
    { id: "5lr", count: 5, rows: ["a b", "a c", "a d", "a e"] },  // big left, 4 stacked right
    { id: "5tb", count: 5, rows: ["a a a a", "b c d e"] },        // big top, 4 bottom

    // 6 charts
    { id: "3x2", count: 6, rows: ["a b c", "d e f"] },            // 3×2
    { id: "2x3", count: 6, rows: ["a b", "c d", "e f"] },         // 2×3
    { id: "6c",  count: 6, rows: ["a b c d e f"] },
    { id: "6r",  count: 6, rows: ["a", "b", "c", "d", "e", "f"] },

    // 7+
    { id: "3x3", count: 9,  rows: ["a b c", "d e f", "g h i"] },
    { id: "4x4", count: 16, rows: ["a b c d", "e f g h", "i j k l", "m n o p"] },
  ];

  function cellArea(index) {
    return String.fromCharCode(97 + index); // 0 → 'a', 1 → 'b', ...
  }

  function gridStyle(layout) {
    const areas = layout.rows.map(r => `"${r}"`).join(" ");
    const nCols = layout.rows[0].trim().split(/\s+/).length;
    const nRows = layout.rows.length;
    const rowPx = rowHeightFor(nRows);
    return {
      gridTemplateAreas: areas,
      gridTemplateColumns: `repeat(${nCols}, minmax(0, 1fr))`,
      gridTemplateRows: `repeat(${nRows}, ${rowPx}px)`,
      nCols, nRows,
    };
  }

  function rowHeightFor(nRows) {
    if (nRows <= 1) return 420;
    if (nRows === 2) return 280;
    if (nRows === 3) return 220;
    return 180;
  }

  // Render a small SVG icon for the picker menu, based on the layout's regions.
  function layoutIcon(layout, size = 22) {
    const nCols = layout.rows[0].trim().split(/\s+/).length;
    const nRows = layout.rows.length;
    const cellW = size / nCols;
    const cellH = size / nRows;

    // Compute bounding box for each letter (assumes rectangular regions, which
    // is always true for the presets above).
    const regions = new Map();
    for (let r = 0; r < nRows; r++) {
      const tokens = layout.rows[r].trim().split(/\s+/);
      for (let c = 0; c < tokens.length; c++) {
        const tok = tokens[c];
        const reg = regions.get(tok);
        if (!reg) {
          regions.set(tok, { r0: r, r1: r, c0: c, c1: c });
        } else {
          reg.r0 = Math.min(reg.r0, r);
          reg.r1 = Math.max(reg.r1, r);
          reg.c0 = Math.min(reg.c0, c);
          reg.c1 = Math.max(reg.c1, c);
        }
      }
    }

    const rects = [];
    for (const reg of regions.values()) {
      const x = reg.c0 * cellW + 1;
      const y = reg.r0 * cellH + 1;
      const w = (reg.c1 - reg.c0 + 1) * cellW - 2;
      const h = (reg.r1 - reg.r0 + 1) * cellH - 2;
      rects.push(
        `<rect x="${x.toFixed(2)}" y="${y.toFixed(2)}" ` +
        `width="${w.toFixed(2)}" height="${h.toFixed(2)}" ` +
        `rx="1" fill="none" stroke="currentColor" stroke-width="1.2"/>`
      );
    }
    return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">${rects.join("")}</svg>`;
  }

  // Group layouts by their cell count so the picker can render them row-by-row.
  function groupedByCount() {
    const groups = new Map();
    for (const l of LAYOUTS) {
      let arr = groups.get(l.count);
      if (!arr) { arr = []; groups.set(l.count, arr); }
      arr.push(l);
    }
    return Array.from(groups.entries()).sort((a, b) => a[0] - b[0]);
  }

  function findLayout(id) {
    return LAYOUTS.find(l => l.id === id) || LAYOUTS[0];
  }

  // Build a DaisyUI dropdown DOM that, when a tile is clicked, calls
  // onPick(layout) with the chosen spec. The anchor button displays the icon
  // of the currently selected layout.
  function mountPicker(host, initialId, onPick) {
    if (!host) return null;
    host.innerHTML = "";
    host.className = (host.className || "") + " dropdown dropdown-end";

    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.tabIndex = 0;
    trigger.className = "btn btn-sm btn-ghost gap-2 normal-case";
    trigger.title = "Chart layout";
    trigger.innerHTML = `
      <span data-role="icon" class="inline-flex"></span>
      <span class="text-xs opacity-70" data-role="label">Layout</span>
      <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 opacity-60"
           fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
      </svg>`;
    host.appendChild(trigger);

    const menu = document.createElement("div");
    menu.tabIndex = 0;
    menu.className =
      "dropdown-content z-50 mt-2 p-3 shadow-lg bg-base-200 border border-base-300 " +
      "rounded-lg flex flex-col gap-2 max-h-[70vh] overflow-y-auto";
    menu.style.minWidth = "320px";
    host.appendChild(menu);

    const groups = groupedByCount();
    for (const [count, items] of groups) {
      const row = document.createElement("div");
      row.className = "flex items-center gap-2 flex-wrap";

      const countLabel = document.createElement("span");
      countLabel.className =
        "text-[10px] font-mono opacity-40 w-4 text-right shrink-0 select-none";
      countLabel.textContent = String(count);
      row.appendChild(countLabel);

      for (const l of items) {
        const tile = document.createElement("button");
        tile.type = "button";
        tile.dataset.layoutId = l.id;
        tile.title = l.id;
        tile.className =
          "btn btn-xs btn-ghost p-1 border border-transparent hover:border-base-content/20 " +
          "hover:bg-base-300";
        tile.innerHTML = layoutIcon(l, 22);
        tile.addEventListener("click", () => {
          setSelected(l);
          if (document.activeElement && document.activeElement.blur) {
            document.activeElement.blur();
          }
          if (typeof onPick === "function") onPick(l);
        });
        row.appendChild(tile);
      }

      menu.appendChild(row);
    }

    function setSelected(l) {
      const iconSlot = trigger.querySelector('[data-role="icon"]');
      const labelSlot = trigger.querySelector('[data-role="label"]');
      if (iconSlot) iconSlot.innerHTML = layoutIcon(l, 18);
      if (labelSlot) labelSlot.textContent = `${l.count} chart${l.count > 1 ? "s" : ""}`;
      menu.querySelectorAll("button[data-layout-id]").forEach(btn => {
        btn.classList.toggle("border-primary", btn.dataset.layoutId === l.id);
        btn.classList.toggle("text-primary", btn.dataset.layoutId === l.id);
      });
    }

    setSelected(findLayout(initialId));

    return { setSelected };
  }

  window.ChartLayouts = {
    LAYOUTS,
    cellArea,
    gridStyle,
    findLayout,
    layoutIcon,
    groupedByCount,
    mountPicker,
  };
})(window);
