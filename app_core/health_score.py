# app_core/health_score.py
"""
Financial Health Score Calculator
Calculates overall business health (0-100) from multiple components
"""

from decimal import Decimal
from datetime import date, timedelta
from typing import Dict
from django.utils import timezone

from .models import Organization, FinancialGoal
from .playbook_engine import calculate_runway
from .metrics import kpis, queryset_to_df
from .models import Transaction


def calculate_health_score(organization: Organization, as_of_date: date = None) -> Dict:
    """
    Calculate overall financial health score (0-100)

    Components:
    - Runway: 30%
    - Revenue Growth: 25%
    - Expense Control: 20%
    - Goal Progress: 15%
    - Financial Stability: 10%

    Args:
        organization: Organization to calculate for
        as_of_date: Date to calculate as of (defaults to today)

    Returns:
        dict with total_score, components, level, badge, explanation
    """
    if as_of_date is None:
        as_of_date = timezone.now().date()

    # Calculate each component score
    runway_score = _calculate_runway_score(organization, as_of_date)
    revenue_score = _calculate_revenue_growth_score(organization, as_of_date)
    expense_score = _calculate_expense_control_score(organization, as_of_date)
    goal_score = _calculate_goal_progress_score(organization, as_of_date)
    stability_score = _calculate_stability_score(organization, as_of_date)

    # Calculate weighted total
    total_score = (
        runway_score * 0.30 +
        revenue_score * 0.25 +
        expense_score * 0.20 +
        goal_score * 0.15 +
        stability_score * 0.10
    )

    # Determine level and badge
    if total_score >= 90:
        level = 'excellent'
        badge = '🥇'
        level_text = 'Excellent'
    elif total_score >= 80:
        level = 'great'
        badge = '🥈'
        level_text = 'Great'
    elif total_score >= 70:
        level = 'good'
        badge = '🥉'
        level_text = 'Good'
    elif total_score >= 60:
        level = 'fair'
        badge = '⚠️'
        level_text = 'Fair'
    else:
        level = 'needs_improvement'
        badge = '🔴'
        level_text = 'Needs Improvement'

    # Generate explanation
    explanation = _generate_score_explanation(
        total_score,
        {
            'runway': runway_score,
            'revenue': revenue_score,
            'expense': expense_score,
            'goal': goal_score,
            'stability': stability_score,
        }
    )

    return {
        'total_score': round(total_score, 1),
        'level': level,
        'level_text': level_text,
        'badge': badge,
        'components': {
            'runway': {
                'score': round(runway_score, 1),
                'weight': 30,
                'status': _get_component_status(runway_score),
            },
            'revenue_growth': {
                'score': round(revenue_score, 1),
                'weight': 25,
                'status': _get_component_status(revenue_score),
            },
            'expense_control': {
                'score': round(expense_score, 1),
                'weight': 20,
                'status': _get_component_status(expense_score),
            },
            'goal_progress': {
                'score': round(goal_score, 1),
                'weight': 15,
                'status': _get_component_status(goal_score),
            },
            'stability': {
                'score': round(stability_score, 1),
                'weight': 10,
                'status': _get_component_status(stability_score),
            },
        },
        'explanation': explanation,
        'calculated_at': as_of_date.isoformat(),
    }


def _calculate_runway_score(organization: Organization, as_of_date: date) -> float:
    """
    Calculate runway component score (0-100)
    6+ months = 100, 0 months = 0, linear between
    """
    runway_data = calculate_runway(organization, as_of_date)
    runway_months = runway_data['runway_months']

    # Cap at 6 months for scoring (6+ months = perfect score)
    if runway_months >= 6:
        return 100.0
    elif runway_months <= 0:
        return 0.0
    else:
        return (runway_months / 6.0) * 100.0


