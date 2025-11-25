/**
 * Dashboard Widgets JavaScript
 * Handles customizable dashboard with drag & drop widgets
 */

(function() {
  'use strict';

  console.log('Dashboard Widgets JS Loading...');

  // Global state
  let grid;
  let widgets = {};
  let charts = {};
  let saveTimeout;
  let currentDateRange = 'last7days'; // Default to current week (Daily view)
  let isEditMode = false; // Track edit mode state
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

  // Widget metadata with default sizes (users can resize freely)
  // Note: cellHeight is 50px, so h:3 = 150px, h:8 = 400px, etc.
  const WIDGET_META = {
    // KPI Widgets - 200px wide × 150px tall (w:2 columns, h:3 cells @ 50px each)
    'kpi-total-income': { title: 'Total Income', w: 2, h: 3, type: 'kpi', minW: 2, minH: 2 },
    'kpi-total-expenses': { title: 'Total Expenses', w: 2, h: 3, type: 'kpi', minW: 2, minH: 2 },
    'kpi-net-cash-flow': { title: 'Net Cash Flow', w: 2, h: 3, type: 'kpi', minW: 2, minH: 2 },
    'kpi-avg-transaction': { title: 'Avg Transaction', w: 2, h: 3, type: 'kpi', minW: 2, minH: 2 },
    'kpi-transaction-count': { title: 'Transaction Count', w: 2, h: 3, type: 'kpi', minW: 2, minH: 2 },
    'kpi-budget-progress': { title: 'Budget Progress', w: 2, h: 3, type: 'kpi', minW: 2, minH: 2 },
    'kpi-burn-rate': { title: 'Burn Rate', w: 2, h: 3, type: 'kpi', minW: 2, minH: 2 },
    'kpi-active-projects': { title: 'Active Projects', w: 2, h: 3, type: 'kpi', minW: 2, minH: 2 },
    'kpi-pending-invoices': { title: 'Pending Invoices', w: 2, h: 3, type: 'kpi', minW: 2, minH: 2 },
    'kpi-overdue-invoices': { title: 'Overdue Invoices', w: 2, h: 3, type: 'kpi', minW: 2, minH: 2 },

    // Chart Widgets - 6 columns wide × 8 cells tall (8 × 50px = 400px)
    'chart-revenue-expense': { title: 'Revenue vs Expenses', w: 6, h: 8, type: 'chart', minW: 4, minH: 6 },
    'chart-expense-pie': { title: 'Expense Breakdown', w: 6, h: 8, type: 'chart', minW: 3, minH: 6 },
    'chart-income-pie': { title: 'Income Breakdown', w: 6, h: 8, type: 'chart', minW: 3, minH: 6 },
    'chart-trend-line': { title: 'Trend Line', w: 6, h: 8, type: 'chart', minW: 4, minH: 6 },
    'chart-waterfall': { title: 'Cash Flow Waterfall', w: 6, h: 8, type: 'chart', minW: 4, minH: 6 },
    'chart-budget-performance': { title: 'Budget Performance', w: 6, h: 8, type: 'chart', minW: 4, minH: 6 },
    'chart-category-heatmap': { title: 'Category Heatmap', w: 6, h: 8, type: 'chart', minW: 3, minH: 6 },
    'chart-money-flow-sankey': { title: 'Money Flow', w: 6, h: 8, type: 'chart', minW: 3, minH: 6 },

    // List Widgets - 4 columns wide × 8 cells tall (8 × 50px = 400px)
    'list-recent-transactions': { title: 'Recent Transactions', w: 4, h: 8, type: 'list', minW: 3, minH: 4 },
    'list-upcoming-bills': { title: 'Upcoming Bills', w: 4, h: 8, type: 'list', minW: 3, minH: 4 },
    'list-budget-alerts': { title: 'Budget Alerts', w: 4, h: 8, type: 'list', minW: 3, minH: 4 },
    'list-recent-invoices': { title: 'Recent Invoices', w: 4, h: 8, type: 'list', minW: 3, minH: 4 },

    // Summary Widgets - 4 columns × 6 cells (6 × 50px = 300px)
    'summary-financial': { title: 'Financial Summary', w: 4, h: 6, type: 'summary', minW: 3, minH: 4 },
    'summary-month-comparison': { title: 'Month Comparison', w: 4, h: 6, type: 'summary', minW: 3, minH: 4 },
  };

  // Configure Chart.js defaults for modern tooltips
  Chart.defaults.plugins.tooltip = {
    enabled: true,
    mode: 'index',
    intersect: false,
    backgroundColor: 'rgba(255, 255, 255, 0.98)',
    titleColor: '#111827',
    bodyColor: '#374151',
    borderColor: 'rgba(229, 231, 235, 0.8)',
    borderWidth: 1,
    padding: 12,
    cornerRadius: 12,
    displayColors: true,
    boxWidth: 12,
    boxHeight: 12,
    boxPadding: 6,
    usePointStyle: true,
    titleFont: {
      size: 13,
      weight: '600'
    },
    bodyFont: {
      size: 12,
      weight: '400'
    },
    callbacks: {
      title: function(context) {
        return context[0].label || '';
      },
      label: function(context) {
        let label = context.dataset.label || '';
        if (label) {
          label += ': ';
        }
        if (context.parsed.y !== null) {
          label += '£' + context.parsed.y.toLocaleString('en-GB', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
          });
        }
        return label;
      }
    }
  };

  // Initialize on DOM load
  document.addEventListener('DOMContentLoaded', init);

  // Color palette for charts - modern, accessible colors
  function getChartColors(count) {
    const palette = [
      '#3b82f6', // Blue
      '#10b981', // Green
      '#f59e0b', // Amber
      '#ef4444', // Red
      '#8b5cf6', // Purple
      '#ec4899', // Pink
      '#14b8a6', // Teal
      '#f97316', // Orange
      '#6366f1', // Indigo
      '#84cc16', // Lime
      '#06b6d4', // Cyan
      '#f43f5e', // Rose
    ];

    // If we need more colors than in palette, generate lighter variations
    if (count <= palette.length) {
      return palette.slice(0, count);
    }

    const colors = [...palette];
    while (colors.length < count) {
      // Add lighter versions of existing colors
      const baseColor = palette[colors.length % palette.length];
      colors.push(baseColor + 'aa'); // Add alpha for lighter shade
    }
    return colors;
  }

  function init() {

    // Initialize Gridstack in static mode (locked) by default
    grid = GridStack.init({
      column: 12,
      cellHeight: 50,
      margin: 10,
      staticGrid: true, // Start locked - users must click Edit Mode to unlock
      disableOneColumnMode: true,
      float: true,
      animate: true
    });

    // Listen for changes
    grid.on('change', debouncedSaveLayout);
    grid.on('resizestop', onWidgetResize);
    grid.on('dragstart', onWidgetDragStart);
    grid.on('dragstop', onWidgetDragStop);

    // Create delete zone
    createDeleteZone();

    // Set default dates
    setDefaultDates();

    // Load layout
    loadLayout();

    // Initialize edit mode as disabled
    setEditMode(false);

    // Setup auto-refresh (30 seconds)
    setInterval(refreshAllWidgets, 30000);
  }

  function setDefaultDates() {
    const today = new Date();

    // Calculate current week (Monday to Sunday)
    const dayOfWeek = today.getDay(); // 0 = Sunday, 1 = Monday, ..., 6 = Saturday
    const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1; // If Sunday, go back 6 days; otherwise go back to Monday

    const monday = new Date(today);
    monday.setDate(today.getDate() - daysToMonday);

    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);

    const startInput = document.getElementById('start_date');
    const endInput = document.getElementById('end_date');

    if (startInput) {
      startInput.value = formatDateForInput(monday);
    }
    if (endInput) {
      endInput.value = formatDateForInput(sunday);
    }

    // Set default frequency tab active (Daily)
    const tabs = document.querySelectorAll('.toolbar-freq-tabs .btn');
    tabs.forEach(tab => {
      if (tab.dataset.freq === 'last7days') {
        tab.setAttribute('aria-current', 'page');
      } else {
        tab.removeAttribute('aria-current');
      }
    });
  }

  function formatDateForInput(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  window.updateDateRange = function(range) {
    console.log('updateDateRange called with:', range);
    currentDateRange = range;

    const today = new Date();
    let startDate, endDate;

    switch(range) {
      case 'last7days': // Daily: Current week (Monday to Sunday)
        const dayOfWeek = today.getDay();
        const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
        startDate = new Date(today);
        startDate.setDate(today.getDate() - daysToMonday);
        endDate = new Date(startDate);
        endDate.setDate(startDate.getDate() + 6); // Sunday
        break;

      case 'last30days': // Weekly: Last 4 weeks (Monday to Sunday structure)
        const currentDayOfWeek = today.getDay();
        const daysToCurrentMonday = currentDayOfWeek === 0 ? 6 : currentDayOfWeek - 1;
        // Go back to this week's Monday
        const thisMonday = new Date(today);
        thisMonday.setDate(today.getDate() - daysToCurrentMonday);
        // Then go back 3 more weeks (21 days)
        startDate = new Date(thisMonday);
        startDate.setDate(thisMonday.getDate() - 21); // 4 weeks total
        endDate = new Date(thisMonday);
        endDate.setDate(thisMonday.getDate() + 6); // This week's Sunday
        break;

      case 'last90days': // Monthly: Last 12 months including current month
        startDate = new Date(today);
        startDate.setMonth(today.getMonth() - 11); // 12 months including current
        startDate.setDate(1); // Start from 1st of that month
        endDate = new Date(today); // End today
        break;

      case 'thisYear': // YTD: Start of current year to today
        startDate = new Date(today.getFullYear(), 0, 1); // January 1st
        endDate = new Date(today); // Today
        break;

      default:
        startDate = new Date(today);
        startDate.setDate(today.getDate() - 6);
        endDate = new Date(today);
    }

    // Update date inputs
    const startInput = document.getElementById('start_date');
    const endInput = document.getElementById('end_date');

    if (startInput) startInput.value = formatDateForInput(startDate);
    if (endInput) endInput.value = formatDateForInput(endDate);

    console.log('Date range updated to:', formatDateForInput(startDate), '-', formatDateForInput(endDate));

    // Update active tab
    const tabs = document.querySelectorAll('.toolbar-freq-tabs .btn');
    tabs.forEach(tab => {
      if (tab.dataset.freq === range) {
        tab.setAttribute('aria-current', 'page');
      } else {
        tab.removeAttribute('aria-current');
      }
    });

    // Refresh all widgets with new date range
    console.log('Calling refreshAllWidgets...');
    refreshAllWidgets();
  };

  window.applyDateFilter = function() {
    console.log('applyDateFilter called');
    // Custom date range selected
    currentDateRange = 'custom';

    const startInput = document.getElementById('start_date');
    const endInput = document.getElementById('end_date');

    console.log('Custom dates:', startInput?.value, '-', endInput?.value);

    // Clear active tab
    const tabs = document.querySelectorAll('.toolbar-freq-tabs .btn');
    tabs.forEach(tab => tab.removeAttribute('aria-current'));

    // Refresh all widgets
    console.log('Calling refreshAllWidgets...');
    refreshAllWidgets();
  };

  async function loadLayout() {
    try {
      const response = await fetch('/api/dashboard/layout/');
      const result = await response.json();

      if (result.success && result.layout && result.layout.widgets) {
        // Clear existing widgets
        grid.removeAll();
        widgets = {};

        // Add widgets from layout - filter out invalid entries
        for (const widgetConfig of result.layout.widgets) {
          // Skip if config or id is missing
          if (!widgetConfig || !widgetConfig.id) {
            console.warn('Skipping invalid widget config (missing id):', widgetConfig);
            continue;
          }

          // Skip if widget metadata doesn't exist
          if (!WIDGET_META[widgetConfig.id]) {
            console.warn('Skipping unknown widget (not in WIDGET_META):', widgetConfig.id);
            continue;
          }

          await addWidgetToGrid(widgetConfig);
        }
      } else {
        // No layout found or empty - load some default widgets
        console.log('No saved layout found, loading defaults');
        await loadDefaultWidgets();
      }
    } catch (error) {
      console.error('Error loading layout:', error);
      // Load default widgets on error
      await loadDefaultWidgets();
    }
  }

  async function loadDefaultWidgets() {
    // Load a few default widgets to get started
    const defaultWidgets = [
      { id: 'kpi-total-income', x: 0, y: 0, w: 2, h: 3 },
      { id: 'kpi-total-expenses', x: 2, y: 0, w: 2, h: 3 },
      { id: 'kpi-net-cash-flow', x: 4, y: 0, w: 2, h: 3 },
      { id: 'chart-revenue-expense', x: 0, y: 3, w: 6, h: 8 }
    ];

    for (const config of defaultWidgets) {
      await addWidgetToGrid(config);
    }
  }

  async function addWidgetToGrid(config) {
    const widgetId = config.id;
    const meta = WIDGET_META[widgetId];

    if (!meta) {
      console.error('Unknown widget:', widgetId);
      return;
    }

    // Create widget HTML
    const widgetEl = document.createElement('div');
    widgetEl.className = 'grid-stack-item';
    widgetEl.setAttribute('gs-id', widgetId);
    widgetEl.setAttribute('gs-w', config.w || meta.w);
    widgetEl.setAttribute('gs-h', config.h || meta.h);
    widgetEl.setAttribute('gs-x', config.x || 0);
    widgetEl.setAttribute('gs-y', config.y || 0);
    // Removed gs-no-resize to allow free resizing
    if (meta.minW) widgetEl.setAttribute('gs-min-w', meta.minW);
    if (meta.minH) widgetEl.setAttribute('gs-min-h', meta.minH);

    const content = `
      <div class="grid-stack-item-content">
        <div class="widget" id="widget-${widgetId}">
          <div class="widget-header">
            <h3 class="widget-title">${meta.title}</h3>
          </div>
          <div class="widget-body" id="widget-body-${widgetId}">
            <div class="widget-loading">Loading...</div>
          </div>
        </div>
      </div>
    `;

    widgetEl.innerHTML = content;

    // Add to grid
    grid.addWidget(widgetEl);

    // Store reference
    widgets[widgetId] = widgetEl;

    // Load widget data
    await loadWidgetData(widgetId);
  }

  async function loadWidgetData(widgetId) {
    const bodyEl = document.getElementById(`widget-body-${widgetId}`);
    if (!bodyEl) return;

    try {
      // Get date range - use currentDateRange or custom from inputs
      let dateRange = currentDateRange;

      // If custom dates are set, use those
      const startInput = document.getElementById('start_date');
      const endInput = document.getElementById('end_date');

      if (startInput && endInput && startInput.value && endInput.value) {
        // Custom date range - pass as query params
        const url = `/api/dashboard/widget/${widgetId}/?start=${startInput.value}&end=${endInput.value}`;
        console.log('Loading widget with custom dates:', widgetId, url);
        const response = await fetch(url);
        const result = await response.json();

        if (result.success) {
          renderWidget(widgetId, result.data);
        } else {
          console.error('Widget load failed:', widgetId, result.error);
          bodyEl.innerHTML = `<div class="widget-error">${result.error || 'Failed to load widget'}</div>`;
        }
      } else {
        // Use preset date range
        const url = `/api/dashboard/widget/${widgetId}/?dateRange=${dateRange}`;
        console.log('Loading widget with preset range:', widgetId, dateRange, url);
        const response = await fetch(url);
        const result = await response.json();

        if (result.success) {
          renderWidget(widgetId, result.data);
        } else {
          console.error('Widget load failed:', widgetId, result.error);
          bodyEl.innerHTML = `<div class="widget-error">${result.error || 'Failed to load widget'}</div>`;
        }
      }
    } catch (error) {
      console.error(`Error loading widget ${widgetId}:`, error);
      bodyEl.innerHTML = `<div class="widget-error">Error loading widget</div>`;
    }
  }

  function renderWidget(widgetId, data) {
    const meta = WIDGET_META[widgetId];
    const bodyEl = document.getElementById(`widget-body-${widgetId}`);

    if (!bodyEl || !meta) return;

    // Route to appropriate render function
    switch (meta.type) {
      case 'kpi':
        renderKpiWidget(widgetId, bodyEl, data);
        break;
      case 'chart':
        renderChartWidget(widgetId, bodyEl, data);
        break;
      case 'list':
        renderListWidget(widgetId, bodyEl, data);
        break;
      case 'summary':
        renderSummaryWidget(widgetId, bodyEl, data);
        break;
    }
  }

  // ==================== KPI WIDGET RENDERING ====================

  function renderKpiWidget(widgetId, bodyEl, data) {
    const { value, prev_value, change, change_pct, currency, count } = data;

    // Handle special KPI types
    if (widgetId === 'kpi-pending-invoices' || widgetId === 'kpi-overdue-invoices') {
      bodyEl.innerHTML = `
        <div class="kpi-widget">
          <div class="kpi-value">${count || 0}</div>
          <div class="kpi-sublabel">${currency}${formatNumber(value || 0)}</div>
        </div>
      `;
      return;
    }

    if (widgetId === 'kpi-transaction-count' || widgetId === 'kpi-active-projects') {
      bodyEl.innerHTML = `
        <div class="kpi-widget">
          <div class="kpi-value">${formatNumber(value || 0)}</div>
        </div>
      `;
      return;
    }

    if (widgetId === 'kpi-budget-progress') {
      bodyEl.innerHTML = `
        <div class="kpi-widget">
          <div class="kpi-value">${formatNumber(value || 0)}%</div>
          <div class="kpi-sublabel">${currency}${formatNumber(data.total_spent || 0)} / ${currency}${formatNumber(data.total_budget || 0)}</div>
        </div>
      `;
      return;
    }

    // Standard KPI with change
    const changeClass = change >= 0 ? 'positive' : 'negative';
    const arrow = change >= 0 ? '↑' : '↓';

    bodyEl.innerHTML = `
      <div class="kpi-widget">
        <div class="kpi-value">${currency || '£'}${formatNumber(value || 0)}</div>
        ${change !== undefined ? `
          <div class="kpi-change ${changeClass}">
            ${arrow} ${formatNumber(Math.abs(change_pct || 0))}% vs prev period
          </div>
        ` : ''}
      </div>
    `;
  }

  // ==================== CHART WIDGET RENDERING ====================

  function renderChartWidget(widgetId, bodyEl, data) {
    try {
      // Destroy existing chart if any
      if (charts[widgetId]) {
        charts[widgetId].destroy();
        delete charts[widgetId];
      }

      // Basic data check - different chart types have different data structures
      if (!data) {
        bodyEl.innerHTML = '<div class="widget-error">No data available</div>';
        return;
      }

      // Create canvas
      const canvasId = `chart-canvas-${widgetId}`;
      bodyEl.innerHTML = `<div class="chart-widget"><canvas id="${canvasId}"></canvas></div>`;
      const canvas = document.getElementById(canvasId);

      if (!canvas) {
        console.error('Canvas not found for widget:', widgetId);
        return;
      }

      const ctx = canvas.getContext('2d');

      // Route to specific chart type
      switch (widgetId) {
        case 'chart-revenue-expense':
          charts[widgetId] = renderBarChart(ctx, data);
          break;
        case 'chart-expense-pie':
        case 'chart-income-pie':
          charts[widgetId] = renderPieChart(ctx, data);
          break;
        case 'chart-trend-line':
          charts[widgetId] = renderLineChart(ctx, data);
          break;
        case 'chart-waterfall':
          charts[widgetId] = renderWaterfallChart(ctx, data);
          break;
        case 'chart-budget-performance':
          charts[widgetId] = renderBarChart(ctx, data);
          break;
        case 'chart-category-heatmap':
          renderHeatmap(bodyEl, data);
          break;
        case 'chart-money-flow-sankey':
          renderSankey(bodyEl, data);
          break;
      }
    } catch (error) {
      console.error('Error rendering chart widget:', widgetId, error);
      bodyEl.innerHTML = `<div class="widget-error">Error rendering chart: ${error.message}</div>`;
    }
  }

  function renderBarChart(ctx, data) {
    try {
      const canvas = ctx.canvas;
      const parentHeight = canvas.parentElement.offsetHeight;

      // Calculate responsive font sizes based on widget height
      const baseFontSize = Math.max(9, Math.min(12, parentHeight / 30));
      const legendFontSize = Math.max(10, Math.min(13, parentHeight / 25));

      return new Chart(ctx, {
        type: 'bar',
        data: data,
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            mode: 'index',
            intersect: false
          },
          plugins: {
            legend: {
              display: true,
              position: 'top',
              labels: {
                boxWidth: 12,
                padding: 8,
                font: {
                  size: legendFontSize
                }
              }
            },
            tooltip: {
              enabled: true,
              mode: 'index',
              intersect: false
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: {
                font: {
                  size: baseFontSize
                }
              }
            },
            x: {
              ticks: {
                font: {
                  size: baseFontSize
                }
              }
            }
          }
        }
      });
    } catch (error) {
      console.error('Error creating bar chart:', error);
      throw error;
    }
  }

  function renderPieChart(ctx, data) {
    const canvas = ctx.canvas;
    const parentHeight = canvas.parentElement.offsetHeight;

    // Calculate responsive font size
    const legendFontSize = Math.max(9, Math.min(12, parentHeight / 30));

    // Apply color palette to the data
    const chartData = { ...data };
    if (chartData.datasets && chartData.datasets.length > 0) {
      const datasetLength = chartData.datasets[0].data?.length || 0;
      const colors = getChartColors(datasetLength);
      chartData.datasets[0].backgroundColor = colors;
      chartData.datasets[0].borderColor = '#ffffff';
      chartData.datasets[0].borderWidth = 2;
    }

    return new Chart(ctx, {
      type: 'pie',
      data: chartData,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              boxWidth: 12,
              padding: 6,
              font: {
                size: legendFontSize
              }
            }
          },
          tooltip: {
            enabled: true,
            mode: 'nearest',
            intersect: true
          }
        }
      }
    });
  }

  function renderLineChart(ctx, data) {
    const canvas = ctx.canvas;
    const parentHeight = canvas.parentElement.offsetHeight;

    // Calculate responsive font sizes
    const baseFontSize = Math.max(9, Math.min(12, parentHeight / 30));
    const legendFontSize = Math.max(10, Math.min(13, parentHeight / 25));

    return new Chart(ctx, {
      type: 'line',
      data: data,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          intersect: false,
          mode: 'index'
        },
        elements: {
          line: {
            tension: 0.4  // Makes the line smooth/curved (0 = straight, 1 = very curved)
          }
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              boxWidth: 12,
              padding: 8,
              font: {
                size: legendFontSize
              }
            }
          },
          tooltip: {
            enabled: true,
            mode: 'index',
            intersect: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              font: {
                size: baseFontSize
              }
            }
          },
          x: {
            ticks: {
              font: {
                size: baseFontSize
              },
              maxRotation: 45,
              minRotation: 0
            }
          }
        }
      }
    });
  }

  function renderWaterfallChart(ctx, data) {
    // Simplified waterfall using bar chart
    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.labels,
        datasets: [{
          data: data.data,
          backgroundColor: data.data.map(v => v >= 0 ? '#10b981' : '#ef4444')
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true
          }
        }
      }
    });
  }

  function renderHeatmap(bodyEl, data) {
    // Simplified heatmap representation
    if (!data.data || data.data.length === 0) {
      bodyEl.innerHTML = '<div class="widget-loading">No data available</div>';
      return;
    }

    const html = `
      <div class="list-widget">
        ${data.data.map(item => `
          <div class="list-item">
            <span class="list-item-label">${item.category}</span>
            <span class="list-item-amount" style="color: ${item.color}">£${formatNumber(item.value)}</span>
          </div>
        `).join('')}
      </div>
    `;

    bodyEl.innerHTML = html;
  }

  function renderSankey(bodyEl, data) {
    // Simplified Sankey as a list (full Sankey requires D3.js or Recharts)
    if (!data.flows || data.flows.length === 0) {
      bodyEl.innerHTML = '<div class="widget-loading">No data available</div>';
      return;
    }

    const html = `
      <div class="list-widget">
        ${data.flows.slice(0, 10).map(flow => `
          <div class="list-item">
            <span class="list-item-label">${flow.source} → ${flow.target}</span>
            <span class="list-item-amount">£${formatNumber(flow.value)}</span>
          </div>
        `).join('')}
      </div>
    `;

    bodyEl.innerHTML = html;
  }

  // ==================== LIST WIDGET RENDERING ====================

  function renderListWidget(widgetId, bodyEl, data) {
    switch (widgetId) {
      case 'list-recent-transactions':
        renderTransactionsList(bodyEl, data);
        break;
      case 'list-upcoming-bills':
        renderUpcomingBills(bodyEl, data);
        break;
      case 'list-budget-alerts':
        renderBudgetAlerts(bodyEl, data);
        break;
      case 'list-recent-invoices':
        renderRecentInvoices(bodyEl, data);
        break;
    }
  }

  function renderTransactionsList(bodyEl, data) {
    if (!data.transactions || data.transactions.length === 0) {
      bodyEl.innerHTML = '<div class="widget-loading">No transactions found</div>';
      return;
    }

    const html = `
      <div class="list-widget">
        ${data.transactions.map(txn => `
          <div class="list-item">
            <div>
              <div class="list-item-label">${txn.description}</div>
              <div class="list-item-date">${txn.date}</div>
            </div>
            <div class="list-item-amount" style="color: ${txn.direction === 'inflow' ? '#10b981' : '#ef4444'}">
              ${txn.direction === 'inflow' ? '+' : '-'}£${formatNumber(txn.amount)}
            </div>
          </div>
        `).join('')}
      </div>
    `;

    bodyEl.innerHTML = html;
  }

  function renderUpcomingBills(bodyEl, data) {
    if (!data.bills || data.bills.length === 0) {
      const message = data.message || 'No upcoming bills';
      bodyEl.innerHTML = `<div class="widget-loading" style="text-align: center; padding: 2rem; color: #6b7280;">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">📅</div>
        <div style="font-weight: 500;">${message}</div>
      </div>`;
      return;
    }

    const html = `
      <div class="list-widget">
        ${data.bills.map(bill => `
          <div class="list-item">
            <div>
              <div class="list-item-label">${bill.name || bill.description}</div>
              <div class="list-item-date">Due: ${bill.due_date}</div>
            </div>
            <div class="list-item-amount" style="color: #ef4444;">£${formatNumber(bill.amount)}</div>
          </div>
        `).join('')}
      </div>
    `;

    bodyEl.innerHTML = html;
  }

  function renderBudgetAlerts(bodyEl, data) {
    if (!data.alerts || data.alerts.length === 0) {
      bodyEl.innerHTML = '<div class="widget-loading">All budgets on track</div>';
      return;
    }

    const html = `
      <div class="list-widget">
        ${data.alerts.map(alert => `
          <div class="budget-alert alert-${alert.status}">
            <div class="budget-alert-name">${alert.budget_name}</div>
            <div style="font-size: 0.875rem; color: #6b7280;">
              £${formatNumber(alert.spent)} / £${formatNumber(alert.amount)} (${formatNumber(alert.pct)}%)
            </div>
            <div class="budget-alert-bar">
              <div class="budget-alert-bar-fill ${alert.status}" style="width: ${Math.min(alert.pct, 100)}%"></div>
            </div>
          </div>
        `).join('')}
      </div>
    `;

    bodyEl.innerHTML = html;
  }

  function renderRecentInvoices(bodyEl, data) {
    if (!data.invoices || data.invoices.length === 0) {
      bodyEl.innerHTML = '<div class="widget-loading">No recent invoices</div>';
      return;
    }

    const html = `
      <div class="list-widget">
        ${data.invoices.map(inv => `
          <div class="list-item">
            <div>
              <div class="list-item-label">${inv.invoice_number} - ${inv.client}</div>
              <div class="list-item-date">${inv.date}</div>
            </div>
            <div class="list-item-amount">£${formatNumber(inv.total)}</div>
          </div>
        `).join('')}
      </div>
    `;

    bodyEl.innerHTML = html;
  }

  // ==================== SUMMARY WIDGET RENDERING ====================

  function renderSummaryWidget(widgetId, bodyEl, data) {
    if (widgetId === 'summary-financial') {
      renderFinancialSummary(bodyEl, data);
    } else if (widgetId === 'summary-month-comparison') {
      renderMonthComparison(bodyEl, data);
    }
  }

  function renderFinancialSummary(bodyEl, data) {
    const html = `
      <div class="summary-widget">
        <div class="summary-stat">
          <span class="summary-stat-label">Income</span>
          <span class="summary-stat-value" style="color: #10b981">${data.currency}${formatNumber(data.income)}</span>
        </div>
        <div class="summary-stat">
          <span class="summary-stat-label">Expenses</span>
          <span class="summary-stat-value" style="color: #ef4444">${data.currency}${formatNumber(data.expenses)}</span>
        </div>
        <div class="summary-stat">
          <span class="summary-stat-label">Net</span>
          <span class="summary-stat-value" style="color: ${data.net >= 0 ? '#10b981' : '#ef4444'}">${data.currency}${formatNumber(data.net)}</span>
        </div>
        <div class="summary-stat">
          <span class="summary-stat-label">Transactions</span>
          <span class="summary-stat-value">${data.transaction_count}</span>
        </div>
      </div>
    `;

    bodyEl.innerHTML = html;
  }

  function renderMonthComparison(bodyEl, data) {
    const html = `
      <div class="summary-widget">
        <h4 style="margin: 0 0 0.75rem 0; font-size: 0.875rem; color: #6b7280;">This Month vs Last Month</h4>
        <div class="summary-stat">
          <span class="summary-stat-label">Income</span>
          <span class="summary-stat-value">
            ${data.currency}${formatNumber(data.this_month.income)}
            <span style="font-size: 0.75rem; color: ${data.changes.income_pct >= 0 ? '#10b981' : '#ef4444'}">
              ${data.changes.income_pct >= 0 ? '↑' : '↓'}${formatNumber(Math.abs(data.changes.income_pct))}%
            </span>
          </span>
        </div>
        <div class="summary-stat">
          <span class="summary-stat-label">Expenses</span>
          <span class="summary-stat-value">
            ${data.currency}${formatNumber(data.this_month.expenses)}
            <span style="font-size: 0.75rem; color: ${data.changes.expense_pct >= 0 ? '#ef4444' : '#10b981'}">
              ${data.changes.expense_pct >= 0 ? '↑' : '↓'}${formatNumber(Math.abs(data.changes.expense_pct))}%
            </span>
          </span>
        </div>
      </div>
    `;

    bodyEl.innerHTML = html;
  }

  // ==================== WIDGET MANAGEMENT ====================

  let currentDraggedWidget = null;

  function createDeleteZone() {
    const deleteZone = document.createElement('div');
    deleteZone.id = 'widget-delete-zone';
    deleteZone.className = 'widget-delete-zone';
    deleteZone.innerHTML = `
      <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
      </svg>
      <span>Drop here to delete</span>
    `;
    document.body.appendChild(deleteZone);

    // Handle drop on delete zone
    deleteZone.addEventListener('mouseenter', function() {
      if (currentDraggedWidget) {
        deleteZone.classList.add('active-drop');
      }
    });

    deleteZone.addEventListener('mouseleave', function() {
      deleteZone.classList.remove('active-drop');
    });
  }

  function onWidgetDragStart(event, element) {
    const widgetId = element.getAttribute('gs-id');
    currentDraggedWidget = widgetId;
    const deleteZone = document.getElementById('widget-delete-zone');
    if (deleteZone) {
      deleteZone.classList.add('visible');
    }
  }

  function onWidgetDragStop(event, element) {
    const deleteZone = document.getElementById('widget-delete-zone');
    if (deleteZone) {
      deleteZone.classList.remove('visible', 'active-drop');

      // Check if widget was dropped on delete zone
      const rect = deleteZone.getBoundingClientRect();
      const mouseX = event.clientX || (event.touches && event.touches[0] ? event.touches[0].clientX : 0);
      const mouseY = event.clientY || (event.touches && event.touches[0] ? event.touches[0].clientY : 0);

      if (mouseX >= rect.left && mouseX <= rect.right && mouseY >= rect.top && mouseY <= rect.bottom) {
        // Delete the widget
        if (currentDraggedWidget) {
          removeWidget(currentDraggedWidget);
        }
      }
    }
    currentDraggedWidget = null;
  }

  function onWidgetResize(event, element) {
    // Refresh the widget data when resized to ensure charts scale properly
    const widgetId = element.getAttribute('gs-id');
    if (widgetId) {
      setTimeout(() => {
        loadWidgetData(widgetId);
      }, 100);
    }
  }

  window.addWidget = function(widgetId) {
    // Check if widget already exists
    if (widgets[widgetId]) {
      alert('Widget already added to dashboard');
      return;
    }

    const meta = WIDGET_META[widgetId];

    // Find an empty position on the grid
    const nodes = grid.engine.nodes;
    let foundPosition = false;
    let x = 0, y = 0;

    // Try to find an empty spot by checking grid positions
    for (let testY = 0; testY < 20; testY++) {
      for (let testX = 0; testX <= 12 - meta.w; testX++) {
        let canFit = true;

        // Check if this position overlaps with any existing widget
        for (const node of nodes) {
          const nodeRight = node.x + node.w;
          const nodeBottom = node.y + node.h;
          const testRight = testX + meta.w;
          const testBottom = testY + meta.h;

          // Check for overlap
          if (!(testRight <= node.x || testX >= nodeRight || testBottom <= node.y || testY >= nodeBottom)) {
            canFit = false;
            break;
          }
        }

        if (canFit) {
          x = testX;
          y = testY;
          foundPosition = true;
          break;
        }
      }
      if (foundPosition) break;
    }

    const config = {
      id: widgetId,
      x: x,
      y: y,
      w: meta.w,
      h: meta.h
    };

    addWidgetToGrid(config);
    closeAddWidgetModal();
    saveLayout();
  };

  window.removeWidget = function(widgetId) {
    const widgetEl = widgets[widgetId];
    if (!widgetEl) return;

    // Destroy chart if exists
    if (charts[widgetId]) {
      charts[widgetId].destroy();
      delete charts[widgetId];
    }

    // Remove from grid
    grid.removeWidget(widgetEl);
    delete widgets[widgetId];

    saveLayout();
  };

  window.resetLayout = function() {
    if (!confirm('Reset dashboard to default layout? This cannot be undone.')) {
      return;
    }

    fetch('/api/dashboard/layout/reset/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json'
      }
    })
    .then(response => response.json())
    .then(result => {
      if (result.success) {
        location.reload();
      } else {
        alert('Failed to reset layout');
      }
    })
    .catch(error => {
      console.error('Error resetting layout:', error);
      alert('Error resetting layout');
    });
  };

  // ==================== LAYOUT SAVE/LOAD ====================

  function saveLayout() {
    const layout = {
      widgets: []
    };

    // Get current grid state
    grid.engine.nodes.forEach(node => {
      layout.widgets.push({
        id: node.el.getAttribute('gs-id'),
        x: node.x,
        y: node.y,
        w: node.w,
        h: node.h
      });
    });

    // Show saving indicator
    const indicator = document.getElementById('saveIndicator');
    if (indicator) {
      indicator.textContent = 'Saving...';
      indicator.classList.add('saving');
    }

    // Save to server
    fetch('/api/dashboard/layout/save/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ layout })
    })
    .then(response => response.json())
    .then(result => {
      if (indicator) {
        indicator.innerHTML = '<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg> Saved';
        indicator.classList.remove('saving');
      }
    })
    .catch(error => {
      console.error('Error saving layout:', error);
      if (indicator) {
        indicator.textContent = 'Error saving';
        indicator.classList.remove('saving');
      }
    });
  }

  function debouncedSaveLayout() {
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(saveLayout, 2000);
  }

  // ==================== EDIT MODE FUNCTIONS ====================

  window.toggleEditMode = function() {
    console.log('toggleEditMode called, current state:', isEditMode);
    isEditMode = !isEditMode;
    console.log('toggleEditMode new state:', isEditMode);
    setEditMode(isEditMode);
  };

  function setEditMode(enabled) {
    isEditMode = enabled;
    const editBtn = document.getElementById('editModeBtn');
    const editText = document.getElementById('editModeText');
    const addWidgetBtn = document.getElementById('addWidgetBtn');
    const resetBtn = document.getElementById('resetBtn');

    if (!grid) {
      console.error('Grid not initialized');
      return;
    }

    if (enabled) {
      // Enable edit mode - use correct GridStack v10 API
      grid.setStatic(false); // Make grid interactive

      // Update button styling
      editBtn.classList.add('active');
      editText.textContent = 'Exit Edit Mode';

      // Enable action buttons
      addWidgetBtn.disabled = false;
      resetBtn.disabled = false;

      // Show widget control buttons (edit/delete)
      document.querySelectorAll('.widget-controls').forEach(el => {
        el.style.display = 'flex';
      });

      console.log('Edit mode ENABLED - widgets can be dragged, resized, added, and removed');
    } else {
      // Disable edit mode - lock the grid
      grid.setStatic(true); // Make grid static (locked)

      // Update button styling
      editBtn.classList.remove('active');
      editText.textContent = 'Edit Mode';

      // Disable action buttons
      addWidgetBtn.disabled = true;
      resetBtn.disabled = true;

      // Hide widget control buttons (edit/delete)
      document.querySelectorAll('.widget-controls').forEach(el => {
        el.style.display = 'none';
      });

      console.log('Edit mode DISABLED - dashboard is locked');
    }
  }

  // ==================== MODAL FUNCTIONS ====================

  window.openAddWidgetModal = function() {
    const modal = document.getElementById('addWidgetModal');
    modal.classList.add('active');

    // Update widget items to show which are already added
    const items = document.querySelectorAll('.widget-item');
    items.forEach(item => {
      const widgetId = item.getAttribute('data-widget-id');
      if (widgets[widgetId]) {
        item.classList.add('widget-added');
        item.setAttribute('title', 'Already added to dashboard');
      } else {
        item.classList.remove('widget-added');
        item.removeAttribute('title');
      }
    });
  };

  window.closeAddWidgetModal = function() {
    document.getElementById('addWidgetModal').classList.remove('active');
  };

  window.filterWidgets = function() {
    const search = document.getElementById('widgetSearch').value.toLowerCase();
    const items = document.querySelectorAll('.widget-item');

    items.forEach(item => {
      const name = item.querySelector('.widget-name').textContent.toLowerCase();
      item.style.display = name.includes(search) ? 'block' : 'none';
    });
  };

  // ==================== REFRESH FUNCTIONS ====================

  function refreshAllWidgets() {
    Object.keys(widgets).forEach(widgetId => {
      loadWidgetData(widgetId);
    });
  }


  // ==================== UTILITY FUNCTIONS ====================

  function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return Math.abs(num).toLocaleString('en-GB', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2
    });
  }

  // Expose functions globally
  window.dashboardWidgets = {
    refresh: refreshAllWidgets,
    saveLayout: saveLayout
  };

})();
