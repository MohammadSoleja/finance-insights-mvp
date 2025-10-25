from django.urls import path, include
from .views import upload_view, dashboard_view, health_view, signup_view
from .forms import LoginForm
from django.contrib.auth import views as auth_views


app_name = "app_web"

urlpatterns = [
    path("", upload_view, name="home"),
    path("upload/", upload_view, name="upload"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("health/", health_view, name="health"),
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

    path("accounts/", include("django.contrib.auth.urls")),
]
