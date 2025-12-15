# app_core/goal_templates.py
"""
Pre-built Financial Goal Templates
Organized by category with industry-specific recommendations
"""

from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone


GOAL_TEMPLATES = {
    'cash_management': {
        'name': 'Cash Management',
        'description': 'Build cash reserves and maintain financial stability',
        'templates': [
            {
                'id': 'build_6_month_runway',
                'name': 'Build 6 months runway',
                'goal_type': 'runway',
                'target_value': 6,
                'description': 'Maintain 6 months of operating expenses in cash reserves for financial security',
                'difficulty': 'medium',
                'duration_months': 6,
                'icon': '🛡️',
                'success_tips': [
                    'Track monthly burn rate consistently',
                    'Cut non-essential expenses',
                    'Focus on increasing revenue streams',
                    'Set up automatic savings transfers',
                ],
            },
            {
                'id': 'emergency_fund',
                'name': 'Create 3-month emergency fund',
                'goal_type': 'savings',
                'target_value': None,  # Calculate based on 3 months expenses
                'description': 'Save 3 months of expenses for unexpected situations',
                'difficulty': 'easy',
                'duration_months': 6,
                'icon': '🚨',
                'success_tips': [
                    'Calculate your average monthly expenses',
                    'Save a fixed percentage each month',
                    'Keep funds in liquid, accessible account',
                    'Review and adjust target quarterly',
                ],
            },
            {
                'id': 'reduce_burn_rate',
                'name': 'Reduce burn rate by 20%',
                'goal_type': 'spending_limit',
                'target_value': None,  # Calculate as 80% of current burn
                'description': 'Cut monthly expenses by 20% to extend runway',
                'difficulty': 'hard',
                'duration_months': 3,
                'icon': '🔥',
                'success_tips': [
                    'Audit all recurring expenses',
                    'Negotiate with vendors',
                    'Eliminate underutilized subscriptions',
                    'Review staff costs carefully',
                ],
            },
            {
                'id': 'maintain_minimum_balance',
                'name': 'Maintain £10k minimum balance',
                'goal_type': 'savings',
                'target_value': 10000,
                'description': 'Keep a minimum cash buffer of £10,000 at all times',
                'difficulty': 'medium',
                'duration_months': 3,
                'icon': '💰',
                'success_tips': [
                    'Set up low-balance alerts',
                    'Review cash flow weekly',
                    'Plan large expenses in advance',
                    'Build buffer gradually',
                ],
            },
            {
                'id': 'tax_reserve',
                'name': 'Build tax reserve fund',
                'goal_type': 'savings',
                'target_value': 25000,
                'description': 'Save £25,000 for upcoming tax payments',
                'difficulty': 'medium',
                'duration_months': 12,
                'icon': '💼',
                'success_tips': [
                    'Calculate estimated tax liability',
                    'Save 25-30% of profit regularly',
                    'Keep in separate account',
                    'Consult with accountant',
                ],
            },
            {
                'id': 'growth_fund',
                'name': 'Build £50k growth fund',
                'goal_type': 'savings',
                'target_value': 50000,
                'description': 'Save £50,000 for strategic investments and growth initiatives',
                'difficulty': 'hard',
                'duration_months': 18,
                'icon': '🚀',
                'success_tips': [
                    'Define growth opportunities first',
                    'Set milestone targets',
                    'Review ROI potential',
                    'Balance growth vs stability',
                ],
            },
        ],
    },

    'growth': {
        'name': 'Growth Goals',
        'description': 'Scale revenue and expand your business',
        'templates': [
            {
                'id': 'revenue_50k',
                'name': 'Reach £50k monthly revenue',
                'goal_type': 'revenue_target',
                'target_value': 50000,
                'description': 'Scale monthly recurring revenue to £50,000',
                'difficulty': 'medium',
                'duration_months': 12,
                'icon': '📈',
                'success_tips': [
                    'Focus on high-value customers',
                    'Optimize pricing strategy',
                    'Expand marketing channels',
                    'Track customer acquisition cost',
                ],
            },
            {
                'id': 'double_mrr',
                'name': 'Double MRR in 6 months',
                'goal_type': 'revenue_target',
                'target_value': None,  # Calculate as 2x current MRR
                'description': '100% revenue growth over 6 months',
                'difficulty': 'hard',
                'duration_months': 6,
                'icon': '⚡',
                'success_tips': [
                    'Analyze current growth drivers',
                    'Double down on what works',
                    'Experiment with new channels',
                    'Monitor metrics daily',
                ],
            },
            {
                'id': 'growth_30_pct',
                'name': 'Achieve 30% month-over-month growth',
                'goal_type': 'revenue_target',
                'target_value': None,  # Track as growth rate
                'description': 'Maintain 30% monthly growth rate',
                'difficulty': 'hard',
                'duration_months': 6,
                'icon': '📊',
                'success_tips': [
                    'Focus on scalable channels',
                    'Invest in automation',
                    'Build referral programs',
                    'Optimize conversion funnel',
                ],
            },
            {
                'id': 'profit_margin_25',
                'name': 'Improve profit margin to 25%',
                'goal_type': 'profit_margin',
                'target_value': 25,
                'description': 'Achieve 25% profit margin through efficiency and pricing',
                'difficulty': 'medium',
                'duration_months': 12,
                'icon': '💎',
                'success_tips': [
                    'Audit cost structure',
                    'Review pricing regularly',
                    'Automate where possible',
                    'Focus on high-margin products',
                ],
            },
            {
                'id': 'arr_1m',
                'name': 'Scale to £1M ARR',
                'goal_type': 'revenue_target',
                'target_value': 1000000,
                'description': 'Reach £1 million in annual recurring revenue',
                'difficulty': 'hard',
                'duration_months': 24,
                'icon': '🏆',
                'success_tips': [
                    'Build predictable sales pipeline',
                    'Focus on retention',
                    'Expand to new markets',
                    'Optimize unit economics',
                ],
            },
            {
                'id': 'break_even_q3',
                'name': 'Break even by Q3',
                'goal_type': 'profit_margin',
                'target_value': 0,  # 0% = break even
                'description': 'Achieve profitability by end of Q3',
                'difficulty': 'medium',
                'duration_months': 9,
                'icon': '⚖️',
                'success_tips': [
                    'Balance growth and profitability',
                    'Control burn rate',
                    'Increase average deal size',
                    'Improve gross margins',
                ],
            },
        ],
    },

    'operational': {
        'name': 'Operational Efficiency',
        'description': 'Optimize costs and improve efficiency',
        'templates': [
            {
                'id': 'overhead_20_pct',
                'name': 'Keep overhead under 20% of revenue',
                'goal_type': 'spending_limit',
                'target_value': None,  # Calculate as 20% of revenue
                'description': 'Maintain operational efficiency with overhead below 20% of revenue',
                'difficulty': 'medium',
                'duration_months': 12,
                'icon': '⚙️',
                'success_tips': [
                    'Define what counts as overhead',
                    'Regular cost audits',
                    'Use automation tools',
                    'Negotiate better rates',
                ],
            },
            {
                'id': 'office_expenses_limit',
                'name': 'Keep office expenses under £2k/month',
                'goal_type': 'spending_limit',
                'target_value': 2000,
                'description': 'Maintain office and facility costs below £2,000 per month',
                'difficulty': 'easy',
                'duration_months': 12,
                'icon': '🏢',
                'success_tips': [
                    'Consider co-working spaces',
                    'Go remote-first if possible',
                    'Review lease terms',
                    'Share costs where possible',
                ],
            },
            {
                'id': 'marketing_budget_compliance',
                'name': 'Stay within marketing budget',
                'goal_type': 'budget_compliance',
                'target_value': None,  # Link to marketing budget
                'description': 'Keep marketing spend within allocated budget',
                'difficulty': 'medium',
                'duration_months': 12,
                'icon': '📢',
                'success_tips': [
                    'Track ROI per channel',
                    'Pause underperforming campaigns',
                    'Set spending limits',
                    'Review weekly',
                ],
            },
            {
                'id': 'gross_margin_80',
                'name': 'Maintain 80% gross margin',
                'goal_type': 'profit_margin',
                'target_value': 80,
                'description': 'Keep gross profit margin at 80% or above',
                'difficulty': 'medium',
                'duration_months': 6,
                'icon': '📊',
                'success_tips': [
                    'Focus on pricing power',
                    'Reduce COGS where possible',
                    'Upsell higher-margin products',
                    'Monitor product mix',
                ],
            },
            {
                'id': 'reduce_software_costs',
                'name': 'Cut software costs by 15%',
                'goal_type': 'spending_limit',
                'target_value': None,  # Calculate as 85% of current
                'description': 'Reduce SaaS and software expenses by 15%',
                'difficulty': 'easy',
                'duration_months': 3,
                'icon': '💻',
                'success_tips': [
                    'Audit all subscriptions',
                    'Cancel unused tools',
                    'Consolidate similar tools',
                    'Negotiate annual contracts',
                ],
            },
        ],
    },

    'marketing': {
        'name': 'Marketing & Sales',
        'description': 'Optimize customer acquisition and retention',
        'templates': [
            {
                'id': 'marketing_roi_3x',
                'name': 'Achieve 3:1 marketing ROI',
                'goal_type': 'revenue_target',
                'target_value': None,  # Track as ROI ratio
                'description': 'Generate £3 in revenue for every £1 spent on marketing',
                'difficulty': 'medium',
                'duration_months': 6,
                'icon': '🎯',
                'success_tips': [
                    'Track attribution carefully',
                    'Focus on proven channels',
                    'Test and optimize constantly',
                    'Calculate full customer LTV',
                ],
            },
            {
                'id': 'marketing_15_pct_revenue',
                'name': 'Keep marketing under 15% of revenue',
                'goal_type': 'spending_limit',
                'target_value': None,  # Calculate as 15% of revenue
                'description': 'Maintain marketing efficiency at or below 15% of revenue',
                'difficulty': 'medium',
                'duration_months': 12,
                'icon': '📊',
                'success_tips': [
                    'Focus on high-ROI channels',
                    'Build organic growth',
                    'Leverage word-of-mouth',
                    'Optimize conversion rates',
                ],
            },
            {
                'id': 'reduce_cac',
                'name': 'Reduce CAC by 30%',
                'goal_type': 'spending_limit',
                'target_value': None,  # Calculate as 70% of current CAC
                'description': 'Lower customer acquisition cost by 30%',
                'difficulty': 'hard',
                'duration_months': 6,
                'icon': '💰',
                'success_tips': [
                    'Improve conversion funnel',
                    'Focus on referrals',
                    'Content marketing',
                    'Optimize ad spend',
                ],
            },
        ],
    },
}


