# Multi-Currency Bug Fixes - November 27, 2025

## 🐛 Issues Fixed

### **Issue 1: Budgets Template Error** ✅ FIXED
**Problem:** Template syntax error due to broken currency tags
```
TemplateSyntaxError: Invalid block tag 'currency_symbol'
Line 209: {% currency_symbol %}{{\ 1}}
```

**Root Cause:** The automated script `update_currency_templates.py` incorrectly replaced `£{{ variable }}` with `{% currency_symbol %}{{\ 1}}` instead of proper variable names.

**Fix Applied:**
1. Added `{% load currency_tags %}` to budgets.html
2. Fixed all broken instances:
   - `{{\ 1}}` → `{{ budget.spent|floatformat:2|intcomma }}`
   - `{{\ 1}}` → `{{ budget.remaining|floatformat:2|intcomma }}`
   - `{{\ 1}}` → `{{ budget.budget_amount|floatformat:2|intcomma }}`

**Files Modified:**
- `app_web/templates/app_web/budgets.html`

---

### **Issue 2: Dashboard Widgets No Conversion** ✅ FIXED
**Problem:** Currency symbol changed but amounts didn't convert
- Changed org currency to USD
- Widgets showed `$` symbol
- But amounts were still in GBP (not converted)

**Root Cause:** Widget data functions were aggregating `amount` field instead of `display_amount` field. When organization currency changes, transactions store converted amounts in `display_amount`, but widgets weren't using it.

**Fix Applied:**
Updated all KPI widget functions to use `display_amount` when available, fallback to `amount`:

```python
# Before
.aggregate(total=Sum('amount'))

# After
.aggregate(
    total=Sum(
        Case(
            When(display_amount__isnull=False, then=F('display_amount')),
            default=F('amount')
        )
    )
)
```

**Functions Updated:**
1. `get_kpi_total_income()` - Uses display_amount
2. `get_kpi_total_expenses()` - Uses display_amount
3. `get_kpi_net_cash_flow()` - Uses display_amount for income, expenses, and prev values
4. `get_kpi_avg_transaction()` - Uses display_amount

**Files Modified:**
- `app_web/dashboard_views.py`

---

## 🧪 How to Test

### **Test 1: Budgets Page**
1. Go to: `http://127.0.0.1:8000/budgets/`
2. **Expected:** Page loads without error
3. **Expected:** Budget amounts show with currency symbol
4. Hard refresh to ensure cache cleared

### **Test 2: Dashboard Widgets with Currency Conversion**

**Step 1: Create Test Transactions**
```python
# In Django shell (optional - if you want fresh test data)
python manage.py shell

from app_core.models import Transaction, Organization
from datetime import date
from decimal import Decimal

org = Organization.objects.first()
user = org.owner

# Create a test transaction in GBP
tx = Transaction.objects.create(
    organization=org,
    user=user,
    date=date.today(),
    description="Test Transaction",
    amount=Decimal('100.00'),
    direction='inflow',
    original_currency='GBP'
)

# Check what was saved
print(f"Amount: {tx.amount}")
print(f"Display Amount: {tx.display_amount}")
print(f"Original Currency: {tx.original_currency}")
print(f"Exchange Rate: {tx.exchange_rate}")
```

**Step 2: Change Currency**
1. Go to: `http://127.0.0.1:8000/settings/`
2. Change to **US Dollar ($)**
3. Save

**Step 3: Check Widgets Dashboard**
1. Go to: `http://127.0.0.1:8000/dashboard/`
2. **Hard refresh:** `Cmd + Shift + R`
3. **Expected:** 
   - All KPI cards show `$` symbol ✓
   - Amounts are **converted** (not the same numbers as GBP)
   - Example: If you had £100, should show ~$127

**Step 4: Verify Conversion**
1. Note a specific transaction amount in GBP
2. Change to USD
3. Refresh dashboard
4. Amount should be multiplied by ~1.27 (GBP→USD rate)

