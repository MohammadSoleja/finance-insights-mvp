from django.urls import path, include
from .views import upload_view, dashboard_view, health_view, signup_view, home_view, profile_view, settings_view, transactions_view, pricing_view, demo_view, about_view
from .views import transaction_edit_view, transaction_delete_view, transaction_bulk_edit_view
from .views import transaction_columns_view
from .views import budgets_view, budget_widget_data, budget_list_data
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
