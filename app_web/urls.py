from django.urls import path, include
from .views import upload_view, health_view, signup_view, home_view, profile_view, settings_view, transactions_view, pricing_view, demo_view, about_view
from .views import transaction_edit_view, transaction_delete_view, transaction_bulk_edit_view
from .views import transaction_columns_view
from .views import budgets_view, budget_widget_data, budget_list_data
from .views import projects_view, project_detail_view, project_list_data, project_detail_data
from .views import invoices_view, clients_view, clients_list_api, invoice_create_view, invoice_edit_view, invoice_delete_view
from .views import invoice_send_view, invoice_payment_view, invoice_detail_view, invoice_reminder_view
from .views import invoice_pdf_view, invoice_pdf_download
from .views import invoice_templates_view, template_create_view, template_edit_view, template_delete_view, template_use_view, template_detail_view
from .views import client_create_view, client_edit_view, client_delete_view
from .views import reports_view, report_pnl_view, report_pnl_download
from .views import report_cashflow_view, report_cashflow_download
from .views import report_expenses_view, report_expenses_download
from .views import report_income_view, report_income_download
from .views import report_tax_view, report_tax_download
from .views import report_budget_performance_view, report_budget_performance_download
from .views import report_project_performance_view, report_project_performance_download
from .views import debug_organization_view, currency_debug_view
from .views import (
    project_tasks, task_create, task_update, task_delete, task_details,
    task_update_status, task_bulk_delete, task_comment_create, task_time_entry_create
)

# Import old dashboard as legacy (keeping for reference)
from .views import dashboard_view as dashboard_legacy_view

# NEW: Dashboard widgets is now the main dashboard
from .dashboard_views import (
    dashboard_view as dashboard_view, get_dashboard_layout, save_dashboard_layout,
    reset_dashboard_layout, get_widget_data
)

# Team collaboration views
from app_core.team_views import (
    switch_organization, team_overview, team_members,
    invite_member, remove_member, change_member_role,
    activity_log,
    approvals_view, approve_request, reject_request,
    approval_workflows_view, create_workflow, delete_workflow
)

from .forms import LoginForm
from django.contrib.auth import views as auth_views


app_name = "app_web"

