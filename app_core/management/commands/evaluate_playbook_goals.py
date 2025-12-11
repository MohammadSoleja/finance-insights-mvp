# app_core/management/commands/evaluate_playbook_goals.py
"""
Management command to evaluate all active financial goals.
Generates AI insights and stores evaluation history.

Usage:
    python manage.py evaluate_playbook_goals
    python manage.py evaluate_playbook_goals --organization-id=1
    python manage.py evaluate_playbook_goals --goal-id=5
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from decimal import Decimal

from app_core.models import FinancialGoal, GoalEvaluation, Organization
from app_core.playbook_engine import evaluate_goal
from app_core import ai_service


class Command(BaseCommand):
    help = 'Evaluate all active financial goals and generate AI insights'

    def add_arguments(self, parser):
        parser.add_argument(
            '--organization-id',
            type=int,
            help='Evaluate goals for specific organization only'
        )
        parser.add_argument(
            '--goal-id',
            type=int,
            help='Evaluate specific goal only'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force evaluation even if recently evaluated'
        )

    def handle(self, *args, **options):
        organization_id = options.get('organization_id')
        goal_id = options.get('goal_id')
        force = options.get('force', False)

        # Build query
        goals = FinancialGoal.objects.filter(active=True)

        if goal_id:
            goals = goals.filter(id=goal_id)
        elif organization_id:
            goals = goals.filter(organization_id=organization_id)

        goals = goals.select_related('organization', 'created_by')

        if not goals.exists():
            self.stdout.write(self.style.WARNING('No active goals found matching criteria'))
            return

        self.stdout.write(f"Found {goals.count()} goal(s) to evaluate")

        evaluated_count = 0
        skipped_count = 0
        error_count = 0

        for goal in goals:
            try:
                # Skip if recently evaluated (unless force)
                if not force and goal.last_evaluated_at:
                    hours_since_eval = (timezone.now() - goal.last_evaluated_at).total_seconds() / 3600
                    if hours_since_eval < 6:  # Skip if evaluated in last 6 hours
                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipping '{goal.name}' - evaluated {hours_since_eval:.1f} hours ago"
                            )
                        )
                        skipped_count += 1
                        continue

                self.stdout.write(f"Evaluating: {goal.name} ({goal.get_goal_type_display()})...")

                # Run evaluation engine
                evaluation_data = evaluate_goal(goal)

                # Get historical evaluations for AI context
                historical_evaluations = list(
                    GoalEvaluation.objects.filter(goal=goal)
                    .order_by('-evaluated_at')[:10]
                )

                # Generate AI insights
                explanation = ''
                recommendations = []
                risk_factors = []
                trend_analysis = ''
                forecast = {}

                try:
                    self.stdout.write("  Generating AI insights...")

                    # Generate explanation (WHY analysis)
                    explanation = ai_service.generate_goal_explanation(
                        goal, evaluation_data, historical_evaluations
                    )

                    # Generate recommendations
                    recommendations = ai_service.generate_recommendations(
                        goal, evaluation_data
                    )

                    # Generate trend analysis (if enough history)
                    if len(historical_evaluations) >= 2:
                        trend_analysis = ai_service.generate_trend_analysis(
                            goal, historical_evaluations
                        )

                    # Identify risk factors
                    risk_factors = ai_service.identify_risk_factors(
                        goal, evaluation_data
                    )

                    # Generate forecast (if enabled and enough data)
                    if len(historical_evaluations) >= 3:
                        forecast = ai_service.generate_forecast(
                            goal, evaluation_data, historical_evaluations
                        )

                except Exception as ai_error:
                    self.stdout.write(
                        self.style.WARNING(f"  AI insights generation failed: {str(ai_error)}")
                    )
                    # Continue with evaluation even if AI fails

                # Create evaluation snapshot
                evaluation = GoalEvaluation.objects.create(
                    goal=goal,
                    status=evaluation_data['status'],
                    current_value=evaluation_data.get('current_value'),
                    progress_percentage=evaluation_data.get('progress_percentage', Decimal('0')),
                    metrics=evaluation_data.get('metrics', {}),
                    explanation=explanation,
                    recommendations=recommendations,
                    risk_factors=risk_factors,
                    trend_analysis=trend_analysis,
                    forecast=forecast,
                )

                # Update goal cached fields
                goal.current_status = evaluation_data['status']
                goal.current_value = evaluation_data.get('current_value')
                goal.progress_percentage = evaluation_data.get('progress_percentage', Decimal('0'))
                goal.last_evaluated_at = timezone.now()
                goal.last_explanation = explanation
                goal.last_recommendations = recommendations
                goal.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ {goal.name}: {evaluation_data['status']} "
                        f"({evaluation_data.get('progress_percentage', 0)}% progress)"
                    )
                )
                evaluated_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Error evaluating '{goal.name}': {str(e)}")
                )
                error_count += 1
                import traceback
                self.stdout.write(traceback.format_exc())

        # Summary
        self.stdout.write(self.style.SUCCESS(f"\n{'='*50}"))
        self.stdout.write(self.style.SUCCESS(f"Evaluation complete:"))
        self.stdout.write(self.style.SUCCESS(f"  ✓ Evaluated: {evaluated_count}"))
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(f"  - Skipped: {skipped_count}"))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"  ✗ Errors: {error_count}"))
        self.stdout.write(self.style.SUCCESS(f"{'='*50}"))