def get_template(template_id: str):
    """Get a specific template by ID"""
    for category in GOAL_TEMPLATES.values():
        for template in category['templates']:
            if template['id'] == template_id:
                return template
    return None


def get_templates_by_category(category: str):
    """Get all templates in a category"""
    return GOAL_TEMPLATES.get(category, {}).get('templates', [])


def get_all_templates():
    """Get all templates across all categories"""
    all_templates = []
    for category_data in GOAL_TEMPLATES.values():
        for template in category_data['templates']:
            template_copy = template.copy()
            template_copy['category'] = category_data['name']
            all_templates.append(template_copy)
    return all_templates


def calculate_dynamic_target(organization, template):
    """Calculate dynamic target values based on current data"""
    from .playbook_engine import calculate_runway
    from .metrics import kpis, queryset_to_df
    from .models import Transaction, Budget
    from decimal import Decimal

    template_id = template['id']

    # Emergency fund: 3 months of expenses
    if template_id == 'emergency_fund':
        runway_data = calculate_runway(organization, timezone.now().date())
        monthly_burn = Decimal(str(runway_data['monthly_burn']))
        return monthly_burn * 3

    # Reduce burn rate: 80% of current
    elif template_id == 'reduce_burn_rate':
        runway_data = calculate_runway(organization, timezone.now().date())
        monthly_burn = Decimal(str(runway_data['monthly_burn']))
        return monthly_burn * Decimal('0.80')

    # Double MRR: 2x current revenue
    elif template_id == 'double_mrr':
        # Get last 30 days revenue
        lookback = timezone.now().date() - timedelta(days=30)
        txs = Transaction.objects.filter(
            organization=organization,
            date__gte=lookback,
            direction='inflow'
        )
        df = queryset_to_df(txs)
        current_revenue = Decimal(str(kpis(df)['inflow']))
        return current_revenue * 2

    # Overhead as % of revenue
    elif template_id == 'overhead_20_pct':
        # Get current monthly revenue
        lookback = timezone.now().date() - timedelta(days=30)
        txs = Transaction.objects.filter(
            organization=organization,
            date__gte=lookback,
            direction='inflow'
        )
        df = queryset_to_df(txs)
        monthly_revenue = Decimal(str(kpis(df)['inflow']))
        return monthly_revenue * Decimal('0.20')

    # Marketing budget: 15% of revenue
    elif template_id == 'marketing_15_pct_revenue':
        lookback = timezone.now().date() - timedelta(days=30)
        txs = Transaction.objects.filter(
            organization=organization,
            date__gte=lookback,
            direction='inflow'
        )
        df = queryset_to_df(txs)
        monthly_revenue = Decimal(str(kpis(df)['inflow']))
        return monthly_revenue * Decimal('0.15')

    # Reduce software costs: 85% of current
    elif template_id == 'reduce_software_costs':
        lookback = timezone.now().date() - timedelta(days=90)
        software_txs = Transaction.objects.filter(
            organization=organization,
            date__gte=lookback,
            direction='outflow',
            category__icontains='software'
        )
        if software_txs.exists():
            df = queryset_to_df(software_txs)
            avg_monthly = Decimal(str(kpis(df)['outflow'])) / 3
            return avg_monthly * Decimal('0.85')
        return Decimal('1000')  # Default

    # Reduce CAC: 70% of current
    elif template_id == 'reduce_cac':
        # This would need more sophisticated calculation
        # For now, return a reasonable default
        return Decimal('500')

    # Default: return template target or reasonable default
    return template.get('target_value') or Decimal('10000')

