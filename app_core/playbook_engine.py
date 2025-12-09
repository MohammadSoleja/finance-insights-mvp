# app_core/playbook_engine.py
"""
AI Financial Playbook - Goal Evaluation Engine
Evaluates financial goals using existing transaction/budget data.
Reuses metrics.py functions for consistency.
"""

from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import Dict, Optional, List
from django.db.models import Sum, Q
from django.utils import timezone

from .models import Transaction, Budget, Organization, Label
from .metrics import queryset_to_df, kpis, timeseries


def evaluate_goal(goal, as_of_date: Optional[date] = None) -> Dict:
    """
    Calculate current progress for a goal.

    Args:
        goal: FinancialGoal instance
        as_of_date: Date to evaluate as of (defaults to today)

    Returns:
        dict with: current_value, target_value, progress_percentage, status, metrics
    """
    if as_of_date is None:
        as_of_date = timezone.now().date()

    # Route to type-specific evaluation
    if goal.goal_type == 'runway':
        return evaluate_runway_goal(goal, as_of_date)
    elif goal.goal_type == 'savings':
        return evaluate_savings_goal(goal, as_of_date)
    elif goal.goal_type == 'spending_limit':
        return evaluate_spending_limit_goal(goal, as_of_date)
    elif goal.goal_type == 'budget_compliance':
        return evaluate_budget_compliance_goal(goal, as_of_date)
    elif goal.goal_type == 'revenue_target':
        return evaluate_revenue_target_goal(goal, as_of_date)
    elif goal.goal_type == 'profit_margin':
        return evaluate_profit_margin_goal(goal, as_of_date)
    else:
        return {
            'current_value': Decimal('0'),
            'target_value': goal.target_value or Decimal('0'),
            'progress_percentage': Decimal('0'),
            'status': 'not_started',
            'metrics': {},
            'error': f"Unknown goal type: {goal.goal_type}"
        }


def evaluate_runway_goal(goal, as_of_date: date) -> Dict:
    """
    Evaluate cash runway goal.
    Calculates months of runway based on current burn rate.

    Goal parameters:
    - target_value: Number of months of runway desired
    - target_date: Date by which to achieve
    """
    organization = goal.organization

    # Calculate runway
    runway_data = calculate_runway(organization, as_of_date)

    current_months = runway_data['runway_months']
    target_months = goal.target_value or Decimal('6')  # Default 6 months

    # Calculate progress percentage
    if target_months > 0:
        progress = (current_months / target_months) * Decimal('100')
    else:
        progress = Decimal('0')

    progress = min(progress, Decimal('100'))  # Cap at 100%

    # Determine status
    status = _determine_status(progress, goal.target_date, as_of_date)

    return {
        'current_value': current_months,
        'target_value': target_months,
        'progress_percentage': round(progress, 2),
        'status': status,
        'metrics': runway_data,
    }


def evaluate_savings_goal(goal, as_of_date: date) -> Dict:
    """
    Evaluate savings target goal.
    Tracks progress toward a specific savings amount.

    Goal parameters:
    - target_value: Amount to save
    - parameters.start_date: When to start tracking
    - parameters.label_ids: Optional labels to track for savings
    """
    organization = goal.organization
    params = goal.parameters or {}

    # Get date range
    start_date = params.get('start_date')
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if isinstance(start_date, str) else start_date
    else:
        start_date = goal.created_at.date()

    # Get transactions in range
    txs = Transaction.objects.filter(
        organization=organization,
        date__gte=start_date,
        date__lte=as_of_date
    )

    # Filter by labels if specified
    label_ids = params.get('label_ids', [])
    if label_ids:
        txs = txs.filter(label_id__in=label_ids)

    # Calculate net savings (inflows - outflows)
    df = queryset_to_df(txs)
    metrics = kpis(df)

    current_savings = Decimal(str(metrics['net']))
    target_savings = goal.target_value or Decimal('10000')  # Default £10k

    # Calculate progress
    if target_savings > 0:
        progress = (current_savings / target_savings) * Decimal('100')
    else:
        progress = Decimal('0')

    progress = max(Decimal('0'), min(progress, Decimal('100')))  # Clamp 0-100%

    # Determine status
    status = _determine_status(progress, goal.target_date, as_of_date)

    return {
        'current_value': current_savings,
        'target_value': target_savings,
        'progress_percentage': round(progress, 2),
        'status': status,
        'metrics': {
            'inflow': metrics['inflow'],
            'outflow': metrics['outflow'],
            'net': metrics['net'],
            'tx_count': metrics['tx_count'],
            'start_date': start_date.isoformat(),
        },
    }


