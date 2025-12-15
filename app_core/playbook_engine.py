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
    Calculates months of runway based on current burn rate with enhanced intelligence.

    Goal parameters:
    - target_value: Number of months of runway desired
    - target_date: Date by which to achieve
    """
    organization = goal.organization

    # Calculate enhanced runway with scenarios and breakdown
    runway_enhanced = calculate_runway_enhanced(organization, as_of_date)
    runway_data = runway_enhanced['current']

    # Convert to Decimal for calculation (runway_months is float from calculate_runway)
    current_months = Decimal(str(runway_data['runway_months']))
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
        'metrics': runway_enhanced,  # Include all enhanced data
    }


def evaluate_savings_goal(goal, as_of_date: date) -> Dict:
    """
    Evaluate savings target goal.
    Tracks progress toward a specific savings amount.

    Goal parameters:
    - target_value: Amount to save
    - start_date: When to start tracking (model field or parameters)
    - parameters.label_ids: Optional labels to track for savings
    """
    organization = goal.organization
    params = goal.parameters or {}

    # Get start date - prioritize model field, then parameters, then created_at
    if goal.start_date:
        start_date = goal.start_date
    elif params.get('start_date'):
        param_start = params.get('start_date')
        start_date = datetime.strptime(param_start, '%Y-%m-%d').date() if isinstance(param_start, str) else param_start
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

    # Clamp progress to 0-100% for display
    progress_clamped = max(Decimal('0'), min(progress, Decimal('100')))

    # Determine status - don't mark as achieved until target date is reached
    if goal.target_date and as_of_date < goal.target_date:
        # Goal hasn't reached target date yet - can't be achieved even if at 100%+
        if progress_clamped >= 90:
            status = 'on_track'
        elif progress_clamped >= 75:
            status = 'on_track'
        elif progress_clamped >= 50:
            status = 'at_risk'
        else:
            status = 'off_track'
    elif goal.target_date and as_of_date >= goal.target_date:
        # Past target date - check if goal was achieved
        if progress >= 100:
            status = 'achieved'
        else:
            status = 'off_track'
    else:
        # No target date - use standard status determination
        status = _determine_status(progress_clamped, goal.target_date, as_of_date)

    return {
        'current_value': current_savings,
        'target_value': target_savings,
        'progress_percentage': round(progress_clamped, 2),
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
    - start_date: When goal tracking begins
    - parameters.period: 'daily', 'weekly', 'monthly', 'yearly'
    - parameters.label_ids: Labels to track
    - parameters.category: Optional category filter
    """
    organization = goal.organization
    params = goal.parameters or {}

    # Check if goal has started yet
    if goal.start_date and as_of_date < goal.start_date:
        # Goal hasn't started yet
        return {
            'current_value': Decimal('0'),
            'target_value': goal.target_value or Decimal('5000'),
            'progress_percentage': Decimal('0'),
            'status': 'not_started',
            'metrics': {
                'spending': 0,
                'limit': float(goal.target_value or Decimal('5000')),
                'usage_percentage': 0,
                'over_limit': False,
                'period': params.get('period', 'monthly'),
                'start_date': goal.start_date.isoformat() if goal.start_date else None,
                'tx_count': 0,
            },
        }

    # Get period
    period = params.get('period', 'monthly')
    period_start = _get_period_start(as_of_date, period)

    # Respect goal.start_date - don't track transactions before it
    if goal.start_date and period_start < goal.start_date:
        period_start = goal.start_date

    # Get transactions in period
    txs = Transaction.objects.filter(
        organization=organization,
        date__gte=period_start,
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
        # Still in progress - can't be achieved yet even if currently under budget
        if current_spending > target_limit:
            status = 'off_track'  # Already over limit
        elif usage_pct >= 90:
            status = 'at_risk'  # Close to limit
        elif usage_pct >= 75:
            status = 'on_track'  # Reasonable usage
        else:
            status = 'on_track'  # Well under limit
    elif goal.target_date and as_of_date >= goal.target_date:
        # Past target date - check if we stayed within limit for the full period
        if current_spending <= target_limit:
            status = 'achieved'  # Successfully stayed within limit for the full period
        else:
            status = 'off_track'  # Went over limit
    else:
        # No target date - treat as ongoing monitoring
        if current_spending <= target_limit:
            status = 'on_track'
        else:
            status = 'off_track'

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
            'start_date': period_start.isoformat(),
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
    - start_date: When goal tracking begins
    - parameters.period: 'monthly', 'quarterly', 'yearly'
    - parameters.label_ids: Optional labels to track
    """
    organization = goal.organization
    params = goal.parameters or {}

    # Check if goal has started yet
    if goal.start_date and as_of_date < goal.start_date:
        # Goal hasn't started yet
        return {
            'current_value': Decimal('0'),
            'target_value': goal.target_value or Decimal('10000'),
            'progress_percentage': Decimal('0'),
            'status': 'not_started',
            'metrics': {
                'revenue': 0,
                'target': float(goal.target_value or Decimal('10000')),
                'period': params.get('period', 'monthly'),
                'start_date': goal.start_date.isoformat() if goal.start_date else None,
                'tx_count': 0,
            },
        }

    # Get period
    period = params.get('period', 'monthly')
    period_start = _get_period_start(as_of_date, period)

    # Respect goal.start_date - don't track transactions before it
    if goal.start_date and period_start < goal.start_date:
        period_start = goal.start_date

    # Get inflow transactions
    txs = Transaction.objects.filter(
        organization=organization,
        date__gte=period_start,
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
            'start_date': period_start.isoformat(),
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
        'runway_months': float(round(runway_months, 1)),
        'current_balance': float(current_balance),
        'monthly_burn': float(monthly_burn),
        'daily_burn': float(daily_burn) if days_in_period > 0 else 0,
        'lookback_days': days_in_period,
        'total_inflow_90d': float(metrics['inflow']),
        'total_outflow_90d': float(metrics['outflow']),
    }


def calculate_runway_enhanced(organization: Organization, as_of_date: Optional[date] = None) -> Dict:
    """
    Enhanced runway calculation with multi-scenario analysis, burn breakdown, and critical dates.

    Args:
        organization: Organization to calculate for
        as_of_date: Date to calculate as of

    Returns:
        dict with:
            - current: baseline runway data
            - scenarios: best/expected/worst case projections
            - burn_breakdown: spending by category
            - critical_dates: key dates and milestones
            - savings_opportunities: potential runway improvements
    """
    if as_of_date is None:
        as_of_date = timezone.now().date()

    # Get baseline runway
    baseline = calculate_runway(organization, as_of_date)

    # Calculate scenario projections
    scenarios = _calculate_runway_scenarios(organization, baseline, as_of_date)

    # Get burn rate breakdown by category
    burn_breakdown = _calculate_burn_breakdown(organization, as_of_date)

    # Calculate critical dates
    critical_dates = _calculate_critical_dates(
        as_of_date,
        baseline['runway_months'],
        baseline['monthly_burn'],
        organization
    )

    # Identify savings opportunities
    savings_opportunities = _calculate_savings_opportunities(burn_breakdown, baseline['runway_months'])

    return {
        'current': baseline,
        'scenarios': scenarios,
        'burn_breakdown': burn_breakdown,
        'critical_dates': critical_dates,
        'savings_opportunities': savings_opportunities,
    }


def _calculate_runway_scenarios(organization: Organization, baseline: Dict, as_of_date: date) -> Dict:
    """Calculate best/expected/worst case runway scenarios"""
    from django.db.models import Sum

    lookback_start = as_of_date - timedelta(days=90)

    # Get average monthly revenue and expenses
    monthly_revenue = Decimal(str(baseline.get('total_inflow_90d', 0))) / Decimal('3')  # 3 months
    monthly_expenses = Decimal(str(baseline.get('monthly_burn', 0)))
    current_balance = Decimal(str(baseline.get('current_balance', 0)))

    # Best case: 20% revenue increase
    best_revenue = monthly_revenue * Decimal('1.20')
    best_net = best_revenue - monthly_expenses
    if best_net > 0:
        best_runway = Decimal('999')  # Positive cash flow
    elif monthly_expenses > 0:
        best_runway = current_balance / monthly_expenses
    else:
        best_runway = Decimal('999')

    # Expected case: current trajectory
    expected_runway = Decimal(str(baseline.get('runway_months', 0)))

    # Worst case: 10% revenue decline
    worst_revenue = monthly_revenue * Decimal('0.90')
    worst_net = worst_revenue - monthly_expenses
    worst_burn = abs(worst_net) if worst_net < 0 else monthly_expenses
    if worst_burn > 0:
        worst_runway = current_balance / worst_burn
    else:
        worst_runway = Decimal('999')

    # Cap scenarios
    best_runway = max(Decimal('0'), min(best_runway, Decimal('999')))
    worst_runway = max(Decimal('0'), min(worst_runway, Decimal('999')))

    return {
        'best_case': {
            'runway_months': float(round(best_runway, 1)),
            'description': '+20% revenue growth',
            'change_pct': float(((best_runway - expected_runway) / expected_runway * 100) if expected_runway > 0 else 0),
        },
        'expected': {
            'runway_months': float(round(expected_runway, 1)),
            'description': 'Current trajectory',
            'change_pct': 0,
        },
        'worst_case': {
            'runway_months': float(round(worst_runway, 1)),
            'description': '-10% revenue decline',
            'change_pct': float(((worst_runway - expected_runway) / expected_runway * 100) if expected_runway > 0 else 0),
        },
    }


def _calculate_burn_breakdown(organization: Organization, as_of_date: date) -> List[Dict]:
    """Calculate burn rate breakdown by category"""
    from django.db.models import Sum

    lookback_start = as_of_date - timedelta(days=90)

    # Get outflow transactions grouped by category
    category_spending = Transaction.objects.filter(
        organization=organization,
        date__gte=lookback_start,
        date__lte=as_of_date,
        direction='outflow'
    ).values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')

    total_spend = sum(item['total'] for item in category_spending) if category_spending else Decimal('0')

    # Calculate monthly average and percentage for each category
    breakdown = []
    for item in category_spending[:10]:  # Top 10 categories
        monthly_avg = item['total'] / Decimal('3')  # 3 months
        percentage = (item['total'] / total_spend * 100) if total_spend > 0 else 0

        breakdown.append({
            'category': item['category'] or 'Uncategorized',
            'monthly_amount': float(monthly_avg),
            'total_90d': float(item['total']),
            'percentage': float(round(percentage, 1)),
        })

    return breakdown


def _calculate_critical_dates(as_of_date: date, runway_months: float, monthly_burn: float, organization: Organization) -> Dict:
    """Calculate critical dates and milestones"""
    from django.db.models import Sum

    # Calculate runway end date
    if runway_months > 0 and runway_months < 999:
        days_remaining = int(runway_months * 30)
        runway_end_date = as_of_date + timedelta(days=days_remaining)
    else:
        runway_end_date = None

    # Calculate when runway hits critical thresholds
    threshold_3_months = None
    threshold_6_months = None

    if runway_months > 3:
        months_until_3 = runway_months - 3
        days_until_3 = int(months_until_3 * 30)
        threshold_3_months = as_of_date + timedelta(days=days_until_3)

    if runway_months > 6:
        months_until_6 = runway_months - 6
        days_until_6 = int(months_until_6 * 30)
        threshold_6_months = as_of_date + timedelta(days=days_until_6)

    # Find upcoming large expenses (next 90 days)
    future_end = as_of_date + timedelta(days=90)
    upcoming = Transaction.objects.filter(
        organization=organization,
        date__gt=as_of_date,
        date__lte=future_end,
        direction='outflow'
    ).order_by('date')[:5]

    upcoming_events = []
    for tx in upcoming:
        upcoming_events.append({
            'date': tx.date.isoformat(),
            'description': tx.description or tx.category,
            'amount': float(tx.amount),
            'days_away': (tx.date - as_of_date).days,
        })

    return {
        'runway_end_date': runway_end_date.isoformat() if runway_end_date else None,
        'days_until_end': (runway_end_date - as_of_date).days if runway_end_date else None,
        'threshold_3_months': threshold_3_months.isoformat() if threshold_3_months else None,
        'threshold_6_months': threshold_6_months.isoformat() if threshold_6_months else None,
        'upcoming_expenses': upcoming_events,
    }


def _calculate_savings_opportunities(burn_breakdown: List[Dict], current_runway: float) -> List[Dict]:
    """Identify potential savings and runway impact"""
    opportunities = []

    for category in burn_breakdown[:5]:  # Top 5 categories
        monthly_amount = Decimal(str(category['monthly_amount']))

        # Calculate impact of 10%, 15%, and 20% cuts
        for cut_pct in [10, 15, 20]:
            savings = monthly_amount * (Decimal(str(cut_pct)) / Decimal('100'))

            # Calculate total current monthly burn (sum of all categories)
            total_burn = sum(Decimal(str(c['monthly_amount'])) for c in burn_breakdown)

            if total_burn > 0:
                # Calculate new runway with reduced burn
                new_burn = total_burn - savings
                if new_burn > 0:
                    # Approximate current balance from runway
                    current_balance = total_burn * Decimal(str(current_runway))
                    new_runway = current_balance / new_burn
                    runway_gain = float(new_runway - Decimal(str(current_runway)))
                else:
                    runway_gain = 999  # Positive cash flow

                opportunities.append({
                    'category': category['category'],
                    'action': f"Cut {category['category']} by {cut_pct}%",
                    'monthly_savings': float(savings),
                    'runway_gain_months': round(runway_gain, 1),
                    'cut_percentage': cut_pct,
                })

    # Sort by runway gain
    opportunities.sort(key=lambda x: x['runway_gain_months'], reverse=True)

    return opportunities[:5]  # Top 5 opportunities


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

