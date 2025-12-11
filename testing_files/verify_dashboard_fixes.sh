#!/bin/bash
# Dashboard Widgets - Complete Verification Script

echo "🔍 DASHBOARD WIDGETS - FILE VERIFICATION"
echo "========================================"
echo ""

cd /Users/mohammadsoleja/Documents/GitHub/finance-insights-mvp

echo "1️⃣ Checking Source Files..."
echo ""

# Check JS file
echo "📄 dashboard_widgets.js:"
if grep -q "margin: '20px'" app_web/static/app_web/dashboard_widgets.js; then
    echo "   ✅ Margin is '20px' (CORRECT)"
else
    echo "   ❌ Margin is NOT '20px'"
    echo "   Current value:"
    grep "margin:" app_web/static/app_web/dashboard_widgets.js | head -3
fi

if grep -q "currentDateRange = 'last7days'" app_web/static/app_web/dashboard_widgets.js; then
    echo "   ✅ Default is 'last7days' (CORRECT)"
else
    echo "   ❌ Default is NOT 'last7days'"
    echo "   Current value:"
    grep "currentDateRange" app_web/static/app_web/dashboard_widgets.js | head -3
fi

if grep -q "expense_pct >= 0 ? '#ef4444'" app_web/static/app_web/dashboard_widgets.js; then
    echo "   ✅ Expense color is RED when up (CORRECT)"
else
    echo "   ❌ Expense color logic may be wrong"
    grep "expense_pct" app_web/static/app_web/dashboard_widgets.js | grep "color:" | head -3
fi

echo ""

# Check CSS file
echo "📄 dashboard_widgets.css:"
if grep -q ".grid-stack-item {" app_web/static/app_web/dashboard_widgets.css; then
    echo "   ❌ Conflicting .grid-stack-item margin STILL EXISTS"
    grep -A 2 ".grid-stack-item {" app_web/static/app_web/dashboard_widgets.css
else
    echo "   ✅ No conflicting .grid-stack-item margin (CORRECT)"
fi

echo ""

# Check Python file
echo "📄 dashboard_views.py:"
COLOR_COUNT=$(grep -c "color_palette = \[" app_web/dashboard_views.py)
if [ "$COLOR_COUNT" -ge 2 ]; then
    echo "   ✅ Color palettes exist ($COLOR_COUNT found - CORRECT)"
else
    echo "   ❌ Color palettes may be missing"
fi

echo ""
echo "2️⃣ Checking Template File..."
echo ""

# Check HTML template
echo "📄 dashboard_widgets.html:"
if grep -q "?v=20251124h" app_web/templates/app_web/dashboard_widgets.html; then
    echo "   ✅ Version is 20251124h (CORRECT)"
else
    echo "   ⚠️  Version may not be 20251124h"
    grep "dashboard_widgets" app_web/templates/app_web/dashboard_widgets.html | grep "?v="
fi

if grep -q 'data-freq="last7days".*aria-current="page"' app_web/templates/app_web/dashboard_widgets.html; then
    echo "   ✅ Daily is default tab (CORRECT)"
else
    echo "   ❌ Daily may not be default"
    grep "last7days" app_web/templates/app_web/dashboard_widgets.html | head -2
fi

echo ""
echo "3️⃣ Checking StaticFiles..."
echo ""

if [ -f "staticfiles/app_web/dashboard_widgets.js" ]; then
    echo "📄 staticfiles/dashboard_widgets.js:"
    if grep -q "margin: '20px'" staticfiles/app_web/dashboard_widgets.js; then
        echo "   ✅ Margin is '20px' in staticfiles"
    else
        echo "   ❌ Margin is NOT '20px' in staticfiles"
        echo "   YOU NEED TO RUN: python manage.py collectstatic"
    fi
else
    echo "   ❌ staticfiles/app_web/dashboard_widgets.js does NOT exist"
    echo "   YOU NEED TO RUN: python manage.py collectstatic"
fi

echo ""
echo "4️⃣ Django Configuration..."
echo ""

echo "📄 settings.py:"
if grep -q "DEBUG = True" financeinsights/settings.py; then
    echo "   ✅ DEBUG = True (Development mode)"
    echo "   ℹ️  Django will serve from app_web/static/app_web/ directly"
else
    echo "   ⚠️  DEBUG = False (Production mode)"
    echo "   ℹ️  Django will serve from staticfiles/"
fi

echo ""
echo "========================================"
echo "📋 SUMMARY:"
echo ""

# Count issues
ISSUES=0

if ! grep -q "margin: '20px'" app_web/static/app_web/dashboard_widgets.js; then
    echo "❌ JS margin needs fixing"
    ((ISSUES++))
fi

if ! grep -q "currentDateRange = 'last7days'" app_web/static/app_web/dashboard_widgets.js; then
    echo "❌ Default date range needs fixing"
    ((ISSUES++))
fi

if ! grep -q "expense_pct >= 0 ? '#ef4444'" app_web/static/app_web/dashboard_widgets.js; then
    echo "❌ Expense color logic needs fixing"
    ((ISSUES++))
fi

if grep -q ".grid-stack-item {" app_web/static/app_web/dashboard_widgets.css; then
    echo "❌ CSS has conflicting margin"
    ((ISSUES++))
fi

if [ "$ISSUES" -eq 0 ]; then
    echo "✅ ALL SOURCE FILES ARE CORRECT!"
    echo ""
    echo "🎯 NEXT STEPS:"
    echo "1. Hard refresh browser: Cmd + Shift + R (Mac) or Ctrl + Shift + R (Windows)"
    echo "2. Or use Incognito/Private mode"
    echo "3. Clear browser cache if still not working"
else
    echo "⚠️  Found $ISSUES issue(s) in source files"
    echo ""
    echo "Files need to be updated!"
fi

echo ""
echo "========================================"

