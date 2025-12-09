#!/bin/bash
# Comprehensive OpenAI Fix and Server Restart Script

echo "======================================================================"
echo "COMPREHENSIVE OPENAI FIX - AUTOMATED"
echo "======================================================================"

cd /Users/mohammadsoleja/Documents/GitHub/finance-insights-mvp

echo ""
echo "[1/6] Checking Python version..."
python --version
which python

echo ""
echo "[2/6] Checking current OpenAI version..."
python -c "import openai; print('Current version:', openai.__version__)" 2>&1

echo ""
echo "[3/6] Uninstalling old OpenAI..."
pip uninstall openai -y 2>&1 | grep -E "(Successfully|Found)"

echo ""
echo "[4/6] Installing OpenAI 1.3.0..."
pip install openai==1.3.0 2>&1 | grep -E "(Successfully|Requirement)"

echo ""
echo "[5/6] Verifying installation..."
python -c "
import openai
print('✓ OpenAI version:', openai.__version__)

# Test client creation
try:
    from openai import OpenAI
    client = OpenAI(api_key='test-key')
    print('✓ Client creation works - no proxies error!')
except Exception as e:
    print('✗ Error:', e)
"

echo ""
echo "[6/6] Checking for running Django servers..."
pgrep -f "python.*manage.py runserver" && echo "⚠️  Django server IS RUNNING - YOU MUST RESTART IT!" || echo "✓ No Django server running"

echo ""
echo "======================================================================"
echo "FIX COMPLETE!"
echo "======================================================================"
echo ""
echo "NEXT STEPS:"
echo "1. If Django server is running: Press Ctrl+C to stop it"
echo "2. Start server: python manage.py runserver"
echo "3. Test: Create a goal and check for 'proxies' error"
echo ""
echo "Expected: NO 'proxies' error, AI working with 85-95% confidence"
echo "======================================================================"

