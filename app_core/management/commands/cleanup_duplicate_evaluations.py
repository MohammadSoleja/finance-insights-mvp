"""
Management command to clean up duplicate goal evaluations.
Keeps only the latest evaluation per day for each goal.
"""

from django.core.management.base import BaseCommand
from django.db.models import Count
from datetime import datetime

from app_core.models import GoalEvaluation


class Command(BaseCommand):
    help = 'Remove duplicate goal evaluations (keep only latest per day)'

    def handle(self, *args, **options):
        self.stdout.write("Scanning for duplicate evaluations...")

        # Get all evaluations
        all_evaluations = GoalEvaluation.objects.all().order_by('goal', 'evaluated_at')

        duplicates_removed = 0
        goals_processed = set()

        # Group by goal and date
        from collections import defaultdict
        by_goal_and_date = defaultdict(list)

        for eval in all_evaluations:
            date_key = eval.evaluated_at.date()
            key = (eval.goal_id, date_key)
            by_goal_and_date[key].append(eval)

        # For each goal+date combination, keep only the latest
        for (goal_id, date), evaluations in by_goal_and_date.items():
            if len(evaluations) > 1:
                # Sort by evaluated_at, keep the latest
                evaluations.sort(key=lambda e: e.evaluated_at, reverse=True)
                latest = evaluations[0]
                to_delete = evaluations[1:]

                self.stdout.write(
                    f"  Goal {goal_id}, {date}: Found {len(evaluations)} evaluations, keeping latest"
                )

                # Delete the older ones
                for eval in to_delete:
                    eval.delete()
                    duplicates_removed += 1

                goals_processed.add(goal_id)

        if duplicates_removed > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✓ Removed {duplicates_removed} duplicate evaluations across {len(goals_processed)} goals"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("\n✓ No duplicates found - database is clean"))

