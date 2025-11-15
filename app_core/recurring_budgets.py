# app_core/recurring_budgets.py
"""
Utility functions for managing recurring budgets.
"""
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from .models import Budget


def get_next_period_start(current_date, period):
    """
    Calculate the next period start date based on period type.
    """
    if period == Budget.PERIOD_WEEKLY:
        return current_date + timedelta(weeks=1)
    elif period == Budget.PERIOD_MONTHLY:
        return current_date + relativedelta(months=1)
    elif period == Budget.PERIOD_YEARLY:
        return current_date + relativedelta(years=1)
    return current_date


def get_period_end(start_date, period):
    """
    Calculate the end date for a period given its start date.
    """
    if period == Budget.PERIOD_WEEKLY:
        return start_date + timedelta(days=6)
    elif period == Budget.PERIOD_MONTHLY:
        # Last day of the month
        next_month = start_date + relativedelta(months=1)
        return next_month - timedelta(days=1)
    elif period == Budget.PERIOD_YEARLY:
        # Last day of the year
        return date(start_date.year, 12, 31)
    return start_date


def generate_recurring_budgets(user=None):
    """
    Generate budgets from recurring budget templates.

    For budgets with is_recurring=True and recurrence_count set:
    - Creates copies of the budget for the next N periods
    - Each copy has the same amount, labels, and settings
    - Updates last_generated_period to track progress

    Args:
        user: Optional user to limit generation to specific user

    Returns:
        Number of budgets created
    """
    query = Budget.objects.filter(is_recurring=True, active=True)
    if user:
        query = query.filter(user=user)

    # Only process budgets that have a recurrence count and aren't custom period
    query = query.exclude(period=Budget.PERIOD_CUSTOM).filter(recurrence_count__isnull=False, recurrence_count__gt=0)

    recurring_budgets = query.all()
    budgets_created = 0

    for template_budget in recurring_budgets:
        # Determine the starting point for generation
        if template_budget.last_generated_period:
            # Start from the next period after last generated
            current_period_start = get_next_period_start(template_budget.last_generated_period, template_budget.period)
        else:
            # First time generating - start from NEXT period after the budget's period
            # The original budget itself represents the current period
            if template_budget.start_date:
                # Start from next period after the budget's start_date
                current_period_start = get_next_period_start(template_budget.start_date, template_budget.period)
            else:
                # Calculate current period, then move to next
                today = template_budget.created_at.date()
                if template_budget.period == Budget.PERIOD_MONTHLY:
                    # First day of next month
                    current_period_start = today.replace(day=1) + relativedelta(months=1)
                elif template_budget.period == Budget.PERIOD_YEARLY:
                    # First day of next year
                    current_period_start = date(today.year + 1, 1, 1)
                elif template_budget.period == Budget.PERIOD_WEEKLY:
                    # Start of next week
                    start_of_week = today - timedelta(days=today.weekday())
                    current_period_start = start_of_week + timedelta(weeks=1)
                else:
                    current_period_start = today

        # Generate exactly recurrence_count FUTURE periods (not including the original)
        periods_to_generate = template_budget.recurrence_count

        for i in range(periods_to_generate):
            # Calculate period dates
            period_start = current_period_start
            period_end = get_period_end(period_start, template_budget.period)

            # Check if a budget already exists for this period
            existing = Budget.objects.filter(
                user=template_budget.user,
                name=template_budget.name,
                period=template_budget.period,
                start_date=period_start,
                end_date=period_end,
            ).exists()

            if not existing:
                # Create the new budget period
                new_budget = Budget.objects.create(
                    user=template_budget.user,
                    name=template_budget.name,
                    amount=template_budget.amount,
                    period=Budget.PERIOD_CUSTOM,  # Generated budgets are custom with specific dates
                    start_date=period_start,
                    end_date=period_end,
                    active=True,
                    is_recurring=False,  # Generated budgets are not themselves recurring
                    recurring_group_id=template_budget.recurring_group_id,  # Link to same group
                )

                # Copy the labels (M2M relationship)
                for label in template_budget.labels.all():
                    new_budget.labels.add(label)

                budgets_created += 1

            # Update template's last_generated_period
            template_budget.last_generated_period = period_start
            template_budget.save(update_fields=['last_generated_period', 'updated_at'])

            # Move to next period
            current_period_start = get_next_period_start(current_period_start, template_budget.period)

    return budgets_created


def preview_recurring_budget_periods(budget, num_periods=None):
    """
    Preview the periods that will be generated for a recurring budget.

    Args:
        budget: Budget instance with is_recurring=True
        num_periods: Number of periods to preview (uses recurrence_count if None)

    Returns:
        List of dicts with 'start_date' and 'end_date' for each period
    """
    if not budget.is_recurring or budget.period == Budget.PERIOD_CUSTOM:
        return []

    periods = []
    count = num_periods or budget.recurrence_count or 3

    # Start from budget's start_date or current period
    if budget.start_date:
        current_start = budget.start_date
    else:
        today = timezone.now().date()
        if budget.period == Budget.PERIOD_MONTHLY:
            current_start = today.replace(day=1)
        elif budget.period == Budget.PERIOD_YEARLY:
            current_start = today.replace(month=1, day=1)
        elif budget.period == Budget.PERIOD_WEEKLY:
            # Start of current week (Monday)
            current_start = today - timedelta(days=today.weekday())
        else:
            current_start = today

    for i in range(count):
        period_end = get_period_end(current_start, budget.period)
        periods.append({
            'start_date': current_start,
            'end_date': period_end,
            'name': f"{budget.name} ({current_start.strftime('%b %Y')})"
        })
        current_start = get_next_period_start(current_start, budget.period)

    return periods