def _calculate_revenue_growth_score(organization: Organization, as_of_date: date) -> float:
    """
    Calculate revenue growth component score (0-100)
    0% growth = 50, 25%+ growth = 100, negative = lower
    """
    # Compare last 30 days vs previous 30 days
    period_end = as_of_date
    period_start = period_end - timedelta(days=30)
    prev_end = period_start
    prev_start = prev_end - timedelta(days=30)

    # Current period revenue
    current_txs = Transaction.objects.filter(
        organization=organization,
        date__gte=period_start,
        date__lte=period_end,
        direction='inflow'
    )
    current_df = queryset_to_df(current_txs)
    current_revenue = Decimal(str(kpis(current_df)['inflow']))

    # Previous period revenue
    prev_txs = Transaction.objects.filter(
        organization=organization,
        date__gte=prev_start,
        date__lte=prev_end,
        direction='inflow'
    )
    prev_df = queryset_to_df(prev_txs)
    prev_revenue = Decimal(str(kpis(prev_df)['inflow']))

    # Calculate growth rate
    if prev_revenue > 0:
        growth_rate = ((current_revenue - prev_revenue) / prev_revenue) * 100
        growth_rate = float(growth_rate)
    else:
        growth_rate = 0.0 if current_revenue == 0 else 100.0

    # Score: 0% = 50 pts, 25%+ = 100 pts, -25%- = 0 pts
    if growth_rate >= 25:
        return 100.0
    elif growth_rate <= -25:
        return 0.0
    else:
        # Linear scale: -25% to +25% maps to 0 to 100
        return 50.0 + (growth_rate * 2.0)


def _calculate_expense_control_score(organization: Organization, as_of_date: date) -> float:
    """
    Calculate expense control component score (0-100)
    Based on burn rate efficiency and trend
    """
    # Compare last 30 days vs previous 30 days
    period_end = as_of_date
    period_start = period_end - timedelta(days=30)
    prev_end = period_start
    prev_start = prev_end - timedelta(days=30)

    # Current period expenses
    current_txs = Transaction.objects.filter(
        organization=organization,
        date__gte=period_start,
        date__lte=period_end,
        direction='outflow'
    )
    current_df = queryset_to_df(current_txs)
    current_metrics = kpis(current_df)
    current_expenses = Decimal(str(current_metrics['outflow']))
    current_revenue = Decimal(str(current_metrics['inflow']))

    # Previous period expenses
    prev_txs = Transaction.objects.filter(
        organization=organization,
        date__gte=prev_start,
        date__lte=prev_end,
        direction='outflow'
    )
    prev_df = queryset_to_df(prev_txs)
    prev_metrics = kpis(prev_df)
    prev_expenses = Decimal(str(prev_metrics['outflow']))

    # Calculate expense growth rate
    if prev_expenses > 0:
        expense_growth = ((current_expenses - prev_expenses) / prev_expenses) * 100
        expense_growth = float(expense_growth)
    else:
        expense_growth = 0.0

    # Score based on expense control (lower growth = better)
    # -10%+ reduction = 100 pts, +10%+ increase = 0 pts
    if expense_growth <= -10:
        return 100.0
    elif expense_growth >= 10:
        return 40.0  # Still some points for having expenses under control
    else:
        # Linear scale: -10% to +10% maps to 100 to 40
        return 100.0 - ((expense_growth + 10) * 3.0)


def _calculate_goal_progress_score(organization: Organization, as_of_date: date) -> float:
    """
    Calculate goal progress component score (0-100)
    Based on % of goals on track or achieved
    """
    goals = FinancialGoal.objects.filter(
        organization=organization,
        active=True
    )

    if not goals.exists():
        return 50.0  # Neutral score if no goals set

    total_goals = goals.count()
    on_track = goals.filter(current_status__in=['on_track', 'achieved']).count()

    # Calculate percentage of goals on track
    if total_goals > 0:
        percentage = (on_track / total_goals) * 100
        return percentage
    else:
        return 50.0