urlpatterns = [
    path("upload/", upload_view, name="upload"),

    # NEW: Widgets dashboard is now the main dashboard at /dashboard/
    path("dashboard/", dashboard_view, name="dashboard"),
    path("api/dashboard/layout/", get_dashboard_layout, name="get_dashboard_layout"),
    path("api/dashboard/layout/save/", save_dashboard_layout, name="save_dashboard_layout"),
    path("api/dashboard/layout/reset/", reset_dashboard_layout, name="reset_dashboard_layout"),
    path("api/dashboard/widget/<str:widget_id>/", get_widget_data, name="get_widget_data"),

    # OLD: Keep legacy dashboard for reference at /dashboard/legacy/
    path("dashboard/legacy/", dashboard_legacy_view, name="dashboard_legacy"),

    path("pricing/", pricing_view, name="pricing"),
    path("demo/", demo_view, name="demo"),
    path("about/", about_view, name="about"),
    path("transactions/", transactions_view, name="transactions"),
    path("transactions/<int:tx_id>/edit/", transaction_edit_view, name="transaction_edit"),
    path("transactions/<int:tx_id>/delete/", transaction_delete_view, name="transaction_delete"),
    path("transactions/bulk_edit/", transaction_bulk_edit_view, name="transaction_bulk_edit"),
    path("transactions/columns/", transaction_columns_view, name="transaction_columns"),
    path("budgets/", budgets_view, name="budgets"),
    path("api/budget-widget/", budget_widget_data, name="budget_widget_data"),
    path("api/budget-list/", budget_list_data, name="budget_list_data"),
    path("projects/", projects_view, name="projects"),
    path("projects/<int:project_id>/", project_detail_view, name="project_detail"),
    path("api/project-list/", project_list_data, name="project_list_data"),
    path("api/project-detail/<int:project_id>/", project_detail_data, name="project_detail_data"),

    # Invoicing & Billing
    path("invoices/", invoices_view, name="invoices"),
    path("invoices/create/", invoice_create_view, name="invoice_create"),
    path("invoices/<int:invoice_id>/edit/", invoice_edit_view, name="invoice_edit"),
    path("invoices/<int:invoice_id>/delete/", invoice_delete_view, name="invoice_delete"),
    path("invoices/<int:invoice_id>/send/", invoice_send_view, name="invoice_send"),
    path("invoices/<int:invoice_id>/reminder/", invoice_reminder_view, name="invoice_reminder"),
    path("invoices/<int:invoice_id>/payment/", invoice_payment_view, name="invoice_payment"),
    path("invoices/<int:invoice_id>/pdf/", invoice_pdf_view, name="invoice_pdf"),
    path("invoices/<int:invoice_id>/download/", invoice_pdf_download, name="invoice_pdf_download"),
    path("api/invoice-detail/<int:invoice_id>/", invoice_detail_view, name="invoice_detail"),

    # Invoice Templates
    path("templates/", invoice_templates_view, name="invoice_templates"),
    path("templates/create/", template_create_view, name="template_create"),
    path("templates/<int:template_id>/edit/", template_edit_view, name="template_edit"),
    path("templates/<int:template_id>/delete/", template_delete_view, name="template_delete"),
    path("templates/<int:template_id>/use/", template_use_view, name="template_use"),
    path("api/template-detail/<int:template_id>/", template_detail_view, name="template_detail"),

    # Clients
    path("clients/", clients_view, name="clients"),
    path("api/clients/", clients_list_api, name="clients_list_api"),
    path("clients/create/", client_create_view, name="client_create"),
    path("clients/<int:client_id>/edit/", client_edit_view, name="client_edit"),
    path("clients/<int:client_id>/delete/", client_delete_view, name="client_delete"),

    # Reports
    path("reports/", reports_view, name="reports"),
    path("reports/pnl/", report_pnl_view, name="report_pnl"),
    path("reports/pnl/download/", report_pnl_download, name="report_pnl_download"),
    path("reports/cashflow/", report_cashflow_view, name="report_cashflow"),
    path("reports/cashflow/download/", report_cashflow_download, name="report_cashflow_download"),
    path("reports/expenses/", report_expenses_view, name="report_expenses"),
    path("reports/expenses/download/", report_expenses_download, name="report_expenses_download"),
    path("reports/income/", report_income_view, name="report_income"),
    path("reports/income/download/", report_income_download, name="report_income_download"),
    path("reports/tax/", report_tax_view, name="report_tax"),
    path("reports/tax/download/", report_tax_download, name="report_tax_download"),
    path("reports/budget-performance/", report_budget_performance_view, name="report_budget_performance"),
    path("reports/budget-performance/download/", report_budget_performance_download, name="report_budget_performance_download"),
    path("reports/project-performance/", report_project_performance_view, name="report_project_performance"),
    path("reports/project-performance/download/", report_project_performance_download, name="report_project_performance_download"),

    # Team collaboration
    path("switch-organization/<int:org_id>/", switch_organization, name="switch_organization"),
    path("team/", team_overview, name="team_overview"),
    path("team/members/", team_members, name="team_members"),
    path("team/members/invite/", invite_member, name="invite_member"),
    path("team/members/<int:member_id>/remove/", remove_member, name="remove_member"),
    path("team/members/<int:member_id>/change-role/", change_member_role, name="change_member_role"),
    path("team/activity/", activity_log, name="activity_log"),
    path("team/approvals/", approvals_view, name="approvals"),
    path("team/approvals/<int:approval_id>/approve/", approve_request, name="approve_request"),
    path("team/approvals/<int:approval_id>/reject/", reject_request, name="reject_request"),
    path("team/workflows/", approval_workflows_view, name="approval_workflows"),
    path("team/workflows/create/", create_workflow, name="create_workflow"),
    path("team/workflows/<int:workflow_id>/delete/", delete_workflow, name="delete_workflow"),

    # Task/Progress Management
    path("projects/<int:project_id>/tasks/", project_tasks, name="project_tasks"),
    path("tasks/create/<int:project_id>/", task_create, name="task_create"),
    path("tasks/<int:task_id>/update/", task_update, name="task_update"),
    path("tasks/<int:task_id>/delete/", task_delete, name="task_delete"),
    path("tasks/<int:task_id>/details/", task_details, name="task_details"),
    path("tasks/<int:task_id>/status/", task_update_status, name="task_update_status"),
    path("tasks/bulk-delete/", task_bulk_delete, name="task_bulk_delete"),
    path("tasks/<int:task_id>/comments/create/", task_comment_create, name="task_comment_create"),
    path("tasks/<int:task_id>/time/create/", task_time_entry_create, name="task_time_entry_create"),

    # Debug
    path("debug/org/", debug_organization_view, name="debug_org"),
    path("debug/currency/", currency_debug_view, name="currency_debug"),

    path("health/", health_view, name="health"),
    path("", home_view, name="home"),
    # Override the default login so we can use our form with placeholders
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",  # we’ll add this next
            authentication_form=LoginForm,
        ),
        name="login",
    ),

    path("accounts/signup/", signup_view, name="signup"),

    # profile & settings placeholders used by the nav dropdown
    path("profile/", profile_view, name="profile"),
    path("settings/", settings_view, name="settings"),

    path("accounts/", include("django.contrib.auth.urls")),
]
