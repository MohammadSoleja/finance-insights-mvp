from django.urls import path, include
from .views import upload_view, dashboard_view, health_view, signup_view, home_view, profile_view, settings_view, transactions_view, pricing_view, demo_view, about_view
from .views import transaction_edit_view, transaction_delete_view, transaction_bulk_edit_view
from .views import transaction_columns_view
from .views import budgets_view, budget_widget_data, budget_list_data
from .views import projects_view, project_list_data, project_detail_data
from .views import invoices_view, clients_view, clients_list_api, invoice_create_view, invoice_edit_view, invoice_delete_view
from .views import invoice_send_view, invoice_payment_view, invoice_detail_view, invoice_reminder_view
from .views import invoice_pdf_view, invoice_pdf_download
from .views import invoice_templates_view, template_create_view, template_edit_view, template_delete_view, template_use_view, template_detail_view
from .views import client_create_view, client_edit_view, client_delete_view
from .forms import LoginForm
from django.contrib.auth import views as auth_views


app_name = "app_web"

urlpatterns = [
    path("upload/", upload_view, name="upload"),
    path("dashboard/", dashboard_view, name="dashboard"),
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
