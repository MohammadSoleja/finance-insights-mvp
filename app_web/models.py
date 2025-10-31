from django.conf import settings
from django.db import models


class UserTableSetting(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='table_setting')
    columns = models.JSONField(default=list)  # will be initialized in code if empty
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"TableSetting({self.user})"
