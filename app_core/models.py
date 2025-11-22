# app_core/models.py
from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()

# Import team collaboration models
from .team_models import (
    Organization,
    OrganizationRole,
    OrganizationMember,
    PermissionRequest,
    ApprovalWorkflow,
    Approval,
    ActivityLog,
)

class Label(models.Model):
    """
    Labels (tags) for categorizing transactions.
    Users create and manage their own labels.
    """
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="labels", help_text="User who created this label")
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name="labels",
        null=True,  # Temporarily nullable for migration
        blank=True
    )
    name = models.CharField(max_length=64, help_text="Label name (e.g., 'Office Supplies', 'Client A')")
    color = models.CharField(max_length=7, default="#2563eb", help_text="Hex color code for UI display")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "name"]),
            models.Index(fields=["organization", "name"]),
        ]
        ordering = ["name"]
        unique_together = [["user", "name"]]  # Each user's label names must be unique

    def __str__(self):
        return f"{self.name}"


class Transaction(models.Model):
    INFLOW = "inflow"
    OUTFLOW = "outflow"
    DIRECTION_CHOICES = [(INFLOW, "Inflow"), (OUTFLOW, "Outflow")]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions", help_text="User who created this transaction")
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name="transactions",
        null=True,  # Temporarily nullable for migration
        blank=True
    )
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
            models.Index(fields=["organization", "date"]),
        ]
        ordering = ["-date", "-id"]

    def __str__(self):
        sign = "+" if self.direction == self.INFLOW else "-"
        label_name = self.label.name if self.label else self.category or "Uncategorized"
        return f"{self.date} {sign}{self.amount} [{label_name}] {self.description[:30]}"

class Rule(models.Model):
    # very simple MVP rules: substring/regex → category/subcategory
    #user_id = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="rules", help_text="User who created this rule")
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

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="budgets", help_text="User who created this budget")
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name="budgets",
        null=True,  # Temporarily nullable for migration
        blank=True
    )
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
            models.Index(fields=["organization", "active"]),
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

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="recurring_transactions", help_text="User who created this recurring transaction")
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


class Project(models.Model):
    """
    Projects / Cost Centers for tracking finances by project, client, or department.
    Supports 3-level hierarchy: Project → Sub-Project → Task
    """
    STATUS_ACTIVE = "active"
    STATUS_COMPLETED = "completed"
    STATUS_ON_HOLD = "on-hold"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_ON_HOLD, "On Hold"),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="projects", help_text="User who created this project (for audit trail)")
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name="projects",
        null=True,  # Temporarily nullable for migration
        blank=True
    )
    name = models.CharField(max_length=128, help_text="Project name (e.g., 'Q4 Marketing Campaign', 'Client XYZ')")
    description = models.TextField(blank=True, default="", help_text="Project description and notes")
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Project budget")
    start_date = models.DateField(null=True, blank=True, help_text="Project start date")
    end_date = models.DateField(null=True, blank=True, help_text="Project end date")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    # Hierarchy support (3 levels max: 0=parent, 1=sub-project, 2=task)
    parent_project = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sub_projects',
        help_text="Parent project if this is a sub-project"
    )
    level = models.PositiveIntegerField(default=0, help_text="Hierarchy level: 0=parent, 1=sub-project, 2=task")

    # Multi-label support: transactions with these labels are automatically considered part of the project
    labels = models.ManyToManyField(Label, related_name="projects", blank=True, help_text="Labels to track in this project")

    color = models.CharField(max_length=7, default="#3b82f6", help_text="Hex color code for UI display")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "name"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["start_date"]),
            models.Index(fields=["parent_project"]),
            models.Index(fields=["level"]),
        ]
        ordering = ["name"]
        unique_together = [["user", "name"]]  # Each user's project names must be unique

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    def get_all_sub_projects(self):
        """Recursively get all sub-projects (children, grandchildren, etc.)"""
        sub_projects = list(self.sub_projects.all())
        for sub in list(sub_projects):
            sub_projects.extend(sub.get_all_sub_projects())
        return sub_projects

    def get_total_budget_with_subs(self):
        """Get total budget including all sub-projects"""
        from decimal import Decimal
        total = self.budget or Decimal('0.00')
        for sub in self.sub_projects.all():
            total += sub.get_total_budget_with_subs()
        return total


