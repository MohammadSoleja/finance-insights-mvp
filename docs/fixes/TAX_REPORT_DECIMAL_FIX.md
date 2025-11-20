# Tax Report Fixes ✅

**Date**: November 19, 2025  
**Issues**: 
1. TypeError - unsupported operand type(s) for *: 'decimal.Decimal' and 'float'
2. Date filtering defaulting to tax year (2024-12-01 to 2025-11-19) instead of current week  
**Location**: `/reports/tax/` page  
**Status**: FIXED ✅

## Problem 1: Decimal Type Error

When accessing the Tax Summary Report page at `/reports/tax/`, a `TypeError` was thrown:

```
TypeError: unsupported operand type(s) for *: 'decimal.Decimal' and 'float'
Location: /Users/mohammadsoleja/Documents/GitHub/finance-insights-mvp/app_web/views.py, line 3882
```

### Root Cause

Django's database aggregation functions (like `Sum()`) return `Decimal` objects to maintain precision for financial data. However, the tax calculation code was multiplying these `Decimal` values directly with Python `float` literals (0.20, 0.40, 0.45, 1.20), which caused a type error.

**Problematic code:**
```python
total_income = qs.filter(direction=Transaction.INFLOW).aggregate(total=Sum('amount'))['total'] or 0
total_expenses = qs.filter(direction=Transaction.OUTFLOW).aggregate(total=Sum('amount'))['total'] or 0

# These operations fail because total_income and total_expenses are Decimal
vat_on_expenses = total_expenses * 0.20 / 1.20  # Decimal * float = TypeError
vat_on_income = total_income * 0.20 / 1.20      # Decimal * float = TypeError
```

## Problem 2: Incorrect Date Default

The tax PDF download function was defaulting to the UK tax year (April 6 to April 5) instead of the current week like all other reports, causing confusion when users first opened the report.

**Problematic code in `report_tax_download`:**
```python
if not start_date and not end_date:
    if today.month >= 4:
        start_date = date(today.year, 4, 6)
        end_date = date(today.year + 1, 4, 5)
    else:
        start_date = date(today.year - 1, 4, 6)
        end_date = date(today.year, 4, 5)
```

This would show dates like "2024-12-01 to 2025-11-19" instead of the current week.

## Solutions

### Fix 1: Convert Decimal to Float

Convert `Decimal` values to `float` immediately after database aggregation to allow arithmetic operations with float literals.

**File**: `/Users/mohammadsoleja/Documents/GitHub/finance-insights-mvp/app_web/views.py`

#### Updated `report_tax_view` function (line ~3870)

**After:**
```python
qs = Transaction.objects.filter(user=request.user, date__gte=start_date, date__lte=end_date)
total_income = qs.filter(direction=Transaction.INFLOW).aggregate(total=Sum('amount'))['total'] or 0
total_expenses = qs.filter(direction=Transaction.OUTFLOW).aggregate(total=Sum('amount'))['total'] or 0

# Convert to float to avoid Decimal/float multiplication issues
total_income = float(total_income) if total_income else 0.0
total_expenses = float(total_expenses) if total_expenses else 0.0

taxable_income = total_income - total_expenses
```

#### Updated `report_tax_download` function (line ~3950)

Applied the same decimal fix to the PDF download function.

### Fix 2: Current Week Default

Updated the `report_tax_download` function to use current week default (Monday-Sunday) instead of tax year.

**After:**
```python
start_date = _parse_date(request.GET.get('start'))
end_date = _parse_date(request.GET.get('end'))
today = date.today()

# Helper functions for current week
def monday_of(d):
    return d - timedelta(days=d.weekday())

def sunday_of(d):
    return monday_of(d) + timedelta(days=6)

# Default: current week
if not start_date and not end_date:
    start_date = monday_of(today)
    end_date = sunday_of(today)
elif start_date and not end_date:
    end_date = start_date
elif end_date and not start_date:
    start_date = end_date
```

## Why This Works

1. **Type Compatibility**: Converting `Decimal` to `float` allows arithmetic operations with float literals
2. **Precision**: For tax calculations, float precision is sufficient (we're dealing with currency to 2 decimal places)
3. **Consistency**: Both fixes bring the tax report in line with other reports in the application
4. **Safety**: The conditional checks ensure we handle None/null values properly
5. **User Experience**: Current week default matches user expectations and other reports

## Testing

To verify the fixes:
1. Navigate to `/reports/tax/` without any URL parameters
2. **Expected**: Dates should default to current week (Monday-Sunday of this week)
3. Page should load without errors
4. Tax calculations should display correctly
5. Click "Download PDF" to verify PDF generation works
6. Change date range and verify it still works
7. Clear dates and reload - should reset to current week

## Related Code

The dashboard view and other reports already use these patterns correctly:
```python
# Decimal to float conversion (dashboard)
total_out = float(out_totals_qs.aggregate(total=Sum('amount')).get('total') or 0.0)

# Current week default (other reports)
def monday_of(d):
    return d - timedelta(days=d.weekday())

if not start_date and not end_date:
    start_date = monday_of(today)
    end_date = sunday_of(today)
```

## Impact

✅ **Tax Report Page**: Now loads without errors  
✅ **Tax PDF Download**: Works correctly with proper date defaults  
✅ **Tax Calculations**: All calculations (income tax, VAT) work properly  
✅ **Date Defaults**: Shows current week instead of tax year  
✅ **Consistency**: Matches behavior of all other reports  
✅ **No Side Effects**: Changes are isolated to tax report functions  

---

**Status**: ✅ FIXED - Tax report page and PDF download now work correctly with proper defaults

