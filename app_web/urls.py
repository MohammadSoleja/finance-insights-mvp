from django.urls import path, include
from .views import upload_view, dashboard_view, health_view, signup_view, home_view, profile_view, settings_view, transactions_view
from .forms import LoginForm
from django.contrib.auth import views as auth_views


app_name = "app_web"

urlpatterns = [
    path("upload/", upload_view, name="upload"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("transactions/", transactions_view, name="transactions"),
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
