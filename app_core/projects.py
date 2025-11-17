# app_core/projects.py
"""Project / Cost Center logic and calculations with hierarchy support."""

from decimal import Decimal
from django.db.models import Sum, Q, Count
from django.utils import timezone
from datetime import date, timedelta


def get_project_summary(user, Transaction, include_sub_projects=True):
    """
    Calculate summary data for all user's projects with hierarchy support.

    Args:
        user: Django User instance
        Transaction: Transaction model class
        include_sub_projects: If True, include all sub-projects in calculations

    Returns:
        List of dicts with project data including actual vs budget, milestones, sub-projects
    """
    from app_core.models import Project, ProjectTransaction, ProjectMilestone, ProjectBudgetCategory

    # Get only parent projects (level=0) if we want hierarchy view
    # Or get all projects if we want flat view
    if include_sub_projects:
        projects = Project.objects.filter(user=user, parent_project=None).prefetch_related(
            'labels', 'project_transactions', 'milestones', 'budget_categories', 'sub_projects'
        )
    else:
        projects = Project.objects.filter(user=user).prefetch_related(
            'labels', 'project_transactions', 'milestones', 'budget_categories'
        )

    summary_list = []

    for project in projects:
        project_data = _calculate_project_data(project, Transaction, include_sub_projects)
        summary_list.append(project_data)

    return summary_list


def _calculate_project_data(project, Transaction, include_subs=True):
    """
    Calculate comprehensive data for a single project.
    """
    from app_core.models import ProjectTransaction

    # Get all transactions allocated to this project (via ProjectTransaction)
    allocated_txs = ProjectTransaction.objects.filter(project=project).select_related('transaction')

    # Calculate actual amounts considering allocation percentages
    total_inflow = Decimal('0.00')
    total_outflow = Decimal('0.00')

    for pt in allocated_txs:
        tx = pt.transaction
        allocation_factor = pt.allocation_percentage / Decimal('100.00')
        allocated_amount = tx.amount * allocation_factor

        if tx.direction == 'inflow':
            total_inflow += allocated_amount
        else:
            total_outflow += allocated_amount

    # Also get transactions with labels that match project labels (auto-assigned)
    project_label_ids = list(project.labels.values_list('id', flat=True))
    if project_label_ids:
        # Get transactions with these labels that aren't already manually allocated
        already_allocated_tx_ids = set(allocated_txs.values_list('transaction_id', flat=True))

        auto_txs = Transaction.objects.filter(
            user=project.user,
            label_id__in=project_label_ids
        ).exclude(id__in=already_allocated_tx_ids)

        # Filter by date range if project has dates
        if project.start_date:
            auto_txs = auto_txs.filter(date__gte=project.start_date)
        if project.end_date:
            auto_txs = auto_txs.filter(date__lte=project.end_date)

        # Add auto-assigned transactions (100% allocation)
        for tx in auto_txs:
            if tx.direction == 'inflow':
                total_inflow += tx.amount
            else:
                total_outflow += tx.amount

    # If including sub-projects, add their totals
    sub_projects_data = []
    if include_subs:
        for sub in project.sub_projects.all():
            sub_data = _calculate_project_data(sub, Transaction, include_subs=True)
            sub_projects_data.append(sub_data)
            total_inflow += sub_data['total_inflow']
            total_outflow += sub_data['total_outflow']

    # Calculate net and budget variance
    net_amount = total_inflow - total_outflow
    budget_variance = None
    budget_variance_abs = None
    budget_usage_pct = None

    if project.budget:
        budget_variance = project.budget - total_outflow
        budget_variance_abs = abs(budget_variance)
        if project.budget > 0:
            budget_usage_pct = float((total_outflow / project.budget) * 100)

    # Calculate progress if dates are set
    progress_pct = None
    days_remaining = None
    days_remaining_abs = None

    if project.start_date and project.end_date:
        today = timezone.now().date()
        total_days = (project.end_date - project.start_date).days + 1

        if today < project.start_date:
            progress_pct = 0
            days_remaining = (project.end_date - today).days
            days_remaining_abs = abs(days_remaining)
        elif today > project.end_date:
            progress_pct = 100
            days_remaining = (today - project.end_date).days * -1  # Negative for overdue
            days_remaining_abs = abs(days_remaining)
        else:
            elapsed_days = (today - project.start_date).days
            progress_pct = int((elapsed_days / total_days) * 100) if total_days > 0 else 0
            days_remaining = (project.end_date - today).days
            days_remaining_abs = abs(days_remaining)

    # Calculate milestone progress
    milestones = project.milestones.all()
    milestone_progress = None
    milestones_completed = 0
    milestones_total = 0

    if milestones:
        milestones_total = milestones.count()
        milestones_completed = milestones.filter(status='completed').count()
        if milestones_total > 0:
            milestone_progress = int((milestones_completed / milestones_total) * 100)

    # Get budget categories with spending
    budget_categories_data = []
    for category in project.budget_categories.all():
        spent = _calculate_category_spending(category, Transaction)
        budget_categories_data.append({
            'id': category.id,
            'name': category.name,
            'allocated': float(category.allocated_amount),
            'spent': float(spent),
            'remaining': float(category.allocated_amount - spent),
            'usage_pct': float((spent / category.allocated_amount) * 100) if category.allocated_amount > 0 else 0,
            'color': category.color,
        })

    return {
        'id': project.id,
        'name': project.name,
        'description': project.description,
        'budget': project.budget,
        'status': project.status,
        'status_display': project.get_status_display(),
        'start_date': project.start_date,
        'end_date': project.end_date,
        'color': project.color,
        'labels': list(project.labels.all()),
        'level': project.level,
        'parent_project_id': project.parent_project_id if project.parent_project else None,
        'has_sub_projects': project.sub_projects.exists(),
        'sub_projects': sub_projects_data,
        'total_inflow': total_inflow,
        'total_outflow': total_outflow,
        'net_amount': net_amount,
        'budget_variance': budget_variance,
        'budget_variance_abs': budget_variance_abs,
        'budget_usage_pct': budget_usage_pct,
        'progress_pct': progress_pct,
        'days_remaining': days_remaining,
        'days_remaining_abs': days_remaining_abs,
        'milestone_progress': milestone_progress,
        'milestones_completed': milestones_completed,
        'milestones_total': milestones_total,
        'budget_categories': budget_categories_data,
        'created_at': project.created_at,
        'updated_at': project.updated_at,
    }


