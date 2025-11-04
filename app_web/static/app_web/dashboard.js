// app_web/static/app_web/dashboard.js
(function () {
  function start() {
    if (typeof window.Chart === "undefined") {
      console.error("[dashboard] Chart.js not loaded yet.");
      return setTimeout(start, 50);
    }

    const el = document.getElementById("chart-data");
    if (!el) {
      console.error("[dashboard] #chart-data script tag not found.");
      return;
    }

    let data = {};
    try { data = JSON.parse(el.textContent || "{}"); } catch (e) { console.error("[dashboard] Failed to parse chart payload:", e); return; }

    const smallScreen = window.matchMedia('(max-width: 720px)').matches;

    // Utility: currency formatter (simple, consistent)
    function fmtCurrency(v) {
      try {
        const n = Number(v) || 0;
        return '£' + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      } catch (e) { return '£' + String(v); }
    }

    // --- Time series line chart ---
    const tsEl = document.getElementById('tsChart');
    if (tsEl && Array.isArray(data.ts_labels)) {
      const ctx = tsEl.getContext('2d');

      // create gradients for each dataset
      const gIn = ctx.createLinearGradient(0, 0, 0, tsEl.height || 300);
      gIn.addColorStop(0, 'rgba(37,99,235,0.18)');
      gIn.addColorStop(1, 'rgba(37,99,235,0.02)');
      const gOut = ctx.createLinearGradient(0, 0, 0, tsEl.height || 300);
      gOut.addColorStop(0, 'rgba(239,68,68,0.14)');
      gOut.addColorStop(1, 'rgba(239,68,68,0.02)');
      const gNet = ctx.createLinearGradient(0, 0, 0, tsEl.height || 300);
      gNet.addColorStop(0, 'rgba(245,158,11,0.14)');
      gNet.addColorStop(1, 'rgba(245,158,11,0.02)');

      new Chart(ctx, {
        type: 'line',
        data: {
          labels: data.ts_labels,
          datasets: [
            { label: 'Inflow',  data: data.ts_in  || [], borderColor: '#2563eb', backgroundColor: gIn, tension: 0.32, pointRadius: 3, pointHoverRadius: 6, borderWidth: 2 },
            { label: 'Outflow', data: data.ts_out || [], borderColor: '#ef4444', backgroundColor: gOut, tension: 0.32, pointRadius: 3, pointHoverRadius: 6, borderWidth: 2 },
            { label: 'Net',     data: data.ts_net || [], borderColor: '#f59e0b', backgroundColor: gNet, tension: 0.32, pointRadius: 3, pointHoverRadius: 6, borderWidth: 2 }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { position: smallScreen ? 'bottom' : 'top', labels: { boxWidth: 12, padding: 10 } },
            tooltip: {
              callbacks: {
                label: function(ctx) { return ctx.dataset.label + ': ' + fmtCurrency(ctx.parsed.y); }
              },
              padding: 8,
              cornerRadius: 6
            }
          },
          scales: {
            x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: smallScreen ? 6 : 12 }, title: { display: false } },
            y: {
              grid: { color: 'rgba(15,23,42,0.04)', drawBorder: false },
              ticks: { callback: function(v){ return '£' + Number(v).toLocaleString(); } }
            }
          },
          animation: { duration: 700, easing: 'easeOutQuart' },
          layout: { padding: { top: 6, bottom: 6, left: 6, right: 6 } }
        }
      });
    }

    // --- Horizontal category bars ---
    const catEl = document.getElementById('catChart');
    if (catEl && Array.isArray(data.cat_labels)) {
      const ctx2 = catEl.getContext('2d');
      const signs = Array.isArray(data.cat_signs) ? data.cat_signs : [];
      const colors = (data.cat_labels || []).map((_, i) => signs[i] > 0 ? 'rgba(16,185,129,0.95)' : (signs[i] < 0 ? 'rgba(239,68,68,0.95)' : 'rgba(107,114,128,0.7)'));

      new Chart(ctx2, {
        type: 'bar',
        data: { labels: data.cat_labels, datasets: [{ data: data.cat_vals || [], backgroundColor: colors, borderColor: colors, borderWidth: 0, barThickness: 14, borderRadius: 8 }] },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false }, tooltip: { callbacks: { label: function(ctx){ return fmtCurrency(ctx.parsed.x); } }, cornerRadius: 6 } },
          scales: {
            x: { grid: { color: 'rgba(15,23,42,0.04)' }, ticks: { callback: function(v){ return '£' + Number(v).toLocaleString(); } } },
            y: { ticks: { autoSkip: false, maxRotation: 0, font: { size: smallScreen ? 11 : 12 } }, grid: { display: false } }
          },
          animation: { duration: 700, easing: 'easeOutQuart' },
          layout: { padding: { top: 6, bottom: 6 } }
        }
      });
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
