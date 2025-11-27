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


def get_org_currency_info(request):
    """Helper to get organization's currency symbol and code"""
    if hasattr(request, 'organization') and request.organization:
        return {
            'symbol': request.organization.get_currency_symbol(),
            'code': request.organization.preferred_currency
        }
    return {'symbol': '£', 'code': 'GBP'}


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
    # Use display_amount (converted) if available, otherwise use amount
    from django.db.models import Case, When, F
    
    total = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.INFLOW,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(
        total=Sum(
            Case(
                When(display_amount__isnull=False, then=F('display_amount')),
                default=F('amount')
            )
        )
    )['total'] or Decimal('0.00')

    # Previous period for comparison
    days_diff = (end_date - start_date).days
    prev_start = start_date - timedelta(days=days_diff)
    prev_end = start_date - timedelta(days=1)

    prev_total = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.INFLOW,
        date__gte=prev_start,
        date__lte=prev_end
    ).aggregate(
        total=Sum(
            Case(
                When(display_amount__isnull=False, then=F('display_amount')),
                default=F('amount')
            )
        )
    )['total'] or Decimal('0.00')

    change = total - prev_total
    change_pct = (change / prev_total * 100) if prev_total else 0

    return {
        'value': float(total),
        'prev_value': float(prev_total),
        'change': float(change),
        'change_pct': float(change_pct),
        'currency': get_org_currency_info(request)['symbol']
    }


def get_kpi_total_expenses(request, start_date, end_date):
    """Total expenses in period"""
    from django.db.models import Case, When, F
    
    total = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.OUTFLOW,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(
        total=Sum(
            Case(
                When(display_amount__isnull=False, then=F('display_amount')),
                default=F('amount')
            )
        )
    )['total'] or Decimal('0.00')

    days_diff = (end_date - start_date).days
    prev_start = start_date - timedelta(days=days_diff)
    prev_end = start_date - timedelta(days=1)

    prev_total = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.OUTFLOW,
        date__gte=prev_start,
        date__lte=prev_end
    ).aggregate(
        total=Sum(
            Case(
                When(display_amount__isnull=False, then=F('display_amount')),
                default=F('amount')
            )
        )
    )['total'] or Decimal('0.00')

    change = total - prev_total
    change_pct = (change / prev_total * 100) if prev_total else 0

    return {
        'value': float(total),
        'prev_value': float(prev_total),
        'change': float(change),
        'change_pct': float(change_pct),
        'currency': get_org_currency_info(request)['symbol']
    }


def get_kpi_net_cash_flow(request, start_date, end_date):
    """Net cash flow (income - expenses)"""
    from django.db.models import Case, When, F

    income = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.INFLOW,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(
        total=Sum(
            Case(
                When(display_amount__isnull=False, then=F('display_amount')),
                default=F('amount')
            )
        )
    )['total'] or Decimal('0.00')

    expenses = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.OUTFLOW,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(
        total=Sum(
            Case(
                When(display_amount__isnull=False, then=F('display_amount')),
                default=F('amount')
            )
        )
    )['total'] or Decimal('0.00')

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
    ).aggregate(
        total=Sum(
            Case(
                When(display_amount__isnull=False, then=F('display_amount')),
                default=F('amount')
            )
        )
    )['total'] or Decimal('0.00')

    prev_expenses = Transaction.objects.filter(
        organization=request.organization,
        direction=Transaction.OUTFLOW,
        date__gte=prev_start,
        date__lte=prev_end
    ).aggregate(
        total=Sum(
            Case(
                When(display_amount__isnull=False, then=F('display_amount')),
                default=F('amount')
            )
        )
    )['total'] or Decimal('0.00')

    prev_net = prev_income - prev_expenses
    change = net - prev_net
    change_pct = (change / prev_net * 100) if prev_net else 0

    return {
        'value': float(net),
        'prev_value': float(prev_net),
        'change': float(change),
        'change_pct': float(change_pct),
        'currency': get_org_currency_info(request)['symbol']
    }


def get_kpi_avg_transaction(request, start_date, end_date):
    """Average transaction amount"""
    from django.db.models import Case, When, F

    avg = Transaction.objects.filter(
        organization=request.organization,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(
        avg=Avg(
            Case(
                When(display_amount__isnull=False, then=F('display_amount')),
                default=F('amount')
            )
        )
    )['avg'] or Decimal('0.00')

    return {
        'value': float(avg),
        'currency': get_org_currency_info(request)['symbol']
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
        'currency': get_org_currency_info(request)['symbol']
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
        'currency': get_org_currency_info(request)['symbol']
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
        'currency': get_org_currency_info(request)['symbol']
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
        'currency': get_org_currency_info(request)['symbol']
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
        'currency': get_org_currency_info(request)['symbol']
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
        'currency': get_org_currency_info(request)['symbol']
    }