def _calculate_stability_score(organization: Organization, as_of_date: date) -> float:
    """
    Calculate financial stability component score (0-100)
    Based on consistency and volatility
    """
    # Look at last 90 days
    lookback_start = as_of_date - timedelta(days=90)

    txs = Transaction.objects.filter(
        organization=organization,
        date__gte=lookback_start,
        date__lte=as_of_date
    )

    if not txs.exists():
        return 50.0  # Neutral if no data

    # Calculate weekly cash flows
    weeks = []
    for i in range(12):  # 12 weeks ~= 90 days
        week_end = as_of_date - timedelta(days=i*7)
        week_start = week_end - timedelta(days=7)

        week_txs = txs.filter(date__gte=week_start, date__lte=week_end)
        if week_txs.exists():
            week_df = queryset_to_df(week_txs)
            week_metrics = kpis(week_df)
            weeks.append(week_metrics['net'])

    if len(weeks) < 4:
        return 50.0  # Not enough data

    # Calculate coefficient of variation (std dev / mean)
    import statistics
    mean_flow = statistics.mean(weeks)
    if mean_flow == 0:
        return 50.0

    std_dev = statistics.stdev(weeks) if len(weeks) > 1 else 0
    cv = abs(std_dev / mean_flow) if mean_flow != 0 else 0

    # Score based on volatility (lower CV = more stable = higher score)
    # CV < 0.2 = 100 pts, CV > 1.0 = 0 pts
    if cv <= 0.2:
        return 100.0
    elif cv >= 1.0:
        return 30.0
    else:
        # Linear scale
        return 100.0 - ((cv - 0.2) * 87.5)


def _get_component_status(score: float) -> str:
    """Get status indicator for component score"""
    if score >= 80:
        return 'excellent'
    elif score >= 60:
        return 'good'
    elif score >= 40:
        return 'fair'
    else:
        return 'poor'


def _generate_score_explanation(total_score: float, components: Dict) -> str:
    """Generate human-readable explanation of score"""
    # Find weakest component
    weakest = min(components.items(), key=lambda x: x[1])
    strongest = max(components.items(), key=lambda x: x[1])

    weak_name = weakest[0].replace('_', ' ').title()
    strong_name = strongest[0].replace('_', ' ').title()

    if total_score >= 90:
        return f"Excellent financial health! Your {strong_name} is particularly strong. Keep up the great work."
    elif total_score >= 80:
        return f"Great financial position! Your {strong_name} is strong. Focus on improving {weak_name} to reach excellent status."
    elif total_score >= 70:
        return f"Good financial health overall. Your {weak_name} needs attention to improve your score."
    elif total_score >= 60:
        return f"Fair financial position. Focus on improving {weak_name} and {strong_name} could be better."
    else:
        return f"Your {weak_name} needs immediate attention. Consider reviewing your financial strategy and making adjustments."


def get_score_trend(organization: Organization, days: int = 30) -> Dict:
    """
    Get health score trend over time

    Args:
        organization: Organization to calculate for
        days: Number of days to look back

    Returns:
        dict with dates and scores
    """
    today = timezone.now().date()
    dates = []
    scores = []

    # Calculate score for today and previous weeks
    for i in range(0, days, 7):  # Weekly intervals
        calc_date = today - timedelta(days=i)
        score_data = calculate_health_score(organization, calc_date)

        dates.insert(0, calc_date.isoformat())
        scores.insert(0, score_data['total_score'])

    # Calculate trend
    if len(scores) >= 2:
        change = scores[-1] - scores[0]
        if change > 0:
            trend = 'improving'
        elif change < 0:
            trend = 'declining'
        else:
            trend = 'stable'
    else:
        trend = 'stable'

    return {
        'dates': dates,
        'scores': scores,
        'trend': trend,
        'change': round(scores[-1] - scores[0], 1) if len(scores) >= 2 else 0,
    }

