# app_web/urls.py
from django.urls import path
from .views import upload_view

app_name = "app_web"

urlpatterns = [
    path("upload/", upload_view, name="upload"),
]
