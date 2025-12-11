# Invoicing & Billing - File Cleanup Summary

## Duplicate Files Found

### CSS Files
1. ✅ **KEEP**: `/app_web/static/app_web/invoices.css` (correct location)
2. ❌ **DELETE**: `/app_web/static/app_web/css/invoices.css` (duplicate in subdirectory)

3. ✅ **KEEP**: `/app_web/static/app_web/clients.css` (correct location)
4. ❌ **DELETE**: `/app_web/static/app_web/css/clients.css` (duplicate in subdirectory)

### JavaScript Files
5. ✅ **KEEP**: `/app_web/static/app_web/invoices.js` (correct location)
6. ❌ **DELETE**: `/app_web/static/app_web/js/invoices.js` (duplicate in subdirectory)

7. ✅ **KEEP**: `/app_web/static/app_web/clients.js` (correct location)
8. ❌ **DELETE**: `/app_web/static/app_web/js/clients.js` (duplicate in subdirectory)

## Why These Locations?

Looking at the existing project structure in `app_web/static/app_web/`:
- ✅ budgets.css (not in css/ subdirectory)
- ✅ budgets.js (not in js/ subdirectory)
- ✅ dashboard.css (not in css/ subdirectory)
- ✅ dashboard.js (not in js/ subdirectory)
- ✅ transactions.css (not in css/ subdirectory)
- ✅ transactions.js (not in js/ subdirectory)

**Pattern**: All CSS and JS files are stored directly in `app_web/static/app_web/`, NOT in subdirectories.

## Template References (Already Corrected)

### invoices.html
- CSS: `{% static 'app_web/invoices.css' %}` ✅
- JS: `{% static 'app_web/invoices.js' %}` ✅

### clients.html
- CSS: `{% static 'app_web/clients.css' %}` ✅
- JS: `{% static 'app_web/clients.js' %}` ✅

## Files to Delete

Please manually delete these 4 duplicate files:
1. `app_web/static/app_web/css/invoices.css`
2. `app_web/static/app_web/css/clients.css`
3. `app_web/static/app_web/js/invoices.js`
4. `app_web/static/app_web/js/clients.js`

You can also delete the empty `css/` and `js/` directories after removing the files if they were only created for this feature.

