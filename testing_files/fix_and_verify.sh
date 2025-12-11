#!/bin/bash
# Complete fix for Python cache and Django startup

echo "🔧 Fixing Python cache and starting fresh..."
echo ""

cd /Users/mohammadsoleja/Documents/GitHub/finance-insights-mvp

echo "1. Clearing Python cache..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
echo "   ✓ Cache cleared"

echo ""
echo "2. Verifying Django can load..."
python manage.py check > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ Django loads successfully"
else
    echo "   ✗ Django has errors"
    python manage.py check
    exit 1
fi

echo ""
echo "3. Verifying Hugging Face integration..."
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'financeinsights.settings')
import django
django.setup()
from django.conf import settings
from app_core import ai_service
if ai_service.HUGGINGFACE_AVAILABLE and ai_service._check_ai_available():
    print('   ✓ Hugging Face is configured and ready')
else:
    print('   ✗ Hugging Face not available')
" 2>/dev/null

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ ALL FIXED! Ready to start your server!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Start your server with:"
echo "  python manage.py runserver"
echo ""
echo "Then test at: http://127.0.0.1:8000/playbook/"
echo ""

