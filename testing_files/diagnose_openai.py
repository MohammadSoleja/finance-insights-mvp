#!/usr/bin/env python
"""
Comprehensive OpenAI integration test.
This will tell us exactly what's wrong.
"""
import os
import sys

# Force fresh import of settings
if 'django' in sys.modules:
    del sys.modules['django']
if 'financeinsights.settings' in sys.modules:
    del sys.modules['financeinsights.settings']

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'financeinsights.settings')

import django
django.setup()

from django.conf import settings
from app_core import ai_service
from app_core.models import FinancialGoal
from app_core.playbook_engine import evaluate_goal

print("=" * 80)
print("COMPREHENSIVE OPENAI DIAGNOSTIC TEST")
print("=" * 80)

# Test 1: Configuration
print("\n[TEST 1] Configuration Check")
print("-" * 80)
print(f"AI_PLAYBOOK_ENABLED: {settings.AI_PLAYBOOK_ENABLED}")
print(f"OPENAI_API_KEY length: {len(settings.OPENAI_API_KEY)}")
print(f"OPENAI_API_KEY first 20 chars: {settings.OPENAI_API_KEY[:20]}")
print(f"OPENAI_API_KEY last 10 chars: ...{settings.OPENAI_API_KEY[-10:]}")
print(f"OPENAI_MODEL: {settings.OPENAI_MODEL}")
print(f"OPENAI_MAX_TOKENS: {settings.OPENAI_MAX_TOKENS}")
print(f"OPENAI_TEMPERATURE: {settings.OPENAI_TEMPERATURE}")

# Test 2: Library Check
print("\n[TEST 2] OpenAI Library Check")
print("-" * 80)
print(f"OPENAI_AVAILABLE (import check): {ai_service.OPENAI_AVAILABLE}")
if ai_service.OPENAI_AVAILABLE:
    import openai
    print(f"✓ OpenAI library version: {openai.__version__}")
else:
    print("✗ OpenAI library NOT imported")

# Test 3: AI Availability Check
print("\n[TEST 3] AI Service Availability")
print("-" * 80)
available = ai_service._check_ai_available()
print(f"_check_ai_available() result: {available}")

if not available:
    print("\nDEBUGGING why AI is not available:")
    print(f"  - AI_PLAYBOOK_ENABLED: {settings.AI_PLAYBOOK_ENABLED}")
    print(f"  - OPENAI_AVAILABLE: {ai_service.OPENAI_AVAILABLE}")
    print(f"  - OPENAI_API_KEY set: {bool(settings.OPENAI_API_KEY)}")

    if not settings.AI_PLAYBOOK_ENABLED:
        print("  ✗ ISSUE: AI_PLAYBOOK_ENABLED is False")
    if not ai_service.OPENAI_AVAILABLE:
        print("  ✗ ISSUE: OpenAI library not available")
    if not settings.OPENAI_API_KEY:
        print("  ✗ ISSUE: OPENAI_API_KEY is empty")

# Test 4: Direct API Call
print("\n[TEST 4] Direct OpenAI API Test")
print("-" * 80)
if available:
    try:
        client = ai_service._get_openai_client()
        print("Making API call to OpenAI...")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Reply with exactly: 'API works!'"}
            ],
            max_tokens=10
        )

        result = response.choices[0].message.content
        tokens = response.usage.total_tokens

        print(f"✓ SUCCESS!")
        print(f"  Response: {result}")
        print(f"  Tokens used: {tokens}")
        print(f"  Model: {response.model}")

    except Exception as e:
        print(f"✗ FAILED!")
        print(f"  Error type: {type(e).__name__}")
        print(f"  Error message: {str(e)}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
else:
    print("Skipping - AI not available")

# Test 5: Goal Explanation Generation
print("\n[TEST 5] Goal Explanation Generation Test")
print("-" * 80)

goal = FinancialGoal.objects.filter(active=True).first()
if goal:
    print(f"Testing with goal: {goal.name}")
    print(f"Goal type: {goal.goal_type}")

    # Get evaluation data
    evaluation_data = evaluate_goal(goal)
    print(f"Current status: {evaluation_data['status']}")
    print(f"Progress: {evaluation_data['progress_percentage']}%")

    print("\nGenerating explanation...")
    try:
        explanation = ai_service.generate_goal_explanation(goal, evaluation_data, [])

        print(f"\n✓ Explanation generated ({len(explanation)} characters)")
        print("\n" + "=" * 80)
        print("EXPLANATION:")
        print("=" * 80)
        print(explanation)
        print("=" * 80)

        # Analyze if it's AI or fallback
        if "Your goal is" in explanation[:50]:
            print("\n⚠️  WARNING: This looks like FALLBACK template text")
            print("    Expected AI text to be more conversational and detailed")
        elif len(explanation) < 100:
            print("\n⚠️  WARNING: Very short explanation - likely fallback")
        else:
            print("\n✓ This appears to be AI-generated content!")

    except Exception as e:
        print(f"\n✗ Error generating explanation: {e}")
        import traceback
        traceback.print_exc()
else:
    print("No active goals found to test")

# Test 6: Recommendations
print("\n[TEST 6] Recommendations Generation Test")
print("-" * 80)

if goal and available:
    try:
        recommendations = ai_service.generate_recommendations(goal, evaluation_data)
        print(f"✓ Generated {len(recommendations)} recommendations")

        for i, rec in enumerate(recommendations, 1):
            print(f"\n  Recommendation {i}:")
            print(f"    Action: {rec.get('action', 'N/A')}")
            print(f"    Impact: {rec.get('impact', 'N/A')}")
            print(f"    Priority: {rec.get('priority', 'N/A')}")
            if 'reasoning' in rec:
                print(f"    Reasoning: {rec['reasoning'][:100]}...")

        if recommendations and 'reasoning' in recommendations[0]:
            print("\n✓ Recommendations have reasoning - likely AI-generated")
        else:
            print("\n⚠️  No reasoning field - likely fallback")

    except Exception as e:
        print(f"✗ Error: {e}")

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)

if available:
    print("\n✓ OpenAI is configured and API calls succeed")
    print("  If you're still seeing template text, try:")
    print("  1. Restart your Django server")
    print("  2. Clear browser cache")
    print("  3. Click 'Refresh' button on a goal")
else:
    print("\n✗ OpenAI is NOT working")
    print("  Check the issues listed above")

