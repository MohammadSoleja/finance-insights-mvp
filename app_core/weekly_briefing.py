# app_core/weekly_briefing.py
"""
Weekly Financial Briefing Generator
Creates personalized weekly summaries with key metrics, insights, and action items
"""

from decimal import Decimal
from datetime import date, timedelta
from typing import Dict, List
from django.utils import timezone

from .models import Organization, FinancialGoal, Transaction
from .playbook_engine import calculate_runway_enhanced
from .health_score import calculate_health_score, get_score_trend
from .metrics import kpis, queryset_to_df


def generate_weekly_briefing(organization: Organization, as_of_date: date = None) -> Dict:
    """
    Generate comprehensive weekly financial briefing

    Returns:
        dict with:
            - key_metrics: Current metrics with week-over-week changes
            - health_score: Current score and change
            - concerns: List of items needing attention
            - good_news: Positive highlights
            - action_items: Top 3 recommended actions
            - upcoming_dates: Critical dates in next 30 days
    """
    if as_of_date is None:
        as_of_date = timezone.now().date()

    # Calculate key metrics
    key_metrics = _calculate_weekly_metrics(organization, as_of_date)

    # Get health score
    health_data = calculate_health_score(organization, as_of_date)
    score_trend = get_score_trend(organization, days=14)  # Last 2 weeks

    # Generate insights
    concerns = _identify_concerns(organization, as_of_date, key_metrics, health_data)
    good_news = _identify_good_news(organization, as_of_date, key_metrics, health_data)

    # Generate action items
    action_items = _generate_action_items(organization, concerns, key_metrics)

    # Get upcoming critical dates
    upcoming_dates = _get_upcoming_dates(organization, as_of_date)

    return {
        'organization': organization.name,
        'week_of': as_of_date.isoformat(),
        'key_metrics': key_metrics,
        'health_score': {
            'current': health_data['total_score'],
            'change': score_trend['change'],
            'trend': score_trend['trend'],
            'level': health_data['level_text'],
            'badge': health_data['badge'],
        },
        'concerns': concerns,
        'good_news': good_news,
        'action_items': action_items,
        'upcoming_dates': upcoming_dates,
        'generated_at': timezone.now().isoformat(),
    }


def _calculate_weekly_metrics(organization: Organization, as_of_date: date) -> Dict:
    """Calculate key metrics with week-over-week comparison"""

    # Current week
    week_end = as_of_date
    week_start = week_end - timedelta(days=7)

    # Previous week
    prev_week_end = week_start
    prev_week_start = prev_week_end - timedelta(days=7)

    # Current week data
    current_txs = Transaction.objects.filter(
        organization=organization,
        date__gte=week_start,
        date__lte=week_end
    )
    current_df = queryset_to_df(current_txs)
    current_metrics = kpis(current_df)

    # Previous week data
    prev_txs = Transaction.objects.filter(
        organization=organization,
        date__gte=prev_week_start,
        date__lte=prev_week_end
    )
    prev_df = queryset_to_df(prev_txs)
    prev_metrics = kpis(prev_df)

    # Calculate runway
    runway_enhanced = calculate_runway_enhanced(organization, as_of_date)
    runway_current = runway_enhanced['current']['runway_months']

    # Previous week runway (approximate)
    runway_prev_data = calculate_runway_enhanced(organization, prev_week_end)
    runway_prev = runway_prev_data['current']['runway_months']

    runway_change = runway_current - runway_prev

    # Calculate changes
    revenue_change = _calculate_change(current_metrics['inflow'], prev_metrics['inflow'])
    expense_change = _calculate_change(current_metrics['outflow'], prev_metrics['outflow'])
    net_change = _calculate_change(current_metrics['net'], prev_metrics['net'])

    return {
        'runway': {
            'current': round(runway_current, 1),
            'change': round(runway_change, 1),
            'change_label': f"↓ {abs(runway_change):.1f}" if runway_change < 0 else f"↑ {abs(runway_change):.1f}",
        },
        'revenue': {
            'current': float(current_metrics['inflow']),
            'change_pct': revenue_change,
            'change_label': f"↓ {abs(revenue_change):.1f}%" if revenue_change < 0 else f"↑ {abs(revenue_change):.1f}%",
        },
        'expenses': {
            'current': float(current_metrics['outflow']),
            'change_pct': expense_change,
            'change_label': f"↓ {abs(expense_change):.1f}%" if expense_change < 0 else f"↑ {abs(expense_change):.1f}%",
        },
        'net_cash_flow': {
            'current': float(current_metrics['net']),
            'change_pct': net_change,
            'change_label': f"↓ {abs(net_change):.1f}%" if net_change < 0 else f"↑ {abs(net_change):.1f}%",
        },
        'burn_rate': {
            'current': float(runway_enhanced['current']['monthly_burn']),
        },
    }


def _calculate_change(current: float, previous: float) -> float:
    """Calculate percentage change"""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return ((current - previous) / previous) * 100