class ProjectTransaction(models.Model):
    """
    Links a Transaction to a Project with optional allocation percentage.
    Allows splitting a transaction across multiple projects.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="project_transactions")
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name="project_allocations")
    allocation_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00,
        help_text="Percentage of the transaction allocated to this project (0-100)"
    )
    notes = models.CharField(max_length=256, blank=True, default="", help_text="Allocation notes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "transaction"]),
        ]
        unique_together = [["project", "transaction"]]

    def __str__(self):
        return f"{self.transaction} → {self.project} ({self.allocation_percentage}%)"


class ProjectMilestone(models.Model):
    """
    Project milestones/deliverables with progress tracking.
    """
    STATUS_PENDING = "pending"
    STATUS_IN_PROGRESS = "in-progress"
    STATUS_COMPLETED = "completed"
    STATUS_OVERDUE = "overdue"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_OVERDUE, "Overdue"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    name = models.CharField(max_length=128, help_text="Milestone name (e.g., 'Design Phase Complete')")
    description = models.TextField(blank=True, default="", help_text="Milestone details")
    due_date = models.DateField(help_text="Milestone due date")
    completed_date = models.DateField(null=True, blank=True, help_text="Date when milestone was completed")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Budget allocated to this milestone")
    owner = models.CharField(max_length=128, blank=True, default="", help_text="Person responsible for this milestone")
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "order"]),
            models.Index(fields=["due_date"]),
        ]
        ordering = ["order", "due_date"]

    def __str__(self):
        return f"{self.project.name} - {self.name} ({self.get_status_display()})"


class ProjectBudgetCategory(models.Model):
    """
    Budget categories for projects (e.g., Labor, Materials, Marketing).
    Allows tracking different types of spending within a project.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='budget_categories')
    name = models.CharField(max_length=64, help_text="Category name (e.g., Labor, Materials, Marketing)")
    allocated_amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Budgeted amount for this category")
    color = models.CharField(max_length=7, default="#6b7280", help_text="Hex color code for UI display")

    # Link to labels to auto-calculate spent amount
    labels = models.ManyToManyField(Label, blank=True, related_name="budget_categories", help_text="Labels that count toward this category")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["project"]),
        ]
        ordering = ["name"]
        unique_together = [["project", "name"]]

    def __str__(self):
        return f"{self.project.name} - {self.name} (£{self.allocated_amount})"


class ProjectActivity(models.Model):
    """
    Auto-generated activity log for project changes.
    Tracks all important events in a project's lifecycle.
    """
    ACTION_CREATED = "created"
    ACTION_UPDATED = "updated"
    ACTION_DELETED = "deleted"
    ACTION_STATUS_CHANGED = "status_changed"
    ACTION_BUDGET_CHANGED = "budget_changed"
    ACTION_MILESTONE_ADDED = "milestone_added"
    ACTION_MILESTONE_COMPLETED = "milestone_completed"
    ACTION_SUB_PROJECT_ADDED = "sub_project_added"
    ACTION_TRANSACTION_ADDED = "transaction_added"

    ACTION_CHOICES = [
        (ACTION_CREATED, "Created"),
        (ACTION_UPDATED, "Updated"),
        (ACTION_DELETED, "Deleted"),
        (ACTION_STATUS_CHANGED, "Status Changed"),
        (ACTION_BUDGET_CHANGED, "Budget Changed"),
        (ACTION_MILESTONE_ADDED, "Milestone Added"),
        (ACTION_MILESTONE_COMPLETED, "Milestone Completed"),
        (ACTION_SUB_PROJECT_ADDED, "Sub-Project Added"),
        (ACTION_TRANSACTION_ADDED, "Transaction Added"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="User who performed this action (null if deleted)")
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    description = models.TextField(help_text="Human-readable description of the action")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.project.name} - {self.get_action_display()} at {self.created_at}"


