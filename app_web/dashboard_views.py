"""
Dashboard Widget Views
Handles widget data and layout management
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta, date, datetime
from decimal import Decimal
import json

from app_core.models import Transaction, Budget, Project, Invoice, Client, Label
from app_core.dashboard_models import DashboardLayout
from app_core.middleware import organization_required


@login_required
@organization_required
def dashboard_view(request):
    """Main dashboard view with customizable widgets"""
    return render(request, 'app_web/dashboard_widgets.html', {
        'page_title': 'Dashboard'
    })


@login_required
@organization_required
@require_http_methods(["GET"])
def get_dashboard_layout(request):
    """Get user's dashboard layout configuration"""
    layout = DashboardLayout.get_or_create_default(
        user=request.user,
        organization=request.organization
    )

    return JsonResponse({
        'success': True,
        'layout': layout.layout_config
    })


@login_required
@organization_required
@require_http_methods(["POST"])
def save_dashboard_layout(request):
    """Save user's dashboard layout configuration"""
    try:
        data = json.loads(request.body)
        layout_config = data.get('layout', {})

        layout, created = DashboardLayout.objects.get_or_create(
            user=request.user,
            organization=request.organization
        )

        layout.layout_config = layout_config
        layout.save()

        return JsonResponse({
            'success': True,
            'message': 'Layout saved successfully'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@organization_required
@require_http_methods(["POST"])
def reset_dashboard_layout(request):
    """Reset dashboard to default layout"""
    try:
        layout, created = DashboardLayout.objects.get_or_create(
            user=request.user,
            organization=request.organization
        )

        layout.layout_config = DashboardLayout.get_default_layout()
        layout.save()

        return JsonResponse({
            'success': True,
            'layout': layout.layout_config
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@organization_required
@require_http_methods(["GET"])
def get_widget_data(request, widget_id):
    """Get data for a specific widget"""
    try:
        # Check if custom start/end dates are provided
        start_param = request.GET.get('start')
        end_param = request.GET.get('end')

        if start_param and end_param:
            # Use custom date range
            try:
                start_date = datetime.strptime(start_param, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_param, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                }, status=400)
        else:
            # Parse date range from query params
            date_range = request.GET.get('dateRange', 'last30days')
            start_date, end_date = parse_date_range(date_range)

        # Route to appropriate widget data function
        widget_data_functions = {
            # KPI Widgets
            'kpi-total-income': get_kpi_total_income,
            'kpi-total-expenses': get_kpi_total_expenses,
            'kpi-net-cash-flow': get_kpi_net_cash_flow,
            'kpi-avg-transaction': get_kpi_avg_transaction,
            'kpi-transaction-count': get_kpi_transaction_count,
            'kpi-budget-progress': get_kpi_budget_progress,
            'kpi-burn-rate': get_kpi_burn_rate,
            'kpi-active-projects': get_kpi_active_projects,
            'kpi-pending-invoices': get_kpi_pending_invoices,
            'kpi-overdue-invoices': get_kpi_overdue_invoices,

            # Chart Widgets
            'chart-revenue-expense': get_chart_revenue_expense,
            'chart-expense-pie': get_chart_expense_pie,
            'chart-income-pie': get_chart_income_pie,
            'chart-trend-line': get_chart_trend_line,
            'chart-waterfall': get_chart_waterfall,
            'chart-budget-performance': get_chart_budget_performance,
            'chart-category-heatmap': get_chart_category_heatmap,
            'chart-money-flow-sankey': get_chart_money_flow_sankey,

            # List Widgets
            'list-recent-transactions': get_list_recent_transactions,
            'list-upcoming-bills': get_list_upcoming_bills,
            'list-budget-alerts': get_list_budget_alerts,
            'list-recent-invoices': get_list_recent_invoices,

            # Summary Widgets
            'summary-financial': get_summary_financial,
            'summary-month-comparison': get_summary_month_comparison,

            # Playbook Widgets
            'widget-playbook-goals': get_widget_playbook_goals,
            'widget-playbook-insights': get_widget_playbook_insights,

            # Phase 1 New Widgets
            'widget-health-score': get_widget_health_score,
            'widget-runway-enhanced': get_widget_runway_enhanced,
            'widget-weekly-briefing': get_widget_weekly_briefing,
            'widget-goal-templates': get_widget_goal_templates,
        }

        if widget_id not in widget_data_functions:
            return JsonResponse({
                'success': False,
                'error': f'Unknown widget: {widget_id}'
            }, status=404)

        data = widget_data_functions[widget_id](request, start_date, end_date)

        return JsonResponse({
            'success': True,
            'widget_id': widget_id,
            'data': data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def parse_date_range(date_range):
    """Convert date range string to start and end dates"""
    today = date.today()

    ranges = {
        'last7days': (today - timedelta(days=7), today),
        'last30days': (today - timedelta(days=30), today),
        'last90days': (today - timedelta(days=90), today),
        'thisMonth': (today.replace(day=1), today),
        'lastMonth': ((today.replace(day=1) - timedelta(days=1)).replace(day=1),
                      today.replace(day=1) - timedelta(days=1)),
        'thisYear': (today.replace(month=1, day=1), today),
    }

    return ranges.get(date_range, ranges['last30days'])


# ==================== KPI WIDGET DATA FUNCTIONS ====================

def get_kpi_total_income(request, start_date, end_date):
    """Total income in period"""
    total = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.INFLOW,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Previous period for comparison
    days_diff = (end_date - start_date).days
    prev_start = start_date - timedelta(days=days_diff)
    prev_end = start_date - timedelta(days=1)

    prev_total = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.INFLOW,
        date__gte=prev_start,
        date__lte=prev_end
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    change = total - prev_total
    change_pct = (change / prev_total * 100) if prev_total else 0

    return {
        'value': float(total),
        'prev_value': float(prev_total),
        'change': float(change),
        'change_pct': float(change_pct),
        'currency': '£'
    }


def get_kpi_total_expenses(request, start_date, end_date):
    """Total expenses in period"""
    total = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.OUTFLOW,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    days_diff = (end_date - start_date).days
    prev_start = start_date - timedelta(days=days_diff)
    prev_end = start_date - timedelta(days=1)

    prev_total = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.OUTFLOW,
        date__gte=prev_start,
        date__lte=prev_end
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    change = total - prev_total
    change_pct = (change / prev_total * 100) if prev_total else 0

    return {
        'value': float(total),
        'prev_value': float(prev_total),
        'change': float(change),
        'change_pct': float(change_pct),
        'currency': '£'
    }


def get_kpi_net_cash_flow(request, start_date, end_date):
    """Net cash flow (income - expenses)"""
    income = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.INFLOW,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    expenses = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.OUTFLOW,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    net = income - expenses

    # Previous period
    days_diff = (end_date - start_date).days
    prev_start = start_date - timedelta(days=days_diff)
    prev_end = start_date - timedelta(days=1)

    prev_income = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.INFLOW,
        date__gte=prev_start,
        date__lte=prev_end
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    prev_expenses = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.OUTFLOW,
        date__gte=prev_start,
        date__lte=prev_end
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    prev_net = prev_income - prev_expenses
    change = net - prev_net
    change_pct = (change / prev_net * 100) if prev_net else 0

    return {
        'value': float(net),
        'prev_value': float(prev_net),
        'change': float(change),
        'change_pct': float(change_pct),
        'currency': '£'
    }


def get_kpi_avg_transaction(request, start_date, end_date):
    """Average transaction amount"""
    avg = Transaction.objects.filter(
        organization=request.organization,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(avg=Avg('amount'))['avg'] or Decimal('0.00')

    return {
        'value': float(avg),
        'currency': '£'
    }


def get_kpi_transaction_count(request, start_date, end_date):
    """Total transaction count"""
    count = Transaction.objects.filter(
        organization=request.organization,
        date__gte=start_date,
        date__lte=end_date
    ).count()

    return {
        'value': count
    }


def get_kpi_budget_progress(request, start_date, end_date):
    """Overall budget progress percentage"""
    budgets = Budget.objects.filter(
        organization=request.organization,
        active=True
    )

    if not budgets.exists():
        return {'value': 0, 'total_budget': 0, 'total_spent': 0}

    total_budget = budgets.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Calculate spent for each budget
    total_spent = Decimal('0.00')
    for budget in budgets:
        labels = budget.labels.all()
        if labels.exists():
            spent = Transaction.objects.filter(
                organization=request.organization,
                direction=Transaction.OUTFLOW,
                label__in=labels,
                date__gte=start_date,
                date__lte=end_date
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            total_spent += spent

    progress = (total_spent / total_budget * 100) if total_budget else 0

    return {
        'value': float(progress),
        'total_budget': float(total_budget),
        'total_spent': float(total_spent),
        'currency': '£'
    }


def get_kpi_burn_rate(request, start_date, end_date):
    """Daily burn rate (average daily spending)"""
    total_expenses = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.OUTFLOW,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    days = (end_date - start_date).days or 1
    burn_rate = total_expenses / days

    return {
        'value': float(burn_rate),
        'total_expenses': float(total_expenses),
        'days': days,
        'currency': '£'
    }


def get_kpi_active_projects(request, start_date, end_date):
    """Count of active projects"""
    count = Project.objects.filter(
        organization=request.organization,
        status=Project.STATUS_ACTIVE
    ).count()

    return {
        'value': count
    }


def get_kpi_pending_invoices(request, start_date, end_date):
    """Pending invoices count and amount"""
    pending = Invoice.objects.filter(
        organization=request.organization,
        status__in=[Invoice.STATUS_SENT, Invoice.STATUS_PARTIALLY_PAID]
    )

    count = pending.count()
    total = pending.aggregate(total=Sum('total'))['total'] or Decimal('0.00')

    return {
        'count': count,
        'value': float(total),
        'currency': '£'
    }


def get_kpi_overdue_invoices(request, start_date, end_date):
    """Overdue invoices count and amount"""
    overdue = Invoice.objects.filter(
        organization=request.organization,
        status=Invoice.STATUS_OVERDUE
    )

    count = overdue.count()
    total = overdue.aggregate(total=Sum('total'))['total'] or Decimal('0.00')

    return {
        'count': count,
        'value': float(total),
        'currency': '£'
    }


# ==================== CHART WIDGET DATA FUNCTIONS ====================

def get_chart_revenue_expense(request, start_date, end_date):
    """Revenue vs Expenses bar chart data"""
    income = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.INFLOW,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    expenses = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.OUTFLOW,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    net = income - expenses

    return {
        'labels': ['Income', 'Expenses', 'Net'],
        'datasets': [{
            'label': 'Amount (£)',
            'data': [float(income), float(expenses), float(net)],
            'backgroundColor': ['#10b981', '#ef4444', '#3b82f6']
        }]
    }


def get_chart_expense_pie(request, start_date, end_date):
    """Expense breakdown by category pie chart"""
    # Define a nice color palette for fallback
    color_palette = [
        '#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6',
        '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
        '#14b8a6', '#a855f7', '#f43f5e', '#eab308'
    ]

    # Group by label
    expenses_by_label = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.OUTFLOW,
        date__gte=start_date,
        date__lte=end_date,
        label__isnull=False
    ).values('label__name', 'label__color').annotate(
        total=Sum('amount')
    ).order_by('-total')[:10]

    labels = [item['label__name'] for item in expenses_by_label]
    data = [float(item['total']) for item in expenses_by_label]

    # Use label color if available, otherwise use palette
    colors = []
    for i, item in enumerate(expenses_by_label):
        if item['label__color']:
            colors.append(item['label__color'])
        else:
            colors.append(color_palette[i % len(color_palette)])

    return {
        'labels': labels,
        'datasets': [{
            'data': data,
            'backgroundColor': colors
        }]
    }


def get_chart_income_pie(request, start_date, end_date):
    """Income breakdown by category pie chart"""
    # Define a nice color palette for fallback
    color_palette = [
        '#10b981', '#3b82f6', '#8b5cf6', '#06b6d4', '#84cc16',
        '#14b8a6', '#6366f1', '#22c55e', '#0ea5e9', '#a855f7',
        '#2dd4bf', '#60a5fa', '#34d399', '#38bdf8'
    ]

    income_by_label = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.INFLOW,
        date__gte=start_date,
        date__lte=end_date,
        label__isnull=False
    ).values('label__name', 'label__color').annotate(
        total=Sum('amount')
    ).order_by('-total')[:10]

    labels = [item['label__name'] for item in income_by_label]
    data = [float(item['total']) for item in income_by_label]

    # Use label color if available, otherwise use palette
    colors = []
    for i, item in enumerate(income_by_label):
        if item['label__color']:
            colors.append(item['label__color'])
        else:
            colors.append(color_palette[i % len(color_palette)])

    return {
        'labels': labels,
        'datasets': [{
            'data': data,
            'backgroundColor': colors
        }]
    }


def get_chart_trend_line(request, start_date, end_date):
    """Income/Expense trend line chart"""
    # Generate daily data points
    from collections import defaultdict

    transactions = Transaction.objects.filter(
        organization=request.organization,
        date__gte=start_date,
        date__lte=end_date
    ).values('date', 'direction', 'amount')

    daily_income = defaultdict(float)
    daily_expense = defaultdict(float)

    for txn in transactions:
        if txn['direction'] == Transaction.INFLOW:
            daily_income[txn['date'].isoformat()] += float(txn['amount'])
        else:
            daily_expense[txn['date'].isoformat()] += float(txn['amount'])

    # Get all dates in range
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current.isoformat())
        current += timedelta(days=1)

    income_data = [daily_income.get(d, 0) for d in dates]
    expense_data = [daily_expense.get(d, 0) for d in dates]
    net_data = [daily_income.get(d, 0) - daily_expense.get(d, 0) for d in dates]

    return {
        'labels': dates,
        'datasets': [
            {
                'label': 'Income',
                'data': income_data,
                'borderColor': '#10b981',
                'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                'fill': True
            },
            {
                'label': 'Expenses',
                'data': expense_data,
                'borderColor': '#ef4444',
                'backgroundColor': 'rgba(239, 68, 68, 0.1)',
                'fill': True
            },
            {
                'label': 'Net',
                'data': net_data,
                'borderColor': '#3b82f6',
                'backgroundColor': 'rgba(59, 130, 246, 0.1)',
                'fill': True
            }
        ]
    }


def get_chart_waterfall(request, start_date, end_date):
    """Cash flow waterfall chart"""
    # Simplified waterfall - starting balance, income, expenses, ending
    income = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.INFLOW,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    expenses = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.OUTFLOW,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Get balance before period
    prev_income = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.INFLOW,
        date__lt=start_date
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    prev_expenses = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.OUTFLOW,
        date__lt=start_date
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    starting = prev_income - prev_expenses
    ending = starting + income - expenses

    return {
        'labels': ['Starting Balance', 'Income', 'Expenses', 'Ending Balance'],
        'data': [
            float(starting),
            float(income),
            -float(expenses),
            float(ending)
        ]
    }


def get_chart_budget_performance(request, start_date, end_date):
    """Budget vs Actual performance bars"""
    budgets = Budget.objects.filter(
        organization=request.organization,
        active=True
    )[:10]

    labels = []
    budget_data = []
    actual_data = []

    for budget in budgets:
        labels.append(budget.name)
        budget_data.append(float(budget.amount))

        # Calculate spent
        labels_in_budget = budget.labels.all()
        if labels_in_budget.exists():
            spent = Transaction.objects.filter(
                organization=request.organization,
                direction=Transaction.OUTFLOW,
                label__in=labels_in_budget,
                date__gte=start_date,
                date__lte=end_date
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            actual_data.append(float(spent))
        else:
            actual_data.append(0)

    return {
        'labels': labels,
        'datasets': [
            {
                'label': 'Budget',
                'data': budget_data,
                'backgroundColor': '#3b82f6'
            },
            {
                'label': 'Actual',
                'data': actual_data,
                'backgroundColor': '#ef4444'
            }
        ]
    }


def get_chart_category_heatmap(request, start_date, end_date):
    """Category spending heatmap (for advanced viz)"""
    # Return data structure for heatmap
    # This will be rendered with Recharts
    categories = Label.objects.filter(organization=request.organization)[:15]

    heatmap_data = []
    for cat in categories:
        spending = Transaction.objects.filter(
            organization=request.organization,
            direction=Transaction.OUTFLOW,
            label=cat,
            date__gte=start_date,
            date__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        if spending:
            heatmap_data.append({
                'category': cat.name,
                'value': float(spending),
                'color': cat.color
            })

    return {'data': heatmap_data}


def get_chart_money_flow_sankey(request, start_date, end_date):
    """Money flow Sankey diagram data"""
    # Income sources -> Categories -> Projects
    flows = []

    # Income labels
    income_by_label = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.INFLOW,
        date__gte=start_date,
        date__lte=end_date,
        label__isnull=False
    ).values('label__name').annotate(total=Sum('amount'))

    for item in income_by_label:
        flows.append({
            'source': item['label__name'],
            'target': 'Total Income',
            'value': float(item['total'])
        })

    # Expense categories
    expense_by_label = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.OUTFLOW,
        date__gte=start_date,
        date__lte=end_date,
        label__isnull=False
    ).values('label__name').annotate(total=Sum('amount'))

    for item in expense_by_label:
        flows.append({
            'source': 'Total Income',
            'target': item['label__name'],
            'value': float(item['total'])
        })

    return {'flows': flows}


# ==================== LIST WIDGET DATA FUNCTIONS ====================

def get_list_recent_transactions(request, start_date, end_date):
    """Recent transactions list"""
    transactions = Transaction.objects.filter(
        organization=request.organization,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('-date', '-id')[:10]

    data = []
    for txn in transactions:
        data.append({
            'id': txn.id,
            'date': txn.date.isoformat(),
            'description': txn.description,
            'amount': float(txn.amount),
            'direction': txn.direction,
            'label': txn.label.name if txn.label else 'Uncategorized',
            'color': txn.label.color if txn.label else '#6b7280'
        })

    return {'transactions': data}


def get_list_upcoming_bills(request, start_date, end_date):
    """Upcoming bills/due dates"""
    # TODO: Bills feature not yet implemented
    # Currently showing invoices, but bills (recurring expenses/obligations) are different
    # Return empty state until bills feature is implemented

    return {'bills': [], 'message': 'Bills feature coming soon'}



def get_list_budget_alerts(request, start_date, end_date):
    """Budget alerts for over/near limit"""
    budgets = Budget.objects.filter(
        organization=request.organization,
        active=True
    )

    alerts = []
    for budget in budgets:
        labels_in_budget = budget.labels.all()
        if labels_in_budget.exists():
            spent = Transaction.objects.filter(
                organization=request.organization,
                direction=Transaction.OUTFLOW,
                label__in=labels_in_budget,
                date__gte=start_date,
                date__lte=end_date
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            pct = (spent / budget.amount * 100) if budget.amount else 0

            # Determine status based on percentage
            if pct >= 100:
                status = 'danger'
            elif pct >= 80:
                status = 'warning'
            else:
                status = 'ok'

            # Show all budgets, not just ones over 80%
            alerts.append({
                'budget_name': budget.name,
                'amount': float(budget.amount),
                'spent': float(spent),
                'pct': float(pct),
                'status': status
            })

    return {'alerts': alerts}


def get_list_recent_invoices(request, start_date, end_date):
    """Recent invoices list"""
    invoices = Invoice.objects.filter(
        organization=request.organization,
        invoice_date__gte=start_date,
        invoice_date__lte=end_date
    ).order_by('-invoice_date', '-id')[:5]

    data = []
    for inv in invoices:
        data.append({
            'id': inv.id,
            'invoice_number': inv.invoice_number,
            'client': inv.client.name,
            'date': inv.invoice_date.isoformat(),
            'total': float(inv.total),
            'status': inv.status,
            'balance_due': float(inv.balance_due)
        })

    return {'invoices': data}


# ==================== SUMMARY WIDGET DATA FUNCTIONS ====================

def get_summary_financial(request, start_date, end_date):
    """Financial summary card"""
    income = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.INFLOW,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    expenses = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.OUTFLOW,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    net = income - expenses
    txn_count = Transaction.objects.filter(
        organization=request.organization,
        date__gte=start_date,
        date__lte=end_date
    ).count()

    avg = (income + expenses) / txn_count if txn_count else 0

    return {
        'income': float(income),
        'expenses': float(expenses),
        'net': float(net),
        'transaction_count': txn_count,
        'avg_transaction': float(avg),
        'currency': '£'
    }


def get_summary_month_comparison(request, start_date, end_date):
    """Month-over-month comparison"""
    # This month
    today = date.today()
    this_month_start = today.replace(day=1)

    this_income = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.INFLOW,
        date__gte=this_month_start,
        date__lte=today
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    this_expenses = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.OUTFLOW,
        date__gte=this_month_start,
        date__lte=today
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Last month
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    last_income = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.INFLOW,
        date__gte=last_month_start,
        date__lte=last_month_end
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    last_expenses = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.OUTFLOW,
        date__gte=last_month_start,
        date__lte=last_month_end
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    income_change = ((this_income - last_income) / last_income * 100) if last_income else 0
    expense_change = ((this_expenses - last_expenses) / last_expenses * 100) if last_expenses else 0

    return {
        'this_month': {
            'income': float(this_income),
            'expenses': float(this_expenses),
            'net': float(this_income - this_expenses)
        },
        'last_month': {
            'income': float(last_income),
            'expenses': float(last_expenses),
            'net': float(last_income - last_expenses)
        },
        'changes': {
            'income_pct': float(income_change),
            'expense_pct': float(expense_change)
        },
        'currency': '£'
    }


# ==================== PLAYBOOK WIDGET DATA FUNCTIONS ====================

def get_widget_playbook_goals(request, start_date, end_date):
    """
    Playbook Goals Widget - Shows ALL active goals
    Sorted by priority: off_track → at_risk → on_track → achieved → not_started
    Widget is scrollable to see all goals
    """
    from app_core.models import FinancialGoal
    from django.db.models import Case, When, IntegerField

    # Get ALL active goals, sorted by status priority
    # Order: off_track (most critical) → at_risk → on_track → achieved → not_started (least urgent)
    goals = FinancialGoal.objects.filter(
        organization=request.organization,
        active=True
    ).annotate(
        status_priority=Case(
            When(current_status='off_track', then=1),
            When(current_status='at_risk', then=2),
            When(current_status='on_track', then=3),
            When(current_status='achieved', then=4),
            When(current_status='not_started', then=5),
            default=6,
            output_field=IntegerField()
        )
    ).order_by('status_priority', '-last_evaluated_at')

    # Format all goals
    goals_data = []
    for goal in goals:
        goals_data.append({
            'id': goal.id,
            'name': goal.name,
            'type': goal.get_goal_type_display(),
            'status': goal.current_status,
            'progress': float(goal.progress_percentage) if goal.progress_percentage else 0,
            'current_value': float(goal.current_value) if goal.current_value else 0,
            'target_value': float(goal.target_value) if goal.target_value else 0,
            'target_date': goal.target_date.isoformat() if goal.target_date else None,
            'last_updated': goal.last_evaluated_at.isoformat() if goal.last_evaluated_at else None,
        })

    # Get counts by status
    total_goals = goals.count()
    on_track_count = goals.filter(current_status='on_track').count()
    critical_count = goals.filter(current_status__in=['at_risk', 'off_track']).count()

    return {
        'goals': goals_data,
        'total_goals': total_goals,
        'on_track_count': on_track_count,
        'critical_count': critical_count,
        'has_critical': critical_count > 0
    }


def get_widget_playbook_insights(request, start_date, end_date):
    """
    Playbook AI Insights Widget - Shows AI-generated insights for goals
    Displays brief summaries of goal status with actionable insights
    """
    from app_core import ai_service

    # Get AI insights using existing function
    insights = ai_service.get_playbook_insights(
        request.organization,
        context='dashboard'
    )

    # Limit to top 3 most important insights for dashboard
    dashboard_insights = insights[:3] if insights else []

    # Format for dashboard widget
    formatted_insights = []
    for insight in dashboard_insights:
        formatted_insights.append({
            'title': insight.get('title', ''),
            'content': insight.get('content', ''),
            'severity': insight.get('severity', 'info'),
            'goal_id': insight.get('goal_id'),
            'icon': _get_insight_icon(insight.get('severity', 'info'))
        })

    return {
        'insights': formatted_insights,
        'has_insights': len(formatted_insights) > 0
    }


def _get_insight_icon(severity):
    """Helper function to get icon based on insight severity"""
    icon_map = {
        'good': '✓',
        'warn': '⚠',
        'bad': '✗',
        'info': 'ℹ'
    }
    return icon_map.get(severity, 'ℹ')


# ========== NEW PHASE 1 WIDGETS ==========

def get_widget_health_score(request, start_date, end_date):
    """
    Financial Health Score Widget
    Displays overall business health (0-100) with component breakdown
    """
    from app_core.health_score import calculate_health_score, get_score_trend

    # Get current health score
    health_data = calculate_health_score(request.organization, end_date)

    # Get trend (last 30 days)
    trend_data = get_score_trend(request.organization, days=30)

    # Format components for display
    components = []
    for key, data in health_data['components'].items():
        component_name = key.replace('_', ' ').title()
        components.append({
            'name': component_name,
            'score': data['score'],
            'status': data['status'],
            'weight': data['weight'],
            'icon': _get_component_icon(key)
        })

    return {
        'total_score': health_data['total_score'],
        'level': health_data['level_text'],
        'badge': health_data['badge'],
        'change': trend_data.get('change', 0),
        'trend': trend_data.get('trend', 'stable'),
        'components': components,
        'explanation': health_data['explanation'],
        'trend_dates': trend_data.get('dates', []),
        'trend_scores': trend_data.get('scores', []),
    }


def get_widget_runway_enhanced(request, start_date, end_date):
    """
    Enhanced Runway Intelligence Widget
    Shows runway scenarios, burn breakdown, and savings opportunities
    """
    from app_core.playbook_engine import calculate_runway_enhanced

    runway_data = calculate_runway_enhanced(request.organization, end_date)

    # Format scenarios
    scenarios = [
        {
            'name': 'Best Case',
            'months': runway_data['scenarios']['best_case']['runway_months'],
            'description': runway_data['scenarios']['best_case']['description'],
            'change_pct': runway_data['scenarios']['best_case']['change_pct'],
            'color': 'success'
        },
        {
            'name': 'Expected',
            'months': runway_data['scenarios']['expected']['runway_months'],
            'description': runway_data['scenarios']['expected']['description'],
            'change_pct': 0,
            'color': 'primary'
        },
        {
            'name': 'Worst Case',
            'months': runway_data['scenarios']['worst_case']['runway_months'],
            'description': runway_data['scenarios']['worst_case']['description'],
            'change_pct': runway_data['scenarios']['worst_case']['change_pct'],
            'color': 'danger'
        }
    ]

    # Get top burn categories
    burn_breakdown = runway_data['burn_breakdown'][:5]  # Top 5

    # Get top 3 savings opportunities
    opportunities = runway_data['savings_opportunities'][:3]

    # Critical dates
    critical_dates = runway_data['critical_dates']

    return {
        'current_runway': runway_data['current']['runway_months'],
        'monthly_burn': runway_data['current']['monthly_burn'],
        'current_balance': runway_data['current']['current_balance'],
        'scenarios': scenarios,
        'burn_breakdown': burn_breakdown,
        'opportunities': opportunities,
        'runway_end_date': critical_dates.get('runway_end_date'),
        'days_until_end': critical_dates.get('days_until_end'),
        'threshold_3_months': critical_dates.get('threshold_3_months'),
    }


def get_widget_weekly_briefing(request, start_date, end_date):
    """
    Weekly Briefing Summary Widget
    Shows key metrics, concerns, and action items from latest briefing
    """
    from app_core.weekly_briefing import generate_weekly_briefing

    briefing_data = generate_weekly_briefing(request.organization, end_date)

    # Format for widget display
    return {
        'health_score': briefing_data['health_score'],
        'runway': briefing_data['key_metrics']['runway'],
        'revenue': briefing_data['key_metrics']['revenue'],
        'expenses': briefing_data['key_metrics']['expenses'],
        'concerns': briefing_data['concerns'][:3],  # Top 3
        'good_news': briefing_data['good_news'][:2],  # Top 2
        'action_items': briefing_data['action_items'],  # Top 3 already
        'upcoming_dates': briefing_data['upcoming_dates'][:3],  # Next 3
        'week_of': briefing_data['week_of'],
    }


def get_widget_goal_templates(request, start_date, end_date):
    """
    Goal Templates Quick Start Widget
    Shows popular templates for quick goal creation
    """
    from app_core.goal_templates import GOAL_TEMPLATES
    from app_core.models import FinancialGoal

    # Get popular templates (one from each category)
    popular_templates = [
        {
            'id': 'build_6_month_runway',
            'name': 'Build 6 months runway',
            'category': 'Cash Management',
            'icon': '🛡️',
            'difficulty': 'medium',
            'description': 'Maintain 6 months of operating expenses in cash reserves'
        },
        {
            'id': 'revenue_50k',
            'name': 'Reach £50k monthly revenue',
            'category': 'Growth',
            'icon': '📈',
            'difficulty': 'medium',
            'description': 'Scale monthly recurring revenue to £50,000'
        },
        {
            'id': 'overhead_20_pct',
            'name': 'Keep overhead under 20%',
            'category': 'Operational',
            'icon': '⚙️',
            'difficulty': 'medium',
            'description': 'Maintain operational efficiency'
        },
        {
            'id': 'marketing_roi_3x',
            'name': 'Achieve 3:1 marketing ROI',
            'category': 'Marketing',
            'icon': '🎯',
            'difficulty': 'medium',
            'description': 'Generate £3 for every £1 spent'
        }
    ]

    # Get user's goal stats
    total_goals = FinancialGoal.objects.filter(
        organization=request.organization,
        active=True
    ).count()

    return {
        'templates': popular_templates,
        'total_templates': 20,
        'user_goal_count': total_goals,
        'has_goals': total_goals > 0
    }


def _get_component_icon(component_key):
    """Helper to get icon for health score components"""
    icons = {
        'runway': '🛡️',
        'revenue_growth': '📈',
        'expense_control': '💰',
        'goal_progress': '🎯',
        'stability': '⚖️',
    }
    return icons.get(component_key, '📊')