def _identify_concerns(organization: Organization, as_of_date: date, metrics: Dict, health: Dict) -> List[str]:
    """Identify items that need attention"""
    concerns = []

    # Runway concerns
    runway = metrics['runway']['current']
    runway_change = metrics['runway']['change']

    if runway < 3:
        concerns.append(f"🔴 Critical: Runway at {runway} months - immediate action needed")
    elif runway < 6:
        concerns.append(f"⚠️ Runway below target at {runway} months")

    if runway_change < -0.5:
        concerns.append(f"⚠️ Runway declining rapidly ({runway_change:.1f} months this week)")

    # Expense concerns
    if metrics['expenses']['change_pct'] > 20:
        concerns.append(f"⚠️ Expenses up {metrics['expenses']['change_pct']:.0f}% this week - review spending")

    # Health score concerns
    if health['total_score'] < 60:
        concerns.append(f"⚠️ Health score at {health['total_score']}/100 - needs improvement")

    # Goal concerns
    at_risk_goals = FinancialGoal.objects.filter(
        organization=organization,
        active=True,
        current_status__in=['at_risk', 'off_track']
    ).count()

    if at_risk_goals > 0:
        concerns.append(f"⚠️ {at_risk_goals} goal{'s' if at_risk_goals > 1 else ''} at risk or off track")

    return concerns[:5]  # Top 5 concerns


def _identify_good_news(organization: Organization, as_of_date: date, metrics: Dict, health: Dict) -> List[str]:
    """Identify positive highlights"""
    good_news = []

    # Revenue growth
    if metrics['revenue']['change_pct'] > 10:
        good_news.append(f"📈 Revenue up {metrics['revenue']['change_pct']:.0f}% this week")

    # Expense reduction
    if metrics['expenses']['change_pct'] < -10:
        good_news.append(f"💰 Expenses down {abs(metrics['expenses']['change_pct']):.0f}%")

    # Runway improvement
    if metrics['runway']['change'] > 0.5:
        good_news.append(f"🛡️ Runway improved by {metrics['runway']['change']:.1f} months")

    # Health score improvement
    if health['total_score'] > 80:
        good_news.append(f"🥈 Strong health score: {health['total_score']}/100")

    # Goals achieved
    achieved_goals = FinancialGoal.objects.filter(
        organization=organization,
        active=True,
        current_status='achieved'
    ).count()

    if achieved_goals > 0:
        good_news.append(f"🎯 {achieved_goals} goal{'s' if achieved_goals > 1 else ''} achieved")

    # On track goals
    on_track = FinancialGoal.objects.filter(
        organization=organization,
        active=True,
        current_status='on_track'
    ).count()

    if on_track >= 3:
        good_news.append(f"✅ {on_track} goals on track")

    return good_news[:5]  # Top 5 positive items


def _generate_action_items(organization: Organization, concerns: List[str], metrics: Dict) -> List[str]:
    """Generate top 3 recommended actions"""
    actions = []

    # Based on concerns, suggest specific actions
    runway = metrics['runway']['current']

    if runway < 4:
        actions.append("Review and reduce non-essential expenses immediately to improve runway")

    if metrics['expenses']['change_pct'] > 15:
        actions.append("Investigate expense spike - identify and address unusual spending")

    if metrics['revenue']['change_pct'] < -10:
        actions.append("Revenue declining - accelerate sales efforts and review pipeline")

    # Goal-related actions
    at_risk_goals = FinancialGoal.objects.filter(
        organization=organization,
        active=True,
        current_status__in=['at_risk', 'off_track']
    )[:2]  # Top 2

    for goal in at_risk_goals:
        actions.append(f"Address '{goal.name}' goal - currently {goal.get_current_status_display()}")

    # Generic actions if no specific concerns
    if not actions:
        actions.append("Continue current strategy - metrics looking good")
        actions.append("Consider setting new growth goals")
        actions.append("Review and optimize operational efficiency")

    return actions[:3]  # Top 3 only


def _get_upcoming_dates(organization: Organization, as_of_date: date) -> List[Dict]:
    """Get critical dates in next 30 days"""
    dates = []

    # Upcoming goals
    upcoming_goals = FinancialGoal.objects.filter(
        organization=organization,
        active=True,
        target_date__gte=as_of_date,
        target_date__lte=as_of_date + timedelta(days=30)
    ).order_by('target_date')[:5]

    for goal in upcoming_goals:
        days_away = (goal.target_date - as_of_date).days
        dates.append({
            'date': goal.target_date.isoformat(),
            'days_away': days_away,
            'description': f"{goal.name} deadline",
            'type': 'goal',
        })

    # Upcoming large expenses
    upcoming_expenses = Transaction.objects.filter(
        organization=organization,
        date__gt=as_of_date,
        date__lte=as_of_date + timedelta(days=30),
        direction='outflow'
    ).order_by('date')[:5]

    for tx in upcoming_expenses:
        if tx.amount > 1000:  # Only large expenses
            days_away = (tx.date - as_of_date).days
            dates.append({
                'date': tx.date.isoformat(),
                'days_away': days_away,
                'description': f"{tx.description or tx.category}: £{tx.amount:,.0f}",
                'type': 'expense',
            })

    # Sort by date
    dates.sort(key=lambda x: x['days_away'])

    return dates[:5]  # Top 5