def evaluate_spending_limit_goal(goal, as_of_date: date) -> Dict:
    """
    Evaluate spending limit goal.
    Checks if spending is within specified limits.

    Goal parameters:
    - target_value: Maximum allowed spending
    - parameters.period: 'daily', 'weekly', 'monthly', 'yearly'
    - parameters.label_ids: Labels to track
    - parameters.category: Optional category filter
    """
    organization = goal.organization
    params = goal.parameters or {}

    # Get period
    period = params.get('period', 'monthly')
    start_date = _get_period_start(as_of_date, period)

    # Get transactions in period
    txs = Transaction.objects.filter(
        organization=organization,
        date__gte=start_date,
        date__lte=as_of_date,
        direction='outflow'  # Only track outflows
    )

    # Filter by labels if specified
    label_ids = params.get('label_ids', [])
    if label_ids:
        txs = txs.filter(label_id__in=label_ids)

    # Filter by category if specified
    category = params.get('category')
    if category:
        txs = txs.filter(category=category)

    # Calculate spending
    df = queryset_to_df(txs)
    metrics = kpis(df)

    current_spending = Decimal(str(metrics['outflow']))
    target_limit = goal.target_value or Decimal('5000')  # Default £5k

    # Calculate usage percentage (inverted - higher is worse)
    if target_limit > 0:
        usage_pct = (current_spending / target_limit) * Decimal('100')
    else:
        usage_pct = Decimal('0')

    # Progress is inverted - we want to be UNDER the limit
    # 100% progress = staying well under limit
    progress = max(Decimal('0'), Decimal('100') - usage_pct)

    # Determine status - spending limits are special
    # They should only be "achieved" if we've passed the target date AND stayed under budget
    if goal.target_date and as_of_date < goal.target_date:
        # Still in progress - can't be achieved yet
        if usage_pct <= 75:
            status = 'on_track'
        elif usage_pct <= 90:
            status = 'at_risk'
        else:
            status = 'off_track'  # Over or near limit
    else:
        # Past target date or no target date
        if usage_pct <= 100:
            status = 'achieved'  # Successfully stayed within limit
        else:
            status = 'off_track'  # Went over limit

    return {
        'current_value': current_spending,
        'target_value': target_limit,
        'progress_percentage': round(progress, 2),
        'status': status,
        'metrics': {
            'spending': float(current_spending),
            'limit': float(target_limit),
            'usage_percentage': float(usage_pct),
            'over_limit': usage_pct > 100,
            'period': period,
            'start_date': start_date.isoformat(),
            'tx_count': metrics['tx_count'],
        },
    }


def evaluate_budget_compliance_goal(goal, as_of_date: date) -> Dict:
    """
    Evaluate budget compliance goal.
    Compare actual spending vs budget using existing Budget model logic.

    Goal parameters:
    - parameters.budget_id: Budget to track
    """
    organization = goal.organization
    params = goal.parameters or {}

    budget_id = params.get('budget_id')
    if not budget_id:
        return {
            'current_value': Decimal('0'),
            'target_value': Decimal('0'),
            'progress_percentage': Decimal('0'),
            'status': 'not_started',
            'metrics': {'error': 'No budget_id specified'},
        }

    try:
        budget = Budget.objects.get(id=budget_id, organization=organization)
    except Budget.DoesNotExist:
        return {
            'current_value': Decimal('0'),
            'target_value': Decimal('0'),
            'progress_percentage': Decimal('0'),
            'status': 'not_started',
            'metrics': {'error': f'Budget {budget_id} not found'},
        }

    # Get budget period dates
    if budget.period == 'custom' and budget.start_date and budget.end_date:
        start_date = budget.start_date
        end_date = min(budget.end_date, as_of_date)
    else:
        # For recurring budgets, get current period
        start_date = _get_period_start(as_of_date, budget.period)
        end_date = as_of_date

    # Get transactions for budget labels
    label_ids = list(budget.labels.values_list('id', flat=True))

    if label_ids:
        txs = Transaction.objects.filter(
            organization=organization,
            label_id__in=label_ids,
            date__gte=start_date,
            date__lte=end_date,
            direction='outflow'
        )
    else:
        # Fallback to category if no labels
        txs = Transaction.objects.filter(
            organization=organization,
            category=budget.category,
            date__gte=start_date,
            date__lte=end_date,
            direction='outflow'
        )

    # Calculate actual spending
    df = queryset_to_df(txs)
    metrics = kpis(df)

    actual_spending = Decimal(str(metrics['outflow']))
    budget_amount = budget.amount

    # Calculate usage percentage
    if budget_amount > 0:
        usage_pct = (actual_spending / budget_amount) * Decimal('100')
    else:
        usage_pct = Decimal('0')

    # Progress is inverted - staying under budget is good
    progress = max(Decimal('0'), Decimal('100') - usage_pct)

    # Determine status
    if usage_pct <= 80:
        status = 'on_track'
    elif usage_pct <= 95:
        status = 'at_risk'
    elif usage_pct <= 100:
        status = 'off_track'
    else:
        status = 'off_track'  # Over budget

    return {
        'current_value': actual_spending,
        'target_value': budget_amount,
        'progress_percentage': round(progress, 2),
        'status': status,
        'metrics': {
            'budget_name': budget.name,
            'budget_amount': float(budget_amount),
            'actual_spending': float(actual_spending),
            'remaining': float(budget_amount - actual_spending),
            'usage_percentage': float(usage_pct),
            'over_budget': usage_pct > 100,
            'period': budget.period,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
        },
    }


