# app_core/budgets.py
"""
Budget calculation utilities
"""
from decimal import Decimal
from django.db.models import Sum, Q
from django.utils import timezone
import datetime
import calendar


def get_period_dates(period_type, budget=None):
    """
    Returns (start_date, end_date) for the given period type.
    If period_type is 'custom' and budget is provided, uses budget's custom dates.
    """
    today = timezone.now().date()

    if period_type == 'custom':
        # Use custom dates from budget if provided
        if budget and budget.start_date and budget.end_date:
            return budget.start_date, budget.end_date
        # Fallback to current month if custom dates not set
        start = datetime.date(today.year, today.month, 1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        end = datetime.date(today.year, today.month, last_day)
        return start, end

    if period_type == 'weekly':
        # Current week (Monday to Sunday)
        start = today - datetime.timedelta(days=today.weekday())
        end = start + datetime.timedelta(days=6)
    elif period_type == 'yearly':
        # Current year
        start = datetime.date(today.year, 1, 1)
        end = datetime.date(today.year, 12, 31)
    else:  # monthly (default)
        # Current month
        start = datetime.date(today.year, today.month, 1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        end = datetime.date(today.year, today.month, last_day)

    return start, end


def calculate_budget_usage(budget, transaction_model):
    """
    Calculate how much of a budget has been spent in the current period.
    Now supports multiple labels per budget.
    Returns a dict with: spent, remaining, percent_used, is_over
    """
    start_date, end_date = get_period_dates(budget.period, budget)

    # Get all labels for this budget
    budget_labels = budget.labels.all()

    if budget_labels.exists():
        # Track spending for transactions with ANY of the budget's labels
        spent_qs = transaction_model.objects.filter(
            organization=budget.organization,
            label__in=budget_labels,
            direction='outflow',
            date__gte=start_date,
            date__lte=end_date
        )
    else:
        # Fallback: use old category field for backward compatibility
        if budget.category:
            spent_qs = transaction_model.objects.filter(
                organization=budget.organization,
                category=budget.category,
                direction='outflow',
                date__gte=start_date,
                date__lte=end_date
            )
        else:
            # No labels or category - no spending to track
            spent_qs = transaction_model.objects.none()

    spent = spent_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    budget_amount = budget.amount
    remaining = budget_amount - spent

    percent_used = 0
    if budget_amount > 0:
        percent_used = float((spent / budget_amount) * 100)

    is_over = spent > budget_amount

    return {
        'spent': float(spent),
        'remaining': float(remaining),
        'percent_used': round(percent_used, 1),
        'is_over': is_over,
        'budget_amount': float(budget_amount),
        'start_date': start_date,
        'end_date': end_date,
    }


def get_budget_summary(organization, transaction_model):
    """
    Get summary of all active budgets for an organization.
    Returns list of budget info dicts sorted by percent used (descending).
    """
    from app_core.models import Budget

    budgets = Budget.objects.filter(organization=organization, active=True).prefetch_related('labels').order_by('name')
    summary = []

    for budget in budgets:
        usage = calculate_budget_usage(budget, transaction_model)

        # Get label names for display
        label_names = [label.name for label in budget.labels.all()]

        # Format period display based on type
        period_display = budget.get_period_display()
        if budget.period == Budget.PERIOD_CUSTOM and budget.start_date:
            # For monthly recurring budgets (which become custom), show "Nov 2025" format
            if budget.start_date and budget.end_date:
                # Check if it's a full month (1st to last day)
                from calendar import monthrange
                last_day = monthrange(budget.start_date.year, budget.start_date.month)[1]
                if budget.start_date.day == 1 and budget.end_date.day == last_day:
                    # It's a full month, show "Nov 2025" format
                    period_display = budget.start_date.strftime('%b %Y')
                else:
                    # Show date range
                    period_display = f"{budget.start_date.strftime('%b %d')} - {budget.end_date.strftime('%b %d')}"

        summary.append({
            'id': budget.id,
            'name': budget.name,
            'category': budget.category or '',  # backward compatibility
            'labels': label_names,
            'period': period_display,
            'period_value': budget.period,
            'recurring_group_id': budget.recurring_group_id,
            **usage
        })

    # Sort by percent used (highest first) to show at-risk budgets first
    summary.sort(key=lambda x: x['percent_used'], reverse=True)

    return summary

