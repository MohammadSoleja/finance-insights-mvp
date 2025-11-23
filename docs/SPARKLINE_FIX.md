# Sparkline Fix - Real Data Implementation

## Problem
The sparklines in Dashboard KPI cards were changing on every page refresh because they were using randomly generated data instead of actual historical data from the database.

## Root Cause
```javascript
// Old code in dashboard.html
const generateTrendData = (base, variance, points = 7) => {
  const data = [];
  for (let i = 0; i < points; i++) {
    const variation = (Math.random() - 0.5) * variance;  // ← Random!
    data.push(Math.max(0, base + variation));
  }
  return data;
};
```

Every page refresh would call `Math.random()`, generating different numbers each time.

## Solution
Replaced random data generation with actual 7-day historical data from the backend.

### Changes Made:

#### 1. Backend (views.py)
Added sparkline data calculation to `dashboard_view()` function:

```python
# Generate sparkline data (last 7 days) for KPI cards
sparkline_days = 7
sparkline_end = today
sparkline_start = sparkline_end - datetime.timedelta(days=sparkline_days - 1)

# Query transactions for last 7 days
sparkline_q = Q(organization=org, date__gte=sparkline_start, date__lte=sparkline_end)
if category:
    sparkline_q &= Q(category=category)

sparkline_qs = Transaction.objects.filter(sparkline_q).order_by('date')
sparkline_df = queryset_to_df(sparkline_qs)

# Group by day and calculate daily values
if not sparkline_df.empty:
    sparkline_df['date'] = pd.to_datetime(sparkline_df['date'])
    daily_data = sparkline_df.groupby(sparkline_df['date'].dt.date).agg({
        'inflow': 'sum',
        'outflow': 'sum',
        'signed_amount': 'sum'
    }).reset_index()
    
    # Fill missing days with zeros
    all_dates = pd.date_range(start=sparkline_start, end=sparkline_end, freq='D')
    for date in all_dates_list:
        day_data = daily_data[daily_data['date'] == date]
        if not day_data.empty:
            sparkline_outflow.append(round(float(day_data['outflow'].iloc[0]), 2))
            sparkline_inflow.append(round(float(day_data['inflow'].iloc[0]), 2))
            sparkline_net.append(round(float(day_data['signed_amount'].iloc[0]), 2))
        else:
            # Fill missing days with 0
            sparkline_outflow.append(0.0)
            sparkline_inflow.append(0.0)
            sparkline_net.append(0.0)

# Pass to context as JSON
context['sparkline_outflow'] = json.dumps(sparkline_outflow)
context['sparkline_inflow'] = json.dumps(sparkline_inflow)
context['sparkline_net'] = json.dumps(sparkline_net)
```

#### 2. Frontend (dashboard.html)
Updated JavaScript to use backend data instead of generating random data:

```javascript
// Use actual 7-day historical data from backend
const outflowData = {{ sparkline_outflow|default:"[]"|safe }};
if (outflowData.length > 0) {
  outflowContainer.innerHTML = createSparkline(outflowData, 80, 28, '#ef4444');
}

const inflowData = {{ sparkline_inflow|default:"[]"|safe }};
if (inflowData.length > 0) {
  inflowContainer.innerHTML = createSparkline(inflowData, 80, 28, '#10b981');
}

const netData = {{ sparkline_net|default:"[]"|safe }};
if (netData.length > 0) {
  netContainer.innerHTML = createSparkline(netData, 80, 28, '#2563eb');
}
```

## Benefits
1. **Consistent Data**: Sparklines now show the same data on every refresh
2. **Real Historical Trends**: Shows actual 7-day trends from your database
3. **Respects Filters**: If category filter is applied, sparklines reflect filtered data
4. **Organization-Aware**: Respects multi-tenant organization filtering
5. **Handles Missing Days**: Fills gaps with zeros for days with no transactions

## Files Modified
- `/app_web/views.py` - Added sparkline data calculation (lines ~680-740)
- `/app_web/templates/app_web/dashboard.html` - Updated JavaScript to use real data (lines ~293-320)

## Result
✅ Sparklines now remain consistent across page refreshes
✅ Shows actual 7-day historical trend data
✅ Color-coded: Red (outflow), Green (inflow), Blue (net)
✅ Positioned below comparison delta for better visual hierarchy
✅ 80px × 28px size for optimal visibility

## Troubleshooting

If sparklines are not appearing, check the following:

### 1. Browser Console
Open Developer Tools (F12) and check the Console tab for:
- `Sparkline containers:` - Should show 3 elements
- `createSparkline function exists:` - Should be `"function"`
- `Outflow/Inflow/Net sparkline data:` - Should show arrays of numbers
- Any errors

### 2. Data Availability
Sparklines only appear when:
- `kpi.tx_count > 0` (there are transactions in the selected period)
- The sparkline containers exist in the DOM
- There is transaction data in the last 7 days

### 3. Check Backend Data
The view should be passing these context variables:
```python
context['sparkline_outflow']  # JSON array like [12.5, 0, 45.2, ...]
context['sparkline_inflow']   # JSON array like [0, 120.0, 0, ...]
context['sparkline_net']      # JSON array like [-12.5, 120.0, -45.2, ...]
```

### 4. Verify Function Load Order
The `ui-utilities.js` file must load before the dashboard-specific JavaScript.
Check in `base.html` that it's included:
```html
<script src="{% static 'app_web/ui-utilities.js' %}"></script>
```

### 5. Check Data Format
The data should be an array of numbers:
```javascript
// ✅ Correct
[12.5, 0, 45.2, 120.0, 0, 67.8, 89.1]

// ❌ Incorrect
"[12.5, 0, 45.2, 120.0, 0, 67.8, 89.1]"  // String instead of array
```

### 6. Manual Test
In browser console, test the function directly:
```javascript
createSparkline([10, 20, 15, 30, 25, 40, 35], 80, 28, '#2563eb')
// Should return SVG HTML string
```

---

**Date**: November 23, 2025
**Status**: ✅ COMPLETE
**Debug Mode**: ENABLED (console logs added for troubleshooting)