def evaluate_revenue_target_goal(goal, as_of_date: date) -> Dict:
    """
    Evaluate revenue target goal.
    Tracks inflows toward a revenue target.

    Goal parameters:
    - target_value: Revenue target
    - parameters.period: 'monthly', 'quarterly', 'yearly'
    - parameters.label_ids: Optional labels to track
    """
    organization = goal.organization
    params = goal.parameters or {}

    # Get period
    period = params.get('period', 'monthly')
    start_date = _get_period_start(as_of_date, period)

    # Get inflow transactions
    txs = Transaction.objects.filter(
        organization=organization,
        date__gte=start_date,
        date__lte=as_of_date,
        direction='inflow'
    )

    # Filter by labels if specified
    label_ids = params.get('label_ids', [])
    if label_ids:
        txs = txs.filter(label_id__in=label_ids)

    # Calculate revenue
    df = queryset_to_df(txs)
    metrics = kpis(df)

    current_revenue = Decimal(str(metrics['inflow']))
    target_revenue = goal.target_value or Decimal('10000')

    # Calculate progress
    if target_revenue > 0:
        progress = (current_revenue / target_revenue) * Decimal('100')
    else:
        progress = Decimal('0')

    progress = min(progress, Decimal('100'))

    # Determine status
    status = _determine_status(progress, goal.target_date, as_of_date)

    return {
        'current_value': current_revenue,
        'target_value': target_revenue,
        'progress_percentage': round(progress, 2),
        'status': status,
        'metrics': {
            'revenue': float(current_revenue),
            'target': float(target_revenue),
            'remaining': float(target_revenue - current_revenue),
            'period': period,
            'start_date': start_date.isoformat(),
            'tx_count': metrics['tx_count'],
        },
    }


def evaluate_profit_margin_goal(goal, as_of_date: date) -> Dict:
    """
    Evaluate profit margin goal.
    Calculates profit margin as (Revenue - Costs) / Revenue * 100.

    Goal parameters:
    - target_value: Target profit margin percentage
    - parameters.period: 'monthly', 'quarterly', 'yearly'
    """
    organization = goal.organization
    params = goal.parameters or {}

    # Get period
    period = params.get('period', 'monthly')
    start_date = _get_period_start(as_of_date, period)

    # Get all transactions
    txs = Transaction.objects.filter(
        organization=organization,
        date__gte=start_date,
        date__lte=as_of_date
    )

    # Calculate metrics
    df = queryset_to_df(txs)
    metrics = kpis(df)

    revenue = Decimal(str(metrics['inflow']))
    costs = Decimal(str(metrics['outflow']))
    profit = revenue - costs

    # Calculate profit margin
    if revenue > 0:
        current_margin = (profit / revenue) * Decimal('100')
    else:
        current_margin = Decimal('0')

    target_margin = goal.target_value or Decimal('20')  # Default 20% margin

    # Calculate progress
    if target_margin > 0:
        progress = (current_margin / target_margin) * Decimal('100')
    else:
        progress = Decimal('0')

    progress = max(Decimal('0'), min(progress, Decimal('100')))

    # Determine status
    status = _determine_status(progress, goal.target_date, as_of_date)

    return {
        'current_value': current_margin,
        'target_value': target_margin,
        'progress_percentage': round(progress, 2),
        'status': status,
        'metrics': {
            'revenue': float(revenue),
            'costs': float(costs),
            'profit': float(profit),
            'margin_percentage': float(current_margin),
            'target_margin': float(target_margin),
            'period': period,
            'start_date': start_date.isoformat(),
        },
    }