# ==================== INVOICING & BILLING MODELS ====================

class Client(models.Model):
    """
    Client/Customer management for invoicing.
    """
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="clients", help_text="User who created this client")
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name="clients",
        null=True,  # Temporarily nullable for migration
        blank=True
    )
    name = models.CharField(max_length=128, help_text="Client name")
    email = models.EmailField(help_text="Client email address")
    company = models.CharField(max_length=128, blank=True, default="", help_text="Company name (optional)")
    phone = models.CharField(max_length=32, blank=True, default="", help_text="Phone number (optional)")
    address = models.TextField(blank=True, default="", help_text="Full address")
    tax_id = models.CharField(max_length=64, blank=True, default="", help_text="VAT/Tax ID (optional)")

    # Payment terms
    payment_terms = models.CharField(
        max_length=64,
        default="Net 30",
        help_text="Payment terms (e.g., Net 30, Net 60, Due on Receipt)"
    )

    # Currency support
    currency = models.CharField(max_length=3, default="GBP", help_text="Currency code (GBP, USD, EUR, etc.)")

    # Notes and metadata
    notes = models.TextField(blank=True, default="", help_text="Internal notes about the client")
    active = models.BooleanField(default=True, help_text="Whether client is active")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "name"]),
            models.Index(fields=["user", "email"]),
            models.Index(fields=["user", "active"]),
            models.Index(fields=["organization", "name"]),
        ]
        ordering = ["name"]
        unique_together = [["user", "email"]]  # Each user's client emails must be unique

    def __str__(self):
        return f"{self.name}" + (f" ({self.company})" if self.company else "")


class Invoice(models.Model):
    """
    Professional invoices for billing clients.
    """
    STATUS_DRAFT = "draft"
    STATUS_SENT = "sent"
    STATUS_PAID = "paid"
    STATUS_PARTIALLY_PAID = "partially_paid"
    STATUS_OVERDUE = "overdue"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SENT, "Sent"),
        (STATUS_PAID, "Paid"),
        (STATUS_PARTIALLY_PAID, "Partially Paid"),
        (STATUS_OVERDUE, "Overdue"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices", help_text="User who created this invoice")
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name="invoices",
        null=True,  # Temporarily nullable for migration
        blank=True
    )
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="invoices")

    # Invoice identification
    invoice_number = models.CharField(max_length=32, unique=True, help_text="Unique invoice number (auto-generated)")

    # Dates
    invoice_date = models.DateField(help_text="Invoice issue date")
    due_date = models.DateField(help_text="Payment due date")
    sent_date = models.DateField(null=True, blank=True, help_text="Date invoice was sent")
    paid_date = models.DateField(null=True, blank=True, help_text="Date invoice was fully paid")

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    # Amounts
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Subtotal before tax")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Tax rate percentage (e.g., 20 for 20%)")
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Tax amount")
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Discount amount")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total invoice amount")
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Amount paid so far")

    # Currency
    currency = models.CharField(max_length=3, default="GBP", help_text="Currency code")

    # Notes and terms
    notes = models.TextField(blank=True, default="", help_text="Notes to client (visible on invoice)")
    terms = models.TextField(blank=True, default="", help_text="Payment terms and conditions")
    internal_notes = models.TextField(blank=True, default="", help_text="Internal notes (not visible on invoice)")

    # Project linkage (optional)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices")

    # Recurring invoice settings
    is_recurring = models.BooleanField(default=False, help_text="Whether this invoice recurs automatically")
    recurrence_frequency = models.CharField(
        max_length=10,
        choices=[
            ("monthly", "Monthly"),
            ("quarterly", "Quarterly"),
            ("yearly", "Yearly"),
        ],
        null=True,
        blank=True,
        help_text="How often the invoice recurs"
    )
    recurrence_count = models.PositiveIntegerField(null=True, blank=True, help_text="Number of recurrences (null = indefinite)")
    recurring_group_id = models.CharField(max_length=64, null=True, blank=True, help_text="UUID linking related recurring invoices")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["user", "invoice_date"]),
            models.Index(fields=["client"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["invoice_number"]),
        ]
        ordering = ["-invoice_date", "-id"]

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.client.name} - {self.currency}{self.total} ({self.get_status_display()})"

    @property
    def balance_due(self):
        """Calculate remaining balance"""
        from decimal import Decimal
        return self.total - (self.paid_amount or Decimal('0.00'))

    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        from datetime import date
        return (
            self.status in [self.STATUS_SENT, self.STATUS_PARTIALLY_PAID] and
            self.due_date < date.today()
        )

    def calculate_totals(self):
        """Calculate subtotal, tax, and total from line items"""
        from decimal import Decimal
        items = self.items.all()
        self.subtotal = sum(item.amount for item in items)
        self.tax_amount = (self.subtotal * self.tax_rate / 100).quantize(Decimal('0.01'))
        self.total = self.subtotal + self.tax_amount - self.discount
        return self.total


