from django.urls import path
from .views import upload_view, dashboard_view

app_name = "app_web"

urlpatterns = [
    path("", upload_view, name="home"),
    path("upload/", upload_view, name="upload"),
    path("dashboard/", dashboard_view, name="dashboard"),
]
