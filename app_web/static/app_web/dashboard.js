// app_web/static/app_web/dashboard.js
(function () {
  function start() {
    // 1) Is Chart.js available?
    if (typeof window.Chart === "undefined") {
      console.error("[dashboard] Chart.js not loaded yet.");
      return setTimeout(start, 50); // try again shortly
    }

    // 2) Find and parse the embedded JSON payload
    const el = document.getElementById("chart-data");
    if (!el) {
      console.error("[dashboard] #chart-data script tag not found.");
      return;
    }

    let data;
    try {
      data = JSON.parse(el.textContent || "{}");
    } catch (e) {
      console.error("[dashboard] Failed to parse chart payload:", e);
      return;
    }

    const smallScreen = window.matchMedia('(max-width: 720px)').matches;

    // 3) Build charts only if canvases exist
    const tsCtx = document.getElementById("tsChart");
    if (tsCtx && Array.isArray(data.ts_labels)) {
      new Chart(tsCtx, {
        type: "line",
        data: {
          labels: data.ts_labels,
          datasets: [
            { label: "Inflow",  data: data.ts_in  || [], tension: 0.25, borderColor: '#2563eb', backgroundColor: 'rgba(37,99,235,0.08)' },
            { label: "Outflow", data: data.ts_out || [], tension: 0.25, borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.06)' },
            { label: "Net",     data: data.ts_net || [], tension: 0.25, borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.06)' }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: smallScreen ? 'bottom' : 'bottom', labels: { boxWidth: 12, padding: 8 } } },
          scales: {
            x: { ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: smallScreen ? 6 : 12 } },
            y: { beginAtZero: true }
          }
        }
      });
    } else {
      console.warn("[dashboard] tsChart canvas or data missing.");
    }

    const catCtx = document.getElementById("catChart");
    if (catCtx && Array.isArray(data.cat_labels)) {
      // determine colors per bar based on provided sign array (1 = inflow, -1 = outflow, 0 = neutral)
      var signs = Array.isArray(data.cat_signs) ? data.cat_signs : [];
      var colors = (data.cat_labels || []).map(function(_, i){
        var s = signs[i] || 0;
        if (s > 0) return 'rgba(16,185,129,0.85)'; // green (inflow)
        if (s < 0) return 'rgba(239,68,68,0.85)';  // red (outflow)
        return 'rgba(107,114,128,0.6)'; // gray neutral
      });

      new Chart(catCtx, {
        type: "bar",
        data: { labels: data.cat_labels, datasets: [{ label: "Amount", data: data.cat_vals || [], backgroundColor: colors, borderColor: colors, borderWidth: 1 }] },
        options: {
          indexAxis: "y",
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { x: { beginAtZero: true, ticks: { maxTicksLimit: smallScreen ? 4 : 8 } }, y: { ticks: { font: { size: smallScreen ? 10 : 12 } } } }
        }
      });
    } else {
      console.warn("[dashboard] catChart canvas or data missing.");
    }
  }

  // Run after DOM is ready so canvases & #chart-data exist
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
