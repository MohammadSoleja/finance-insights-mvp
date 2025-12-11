#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'financeinsights.settings')
django.setup()

from app_core import ai_service
from app_core.models import FinancialGoal, GoalEvaluation

print('=' * 70)
print('AI PLAYBOOK STATUS CHECK')
print('=' * 70)

# Check OpenAI configuration
print('\n1. OpenAI Configuration:')
print('-' * 70)
print(f'   AI Playbook Enabled: {ai_service.settings.AI_PLAYBOOK_ENABLED}')
if ai_service.settings.OPENAI_API_KEY:
    print(f'   API Key: {ai_service.settings.OPENAI_API_KEY[:30]}...(length: {len(ai_service.settings.OPENAI_API_KEY)})')
else:
    print('   API Key: NOT SET')
print(f'   Model: {ai_service.settings.OPENAI_MODEL}')
print(f'   AI Available: {ai_service._check_ai_available()}')

# Check if OpenAI library is installed
print('\n2. OpenAI Library:')
print('-' * 70)
try:
    import openai
    print(f'   ✓ OpenAI library installed (version: {openai.__version__})')
except ImportError:
    print('   ✗ OpenAI library NOT installed')

# Check recent evaluations
print('\n3. Recent Goal Evaluations:')
print('-' * 70)
goals = FinancialGoal.objects.filter(active=True)
if not goals.exists():
    print('   No active goals found')
else:
    for goal in goals:
        print(f'\n   Goal: {goal.name}')
        print(f'   Type: {goal.get_goal_type_display()}')
        print(f'   Status: {goal.current_status}')

        latest_eval = GoalEvaluation.objects.filter(goal=goal).order_by('-evaluated_at').first()
        if latest_eval:
            print(f'   Latest Evaluation: {latest_eval.evaluated_at}')

            if latest_eval.explanation:
                print(f'   ✓ Has AI Explanation ({len(latest_eval.explanation)} chars)')
                # Check if it's AI-generated or template
                if len(latest_eval.explanation) > 150 and '...' not in latest_eval.explanation[:50]:
                    print('   → Appears to be AI-generated (detailed text)')
                else:
                    print('   → Appears to be template-based (short/generic)')
            else:
                print('   ✗ No explanation')

            if latest_eval.recommendations:
                print(f'   ✓ Has Recommendations ({len(latest_eval.recommendations)} items)')
                if latest_eval.recommendations and isinstance(latest_eval.recommendations[0], dict):
                    if 'reasoning' in latest_eval.recommendations[0]:
                        print('   → AI-generated recommendations (has reasoning)')
                    else:
                        print('   → Template-based recommendations')
            else:
                print('   ✗ No recommendations')

# Summary
print('\n' + '=' * 70)
print('SUMMARY:')
print('=' * 70)
if ai_service._check_ai_available():
    print('✓ OpenAI is FULLY CONFIGURED and ACTIVE')
    print('')
    print('Your Playbook is using GPT-4o-mini for:')
    print('  • Natural language goal parsing')
    print('  • Detailed WHY explanations')
    print('  • Actionable recommendations with reasoning')
    print('  • Trend analysis')
    print('  • Risk factor identification')
    print('  • Forecasting with scenarios')
    print('  • Conversational what-if simulations')
else:
    print('✗ OpenAI is NOT available - using fallback mode')
    print('')
    print('Your Playbook is using rule-based logic:')
    print('  • Keyword-based goal parsing')
    print('  • Template-based explanations')
    print('  • Basic recommendations')
    print('  • Simple trend statistics')
print('=' * 70)