# ========== HELPER FUNCTIONS ==========

def calculate_runway(organization: Organization, as_of_date: Optional[date] = None) -> Dict:
    """
    Calculate months of runway based on current burn rate.

    Args:
        organization: Organization to calculate for
        as_of_date: Date to calculate as of

    Returns:
        dict with runway_months, current_balance, monthly_burn, etc.
    """
    if as_of_date is None:
        as_of_date = timezone.now().date()

    # Get last 90 days of transactions to calculate burn rate
    lookback_start = as_of_date - timedelta(days=90)

    txs = Transaction.objects.filter(
        organization=organization,
        date__gte=lookback_start,
        date__lte=as_of_date
    )

    df = queryset_to_df(txs)
    metrics = kpis(df)

    # Calculate monthly burn rate (average outflow per month)
    days_in_period = (as_of_date - lookback_start).days
    daily_burn = Decimal('0')
    if days_in_period > 0:
        daily_burn = Decimal(str(metrics['outflow'])) / Decimal(str(days_in_period))
        monthly_burn = daily_burn * Decimal('30')
    else:
        monthly_burn = Decimal('0')

    # Get current balance (all-time net)
    all_txs = Transaction.objects.filter(
        organization=organization,
        date__lte=as_of_date
    )
    all_df = queryset_to_df(all_txs)
    all_metrics = kpis(all_df)
    current_balance = Decimal(str(all_metrics['net']))

    # Calculate runway months
    if monthly_burn > 0:
        runway_months = current_balance / monthly_burn
    else:
        runway_months = Decimal('999')  # Infinite runway if no burn

    # Cap at reasonable max
    runway_months = max(Decimal('0'), min(runway_months, Decimal('999')))

    return {
        'runway_months': round(runway_months, 1),
        'current_balance': float(current_balance),
        'monthly_burn': float(monthly_burn),
        'daily_burn': float(daily_burn) if days_in_period > 0 else 0,
        'lookback_days': days_in_period,
        'total_inflow_90d': metrics['inflow'],
        'total_outflow_90d': metrics['outflow'],
    }


def _get_period_start(as_of_date: date, period: str) -> date:
    """Get start date for a given period type"""
    if period == 'daily':
        return as_of_date
    elif period == 'weekly':
        # Start of week (Monday)
        return as_of_date - timedelta(days=as_of_date.weekday())
    elif period == 'monthly':
        # Start of month
        return as_of_date.replace(day=1)
    elif period == 'quarterly':
        # Start of quarter
        quarter_month = ((as_of_date.month - 1) // 3) * 3 + 1
        return as_of_date.replace(month=quarter_month, day=1)
    elif period == 'yearly':
        # Start of year
        return as_of_date.replace(month=1, day=1)
    else:
        # Default to start of month
        return as_of_date.replace(day=1)


def _determine_status(progress: Decimal, target_date: Optional[date], as_of_date: date) -> str:
    """
    Determine goal status based on progress and timeline.

    Args:
        progress: Progress percentage (0-100)
        target_date: Target completion date (optional)
        as_of_date: Current evaluation date

    Returns:
        Status string: 'on_track', 'at_risk', 'off_track', 'achieved', 'not_started'
    """
    if progress >= 100:
        return 'achieved'

    if progress == 0:
        return 'not_started'

    # If no target date, base status only on progress
    if not target_date:
        if progress >= 75:
            return 'on_track'
        elif progress >= 50:
            return 'at_risk'
        else:
            return 'off_track'

    # Calculate if we're on track based on time elapsed
    # This is a simple linear projection
    days_until_target = (target_date - as_of_date).days

    if days_until_target < 0:
        # Past target date
        return 'off_track' if progress < 100 else 'achieved'

    # Expected progress based on time (if goal was created recently, adjust)
    # For now, use simple thresholds
    if progress >= 75:
        return 'on_track'
    elif progress >= 50:
        return 'at_risk'
    else:
        return 'off_track'

