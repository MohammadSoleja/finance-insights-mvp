# Dashboard Widgets Implementation Plan 🎨

**Date:** November 23, 2025  
**Feature:** Customizable Dashboard with Drag & Drop Widgets  
**Status:** 🚧 IN PROGRESS

---

## 🎯 Specifications

### **Technology Stack:**
- **Grid System:** Gridstack.js
- **Charts Library:** Recharts (for advanced charts like Sankey, Heatmap)
- **Save Behavior:** Auto-save with 2-second debounce
- **Layouts:** Single custom layout per user
- **Mobile:** Vertical stacking (no drag & drop)
- **Updates:** Real-time with polling (30-second intervals)

---

## 📦 Widget Inventory (24 Total)

### **KPI Widgets (10):**
1. `kpi-total-income` - Total Income (current period)
2. `kpi-total-expenses` - Total Expenses (current period)
3. `kpi-net-cash-flow` - Net Cash Flow (income - expenses)
4. `kpi-avg-transaction` - Average Transaction Amount
5. `kpi-transaction-count` - Total Transaction Count
6. `kpi-budget-progress` - Overall Budget Progress %
7. `kpi-burn-rate` - Daily Burn Rate
8. `kpi-active-projects` - Active Projects Count
9. `kpi-pending-invoices` - Pending Invoices (count + amount)
10. `kpi-overdue-invoices` - Overdue Invoices (count + amount)

### **Chart Widgets (8):**
1. `chart-revenue-expense` - Revenue vs Expenses Bar Chart
2. `chart-expense-pie` - Expense Breakdown Pie Chart
3. `chart-income-pie` - Income Breakdown Pie Chart
4. `chart-trend-line` - Income/Expense Trend Line
5. `chart-waterfall` - Cash Flow Waterfall Chart
6. `chart-budget-performance` - Budget vs Actual Bars
7. `chart-category-heatmap` - Category Spending Heatmap (NEW!)
8. `chart-money-flow-sankey` - Money Flow Sankey Diagram (NEW!)

### **List Widgets (4):**
1. `list-recent-transactions` - Last 10 Transactions
2. `list-upcoming-bills` - Upcoming Due Dates
3. `list-budget-alerts` - Over/Near Budget Alerts
4. `list-recent-invoices` - Last 5 Invoices

### **Summary Widgets (2):**
1. `summary-financial` - Financial Summary Card
2. `summary-month-comparison` - Month-over-Month Stats

---

## 🗄️ Database Schema

```python
class DashboardLayout(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    layout_config = models.JSONField(default=dict)
    # {
    #   'widgets': [
    #     {
    #       'id': 'kpi-total-income',
    #       'x': 0, 'y': 0, 'w': 3, 'h': 1,
    #       'settings': {
    #         'dateRange': 'last30days',
    #         'showSparkline': True
    #       }
    #     }
    #   ],
    #   'density': 'comfortable',  # compact, comfortable, spacious
    #   'autoRefresh': 30  # seconds
    # }
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'organization']
```

---

## 📋 Implementation Checklist

### Phase 1: Backend Setup
- [ ] Create DashboardLayout model
- [ ] Create migration
- [ ] Create API endpoints (GET, POST layout)
- [ ] Create widget data endpoints (for each widget type)

### Phase 2: Frontend - Grid System
- [ ] Add Gridstack.js CDN
- [ ] Add Recharts CDN
- [ ] Create dashboard.js
- [ ] Initialize Gridstack
- [ ] Setup grid options (12 columns, responsive)

### Phase 3: Widget Components
- [ ] Create widget template structure
- [ ] Implement all 10 KPI widgets
- [ ] Implement all 8 Chart widgets
- [ ] Implement all 4 List widgets
- [ ] Implement all 2 Summary widgets

### Phase 4: Widget Library
- [ ] Create "Add Widget" modal
- [ ] Group widgets by category
- [ ] Search/filter widgets
- [ ] Add widget to grid

### Phase 5: Customization
- [ ] Widget settings modal (per widget)
- [ ] Date range selector
- [ ] Remove widget functionality
- [ ] Reset to default layout

### Phase 6: Save/Load
- [ ] Debounced auto-save (2 seconds)
- [ ] Load layout on page load
- [ ] Default layout for new users
- [ ] Visual save indicator

### Phase 7: Real-time Updates
- [ ] Setup polling (30-second intervals)
- [ ] Update widget data
- [ ] Loading states
- [ ] Error handling

### Phase 8: Polish
- [ ] Mobile responsive (stack vertically)
- [ ] Loading skeletons
- [ ] Empty states
- [ ] Tooltips
- [ ] Animations

---

## 🎨 Default Layout

```javascript
{
  widgets: [
    // Row 1: KPIs
    { id: 'kpi-total-income', x: 0, y: 0, w: 3, h: 1 },
    { id: 'kpi-total-expenses', x: 3, y: 0, w: 3, h: 1 },
    { id: 'kpi-net-cash-flow', x: 6, y: 0, w: 3, h: 1 },
    { id: 'kpi-budget-progress', x: 9, y: 0, w: 3, h: 1 },
    
    // Row 2: Main Charts
    { id: 'chart-revenue-expense', x: 0, y: 1, w: 6, h: 2 },
    { id: 'chart-trend-line', x: 6, y: 1, w: 6, h: 2 },
    
    // Row 3: Secondary Charts
    { id: 'chart-expense-pie', x: 0, y: 3, w: 4, h: 2 },
    { id: 'chart-budget-performance', x: 4, y: 3, w: 4, h: 2 },
    { id: 'list-recent-transactions', x: 8, y: 3, w: 4, h: 2 }
  ]
}
```

---

## 🚀 Next Steps

1. Create database model
2. Setup CDN dependencies
3. Build widget components
4. Implement drag & drop
5. Add auto-save
6. Test & polish

---

**Estimated Time:** 2-3 hours  
**Priority:** High  
**Complexity:** Medium-High

