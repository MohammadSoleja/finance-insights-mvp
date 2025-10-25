# app_core/migrations/0002_create_initial_superuser.py
from django.db import migrations
import os
from django.conf import settings

def create_initial_superuser(apps, schema_editor):
    """
    Creates the first superuser if DJANGO_SUPERUSER_* env vars are set.
    Safe to run multiple times (no-op if user already exists or vars missing).
    """
    username = os.getenv("DJANGO_SUPERUSER_USERNAME")
    email = os.getenv("DJANGO_SUPERUSER_EMAIL")
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
    if not (username and email and password):
        return  # nothing to do

    # Get the current User model via the historical apps registry
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)

    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username=username, email=email, password=password)

def noop(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ("app_core", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(create_initial_superuser, reverse_code=noop),
    ]