class InvoiceItem(models.Model):
    """
    Line items for invoices.
    """
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=256, help_text="Item/service description")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1, help_text="Quantity")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Price per unit")
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Line total (quantity × unit_price)")
    order = models.PositiveIntegerField(default=0, help_text="Display order")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["invoice", "order"]),
        ]
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.description} - {self.quantity} × {self.unit_price}"

    def save(self, *args, **kwargs):
        """Auto-calculate amount when saving"""
        self.amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class InvoicePayment(models.Model):
    """
    Track payments received for invoices.
    """
    PAYMENT_METHOD_BANK_TRANSFER = "bank_transfer"
    PAYMENT_METHOD_CARD = "card"
    PAYMENT_METHOD_CASH = "cash"
    PAYMENT_METHOD_CHEQUE = "cheque"
    PAYMENT_METHOD_OTHER = "other"

    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_METHOD_BANK_TRANSFER, "Bank Transfer"),
        (PAYMENT_METHOD_CARD, "Card"),
        (PAYMENT_METHOD_CASH, "Cash"),
        (PAYMENT_METHOD_CHEQUE, "Cheque"),
        (PAYMENT_METHOD_OTHER, "Other"),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_payments",
        help_text="Link to the actual transaction (optional)"
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Payment amount")
    payment_date = models.DateField(help_text="Date payment was received")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default=PAYMENT_METHOD_BANK_TRANSFER)
    reference = models.CharField(max_length=128, blank=True, default="", help_text="Payment reference/transaction ID")
    notes = models.TextField(blank=True, default="", help_text="Payment notes")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["invoice", "payment_date"]),
        ]
        ordering = ["-payment_date"]

    def __str__(self):
        return f"Payment {self.amount} for {self.invoice.invoice_number} on {self.payment_date}"


class InvoiceTemplate(models.Model):
    """
    Reusable invoice templates for common services/products.
    """
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoice_templates", help_text="User who created this template")
    name = models.CharField(max_length=128, help_text="Template name")
    description = models.TextField(blank=True, default="", help_text="Template description")

    # Default settings
    default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Default tax rate %")
    default_payment_terms = models.CharField(max_length=64, default="Net 30", help_text="Default payment terms")
    default_notes = models.TextField(blank=True, default="", help_text="Default notes for invoices")
    default_terms = models.TextField(blank=True, default="", help_text="Default terms and conditions")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "name"]),
        ]
        ordering = ["name"]
        unique_together = [["user", "name"]]

    def __str__(self):
        return self.name


class InvoiceTemplateItem(models.Model):
    """
    Line items for invoice templates.
    """
    template = models.ForeignKey(InvoiceTemplate, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=256, help_text="Item/service description")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1, help_text="Default quantity")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Default price per unit")
    order = models.PositiveIntegerField(default=0, help_text="Display order")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.description} - {self.quantity} × {self.unit_price}"


