# app_core/models.py
from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()

class Label(models.Model):
    """
    Labels (tags) for categorizing transactions.
    Users create and manage their own labels.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="labels")
    name = models.CharField(max_length=64, help_text="Label name (e.g., 'Office Supplies', 'Client A')")
    color = models.CharField(max_length=7, default="#2563eb", help_text="Hex color code for UI display")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "name"]),
        ]
        ordering = ["name"]
        unique_together = [["user", "name"]]  # Each user's label names must be unique

    def __str__(self):
        return f"{self.name}"


class Transaction(models.Model):
    INFLOW = "inflow"
    OUTFLOW = "outflow"
    DIRECTION_CHOICES = [(INFLOW, "Inflow"), (OUTFLOW, "Outflow")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    date = models.DateField(db_index=True)
    description = models.CharField(max_length=512)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)

    # Label-based categorization (replaces category string)
    label = models.ForeignKey(Label, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")

    # Keep old category field for migration/backward compatibility (will deprecate later)
    category = models.CharField(max_length=128, blank=True, default="", help_text="DEPRECATED: Use label instead")

    subcategory = models.CharField(max_length=128, blank=True, default="")
    account = models.CharField(max_length=128, blank=True, default="")
    source = models.CharField(max_length=64, blank=True, default="csv")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["user", "label"]),
        ]
        ordering = ["-date", "-id"]

    def __str__(self):
        sign = "+" if self.direction == self.INFLOW else "-"
        label_name = self.label.name if self.label else self.category or "Uncategorized"
        return f"{self.date} {sign}{self.amount} [{label_name}] {self.description[:30]}"

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

class Budget(models.Model):
    PERIOD_MONTHLY = "monthly"
    PERIOD_WEEKLY = "weekly"
    PERIOD_YEARLY = "yearly"
    PERIOD_CUSTOM = "custom"
    PERIOD_CHOICES = [
        (PERIOD_MONTHLY, "Monthly"),
        (PERIOD_WEEKLY, "Weekly"),
        (PERIOD_YEARLY, "Yearly"),
        (PERIOD_CUSTOM, "Custom Date Range"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="budgets")
    name = models.CharField(max_length=128, help_text="Budget name (e.g., 'Q4 Marketing', 'Office Renovation')")
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Budget limit")

    # Multi-label support for flexible project-based budgets
    labels = models.ManyToManyField(Label, related_name="budgets", blank=True, help_text="Labels to track in this budget")

    # Keep old category field for backward compatibility during migration
    category = models.CharField(max_length=128, blank=True, default="", help_text="DEPRECATED: Use labels instead")

    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default=PERIOD_MONTHLY)
    # Custom date range fields (optional, used when period='custom')
    start_date = models.DateField(null=True, blank=True, help_text="Custom start date (required for custom period)")
    end_date = models.DateField(null=True, blank=True, help_text="Custom end date (required for custom period)")
    active = models.BooleanField(default=True)

    # Recurring budget settings
    is_recurring = models.BooleanField(default=False, help_text="Whether this budget recurs automatically")
    recurrence_count = models.PositiveIntegerField(null=True, blank=True, help_text="Number of times to recur (e.g., 3 = create budget for next 3 periods)")
    last_generated_period = models.DateField(null=True, blank=True, help_text="Last period start date that was generated")
    recurring_group_id = models.CharField(max_length=64, null=True, blank=True, help_text="UUID linking related recurring budgets together")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "active"]),
            models.Index(fields=["start_date", "end_date"]),
        ]
        ordering = ["name"]

    def __str__(self):
        if self.period == self.PERIOD_CUSTOM and self.start_date and self.end_date:
            return f"{self.name} - £{self.amount} ({self.start_date} to {self.end_date})"
        return f"{self.name} - £{self.amount} ({self.get_period_display()})"


class RecurringTransaction(models.Model):
    """
    Template for transactions that repeat on a schedule.
    Generates actual Transaction instances automatically.
    """
    FREQUENCY_DAILY = "daily"
    FREQUENCY_WEEKLY = "weekly"
    FREQUENCY_MONTHLY = "monthly"
    FREQUENCY_YEARLY = "yearly"

    FREQUENCY_CHOICES = [
        (FREQUENCY_DAILY, "Daily"),
        (FREQUENCY_WEEKLY, "Weekly"),
        (FREQUENCY_MONTHLY, "Monthly"),
        (FREQUENCY_YEARLY, "Yearly"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recurring_transactions")
    description = models.CharField(max_length=512, help_text="Transaction description")
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Transaction amount")
    direction = models.CharField(max_length=10, choices=Transaction.DIRECTION_CHOICES, help_text="Inflow or Outflow")
    label = models.ForeignKey(Label, on_delete=models.SET_NULL, null=True, blank=True, related_name="recurring_transactions")
    category = models.CharField(max_length=128, blank=True, default="")
    subcategory = models.CharField(max_length=128, blank=True, default="")
    account = models.CharField(max_length=128, blank=True, default="")

    # Recurrence settings
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default=FREQUENCY_MONTHLY)
    start_date = models.DateField(help_text="Date of first occurrence")
    end_date = models.DateField(null=True, blank=True, help_text="Optional end date (leave blank for indefinite)")

    # Track generation
    last_generated_date = models.DateField(null=True, blank=True, help_text="Last date a transaction was generated")
    active = models.BooleanField(default=True, help_text="Whether to continue generating transactions")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "active"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["last_generated_date"]),
        ]
        ordering = ["-start_date"]

    def __str__(self):
        sign = "+" if self.direction == Transaction.INFLOW else "-"
        label_name = self.label.name if self.label else self.category or "Uncategorized"
        return f"{sign}£{self.amount} [{label_name}] {self.description[:30]} ({self.get_frequency_display()})"