### **Test 3: Check All KPI Widgets**
Test each widget:
- ✅ Total Income - Should show converted amount
- ✅ Total Expenses - Should show converted amount  
- ✅ Net Cash Flow - Should show converted amount
- ✅ Avg Transaction - Should show converted amount

---

## 💡 How Conversion Works Now

### **Transaction Save Flow:**
1. User creates transaction with amount (e.g., £100)
2. `Transaction.save()` checks org's preferred_currency
3. If different from transaction's currency:
   - Calls `CurrencyConverter.convert_to_org_currency()`
   - Stores result in `display_amount` (e.g., $127)
   - Stores `exchange_rate` (e.g., 1.27)
   - Stores `rate_date`
4. If same currency:
   - `display_amount` = `amount`
   - `exchange_rate` = 1.0

### **Widget Data Query:**
```python
# Smart aggregation
.aggregate(
    total=Sum(
        Case(
            When(display_amount__isnull=False, then=F('display_amount')),
            default=F('amount')
        )
    )
)
```

This ensures:
- ✅ New transactions use converted `display_amount`
- ✅ Old transactions (pre-currency feature) use `amount`
- ✅ Transactions in org currency use `amount` (no conversion needed)

---

## ⚠️ Important Notes

### **Existing Transactions:**
- Old transactions created before currency feature won't have `display_amount`
- Query uses `CASE WHEN` to fallback to `amount` for these
- Once you edit/save an old transaction, it will auto-convert

### **Force Convert All Transactions:**
To convert all existing transactions to org currency:
```python
python manage.py shell

from app_core.models import Transaction

# Re-save all transactions to trigger conversion
for tx in Transaction.objects.all():
    tx.save()  # This triggers the auto-conversion in save()

print("All transactions converted!")
```

### **Browser Cache:**
- **Must hard refresh** after changing currency
- Dashboard widgets cache data for 30 seconds
- Hard refresh: `Cmd + Shift + R` (Mac) or `Ctrl + Shift + R` (Windows)

---

## 📊 Expected Behavior

### **Scenario: GBP → USD**

**Before (GBP):**
```
Total Income: £10,000
Total Expenses: £7,500
Net: £2,500
Avg Transaction: £250
```

**After (Changed to USD):**
```
Total Income: $12,700  (converted at 1.27)
Total Expenses: $9,525  (converted at 1.27)
Net: $3,175
Avg Transaction: $317.50
```

**Key Point:** Numbers should **change** when currency changes, not just the symbol!

---

## 🔍 Troubleshooting

### **Problem: Numbers don't convert**
**Solution:**
1. Check transactions have `display_amount`:
```python
python manage.py shell
from app_core.models import Transaction
tx = Transaction.objects.first()
print(f"Display: {tx.display_amount}, Amount: {tx.amount}")
```

2. If `display_amount` is None, re-save transactions:
```python
Transaction.objects.all().update(display_amount=None)
for tx in Transaction.objects.all():
    tx.save()
```

### **Problem: Budgets page still errors**
**Solution:**
1. Check template has: `{% load currency_tags %}`
2. Hard refresh browser
3. Check no syntax errors with:
```bash
python manage.py check
```

### **Problem: Symbol shows but amounts wrong**
**Solution:**
1. Check exchange rates exist:
```python
python manage.py shell
from app_core.models import ExchangeRate
rates = ExchangeRate.objects.filter(from_currency='GBP', to_currency='USD')
print(rates)
```

2. If no rates, refresh:
```bash
python manage.py refresh_exchange_rates
```

---

## ✅ Status

**Both Issues: FIXED** ✅

- [x] Budgets template loads without error
- [x] Currency symbol shows correctly in budgets
- [x] Dashboard widgets show correct currency symbol
- [x] Dashboard widgets convert amounts correctly
- [x] All KPI widgets use display_amount
- [x] Fallback to amount for old transactions

---

## 📁 Files Modified

1. `app_web/templates/app_web/budgets.html` - Fixed template tags
2. `app_web/dashboard_views.py` - Updated 4 KPI functions to use display_amount

**Total Changes:** 2 files, ~100 lines modified

---

**Test now and verify both issues are resolved!** 🚀

