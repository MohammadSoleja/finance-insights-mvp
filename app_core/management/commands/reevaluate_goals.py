"""
Management command to force re-evaluation of all goals.
Useful after fixing evaluation logic to update existing goals.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal

from app_core.models import FinancialGoal
from app_core.playbook_engine import evaluate_goal


class Command(BaseCommand):
    help = 'Force re-evaluation of all active goals (ignores last_evaluated_at)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--goal-id',
            type=int,
            help='Re-evaluate specific goal only'
        )

    def handle(self, *args, **options):
        goal_id = options.get('goal_id')

        if goal_id:
            goals = FinancialGoal.objects.filter(id=goal_id, active=True)
        else:
            goals = FinancialGoal.objects.filter(active=True)

        if not goals.exists():
            self.stdout.write(self.style.WARNING('No active goals found'))
            return

        self.stdout.write(f"Re-evaluating {goals.count()} goal(s)...")

        updated_count = 0

        for goal in goals:
            try:
                # Run evaluation with new logic
                evaluation_data = evaluate_goal(goal)

                # Update goal status
                old_status = goal.current_status
                new_status = evaluation_data['status']

                goal.current_status = new_status
                goal.current_value = evaluation_data.get('current_value')
                goal.progress_percentage = evaluation_data.get('progress_percentage', Decimal('0'))
                goal.last_evaluated_at = timezone.now()
                goal.save()

                if old_status != new_status:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ {goal.name}: {old_status} → {new_status} ({goal.progress_percentage}%)"
                        )
                    )
                else:
                    self.stdout.write(
                        f"  - {goal.name}: {new_status} ({goal.progress_percentage}%)"
                    )

                updated_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Error with {goal.name}: {str(e)}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Re-evaluated {updated_count} goal(s)")
        )

