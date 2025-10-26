# app_core/models.py
from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()

class Transaction(models.Model):
    INFLOW = "inflow"
    OUTFLOW = "outflow"
    DIRECTION_CHOICES = [(INFLOW, "Inflow"), (OUTFLOW, "Outflow")]

    #user_id = models.IntegerField()  # simple for MVP; replace with FK when auth lands
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    date = models.DateField(db_index=True)
    description = models.CharField(max_length=512)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    category = models.CharField(max_length=128, blank=True, default="")
    subcategory = models.CharField(max_length=128, blank=True, default="")
    account = models.CharField(max_length=128, blank=True, default="")
    source = models.CharField(max_length=64, blank=True, default="csv")  # csv, xlsx, sheets, etc.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["user", "category"]),
        ]
        ordering = ["-date", "-id"]

    def __str__(self):
        sign = "+" if self.direction == self.INFLOW else "-"
        return f"{self.date} {sign}{self.amount} {self.description[:30]}"

class Rule(models.Model):
    # very simple MVP rules: substring/regex → category/subcategory
    #user_id = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rules")
    pattern = models.CharField(max_length=256, help_text="Substring or regex to match in description.")
    is_regex = models.BooleanField(default=False)
    category = models.CharField(max_length=128)
    subcategory = models.CharField(max_length=128, blank=True, default="")
    notes = models.CharField(max_length=256, blank=True, default="")
    priority = models.PositiveIntegerField(default=100)  # lower = applied first
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "priority"]),
            models.Index(fields=["user", "pattern"]),
        ]
        ordering = ["priority", "id"]

    def __str__(self):
        # user is a FK; show user id if available
        uid = getattr(self.user, "id", None)
        return f"[{uid}] {self.pattern} \u2192 {self.category}/{self.subcategory or '-'}"
