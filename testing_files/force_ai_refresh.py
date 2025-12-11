#!/usr/bin/env python
"""
Force refresh all goals with AI explanations.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'financeinsights.settings')
django.setup()

from app_core.models import FinancialGoal, GoalEvaluation
from app_core.playbook_engine import evaluate_goal
from app_core import ai_service
from django.utils import timezone
from decimal import Decimal

print("Forcing AI refresh on all goals...")
print("=" * 70)

goals = FinancialGoal.objects.filter(active=True)
print(f"Found {goals.count()} active goal(s)\n")

for goal in goals:
    print(f"Goal: {goal.name}")
    print(f"Type: {goal.get_goal_type_display()}")

    # Run evaluation
    evaluation_data = evaluate_goal(goal)
    print(f"Status: {evaluation_data['status']} ({evaluation_data['progress_percentage']}%)")

    # Get historical for context
    historical = list(GoalEvaluation.objects.filter(goal=goal).order_by('-evaluated_at')[:10])

    # Force AI generation
    print("Calling OpenAI API...")
    try:
        explanation = ai_service.generate_goal_explanation(goal, evaluation_data, historical)

        if explanation and len(explanation) > 150:
            print(f"✓ AI Explanation generated ({len(explanation)} chars)")
            print(f"\nExplanation preview:")
            print("-" * 70)
            print(explanation[:300] + "...")
            print("-" * 70)

            # Save to goal
            goal.last_explanation = explanation
            goal.save()
            print("✓ Saved to goal")
        else:
            print(f"✗ Fallback used ({len(explanation)} chars): {explanation[:100]}")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70 + "\n")

print("Done!")