def _calculate_category_spending(category, Transaction):
    """Calculate total spending for a budget category based on its labels."""
    from app_core.models import ProjectTransaction

    total_spent = Decimal('0.00')

    category_label_ids = list(category.labels.values_list('id', flat=True))
    if not category_label_ids:
        return total_spent

    # Get transactions with these labels within project date range
    project = category.project
    txs = Transaction.objects.filter(
        user=project.user,
        label_id__in=category_label_ids,
        direction='outflow'  # Only count outflows for spending
    )

    if project.start_date:
        txs = txs.filter(date__gte=project.start_date)
    if project.end_date:
        txs = txs.filter(date__lte=project.end_date)

    for tx in txs:
        total_spent += tx.amount

    return total_spent


def get_project_transactions(project, Transaction):
    """
    Get all transactions for a specific project (including sub-projects).

    Args:
        project: Project instance
        Transaction: Transaction model class

    Returns:
        QuerySet of transactions allocated to this project and its sub-projects
    """
    from app_core.models import ProjectTransaction

    # Get manually allocated transactions for this project and all sub-projects
    all_project_ids = [project.id] + [sub.id for sub in project.get_all_sub_projects()]

    allocated_tx_ids = ProjectTransaction.objects.filter(
        project_id__in=all_project_ids
    ).values_list('transaction_id', flat=True)

    # Get auto-assigned transactions (via labels)
    project_label_ids = list(project.labels.values_list('id', flat=True))

    if project_label_ids:
        auto_txs = Transaction.objects.filter(
            user=project.user,
            label_id__in=project_label_ids
        ).exclude(id__in=allocated_tx_ids)

        # Filter by date range
        if project.start_date:
            auto_txs = auto_txs.filter(date__gte=project.start_date)
        if project.end_date:
            auto_txs = auto_txs.filter(date__lte=project.end_date)

        # Combine manual and auto
        all_tx_ids = list(allocated_tx_ids) + list(auto_txs.values_list('id', flat=True))

        return Transaction.objects.filter(id__in=all_tx_ids).order_by('-date')
    else:
        return Transaction.objects.filter(id__in=allocated_tx_ids).order_by('-date')


def calculate_project_pl(project, Transaction):
    """
    Calculate Profit & Loss for a project (including sub-projects).

    Returns:
        Dict with P&L breakdown by label/category
    """
    transactions = get_project_transactions(project, Transaction)

    # Group by label
    inflow_by_label = {}
    outflow_by_label = {}

    for tx in transactions:
        label_name = tx.label.name if tx.label else 'Uncategorized'

        if tx.direction == 'inflow':
            inflow_by_label[label_name] = inflow_by_label.get(label_name, Decimal('0.00')) + tx.amount
        else:
            outflow_by_label[label_name] = outflow_by_label.get(label_name, Decimal('0.00')) + tx.amount

    total_inflow = sum(inflow_by_label.values()) if inflow_by_label else Decimal('0.00')
    total_outflow = sum(outflow_by_label.values()) if outflow_by_label else Decimal('0.00')
    net_profit = total_inflow - total_outflow

    return {
        'inflow_by_label': inflow_by_label,
        'outflow_by_label': outflow_by_label,
        'total_inflow': total_inflow,
        'total_outflow': total_outflow,
        'net_profit': net_profit,
        'profit_margin_pct': float((net_profit / total_inflow) * 100) if total_inflow > 0 else 0,
    }


def log_project_activity(project, user, action, description):
    """
    Create an activity log entry for a project.

    Args:
        project: Project instance
        user: User who performed the action
        action: Action type (from ProjectActivity.ACTION_CHOICES)
        description: Human-readable description
    """
    from app_core.models import ProjectActivity

    ProjectActivity.objects.create(
        project=project,
        user=user,
        action=action,
        description=description
    )


def update_milestone_status(milestone):
    """
    Auto-update milestone status based on due date and completion.
    """
    from app_core.models import ProjectMilestone

    if milestone.completed_date:
        milestone.status = ProjectMilestone.STATUS_COMPLETED
    elif milestone.due_date < timezone.now().date():
        milestone.status = ProjectMilestone.STATUS_OVERDUE
    elif milestone.status == ProjectMilestone.STATUS_PENDING:
        # Keep as pending unless explicitly changed
        pass

    milestone.save(update_fields=['status'])

