# Transaction Creation Fix - December 7, 2025

## Issue

**Error when creating transactions:**
```
Failed to save transaction: NOT NULL constraint failed: app_core_transaction.original_currency
```

## Root Cause

The database schema had an `original_currency` column with a NOT NULL constraint, but:
1. The field was not defined in the `Transaction` model in `models.py`
2. Transaction creation code didn't set this field
3. This caused all new transaction creations to fail

## Solution

Added the missing `original_currency` field to the `Transaction` model with a default value of "GBP".

### Code Changes

**File:** `app_core/models.py`

```python
class Transaction(models.Model):
    # ...existing fields...
    subcategory = models.CharField(max_length=128, blank=True, default="")
    account = models.CharField(max_length=128, blank=True, default="")
    source = models.CharField(max_length=64, blank=True, default="csv")
    original_currency = models.CharField(max_length=3, default="GBP", help_text="Original currency code (ISO 4217)")  # NEW
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Migration

- Created migration to add the field with default value
- No data migration needed since default value is set

## Testing

✅ **Verified:** Test transaction created successfully
✅ **Verified:** Field has default value of "GBP"
✅ **Verified:** No migration conflicts

## Result

**Transaction creation now works!** The `original_currency` field will automatically be set to "GBP" for all new transactions unless explicitly specified otherwise.

### Future Enhancement

If multi-currency support is needed in the future, the transaction creation forms should include a currency selector. For now, all transactions default to GBP (£).

---

**Fixed:** December 7, 2025  
**Status:** ✅ Resolved

