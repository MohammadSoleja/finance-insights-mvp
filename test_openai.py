#!/usr/bin/env python
"""
Test script to verify OpenAI API is working and generate a test explanation.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'financeinsights.settings')
django.setup()

from django.conf import settings
from app_core import ai_service
from app_core.models import FinancialGoal
from app_core.playbook_engine import evaluate_goal

print("=" * 70)
print("TESTING OPENAI API CONNECTION")
print("=" * 70)

# Step 1: Check configuration
print("\n1. Configuration Check:")
print("-" * 70)
print(f"   AI_PLAYBOOK_ENABLED: {settings.AI_PLAYBOOK_ENABLED}")
print(f"   OPENAI_API_KEY set: {bool(settings.OPENAI_API_KEY)}")
if settings.OPENAI_API_KEY:
    print(f"   API Key: {settings.OPENAI_API_KEY[:20]}...{settings.OPENAI_API_KEY[-10:]}")
print(f"   OPENAI_MODEL: {settings.OPENAI_MODEL}")
print(f"   OPENAI_AVAILABLE: {ai_service.OPENAI_AVAILABLE}")
print(f"   _check_ai_available(): {ai_service._check_ai_available()}")

# Step 2: Test simple API call
print("\n2. Testing Simple API Call:")
print("-" * 70)
if ai_service._check_ai_available():
    try:
        client = ai_service._get_openai_client()
        print("   Making test API call...")
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": "Reply with exactly: 'AI is working!'"}],
            max_tokens=20
        )
        print(f"   ✓ Response: {response.choices[0].message.content}")
        print(f"   ✓ Tokens used: {response.usage.total_tokens}")
        print("   ✓ OpenAI API is WORKING!")
    except Exception as e:
        print(f"   ✗ API Error: {type(e).__name__}: {str(e)}")
        print("   ✗ OpenAI API is NOT working!")
else:
    print("   ✗ AI check failed - won't make API call")

# Step 3: Test with actual goal
print("\n3. Testing Goal Explanation Generation:")
print("-" * 70)
goal = FinancialGoal.objects.filter(active=True).first()
if goal:
    print(f"   Testing with goal: {goal.name}")

    # Get evaluation data
    evaluation_data = evaluate_goal(goal)
    print(f"   Status: {evaluation_data['status']}")
    print(f"   Progress: {evaluation_data['progress_percentage']}%")

    # Try to generate AI explanation
    print("\n   Generating AI explanation...")
    try:
        explanation = ai_service.generate_goal_explanation(goal, evaluation_data, [])
        print(f"   ✓ Generated explanation ({len(explanation)} chars)")
        print(f"\n   Explanation:")
        print(f"   {'-' * 66}")
        print(f"   {explanation}")
        print(f"   {'-' * 66}")

        # Check if it's AI or fallback
        if len(explanation) > 150 and "Your goal is" not in explanation[:50]:
            print("\n   ✓ This appears to be AI-GENERATED content!")
        else:
            print("\n   ✗ This appears to be FALLBACK template content")

    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {str(e)}")
        import traceback
        print(traceback.format_exc())
else:
    print("   No active goals found to test")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)

