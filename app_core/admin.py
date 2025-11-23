# core/admin.py
from django.contrib import admin
from .models import (
    Transaction, Rule, Budget, Label, RecurringTransaction,
    Project, ProjectTransaction, ProjectMilestone, ProjectBudgetCategory, ProjectActivity,
    Client, Invoice, InvoiceItem, InvoicePayment, InvoiceTemplate, InvoiceTemplateItem
)
from .task_models import Task, TaskComment, TaskTimeEntry, TaskActivity

@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ("name", "color", "user", "created_at")
    list_filter = ("user",)
    search_fields = ("name", "user__username")
    ordering = ("user", "name")

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "description", "amount", "direction", "label", "category", "account", "user")
    list_filter = ("direction", "label", "account", "source")
    search_fields = ("description", "category", "subcategory", "account")
    date_hierarchy = "date"

@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ("pattern", "is_regex", "category", "subcategory", "priority", "active", "user")
    list_filter = ("active", "is_regex")
    search_fields = ("pattern", "category", "subcategory", "notes")
    ordering = ("priority",)

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("name", "amount", "period", "active", "user", "created_at")
    list_filter = ("period", "active", "user")
    search_fields = ("name", "category", "user__username")
    ordering = ("user", "name")
    filter_horizontal = ("labels",)  # Nice UI for many-to-many

@admin.register(RecurringTransaction)
class RecurringTransactionAdmin(admin.ModelAdmin):
    list_display = ("description", "amount", "direction", "frequency", "start_date", "end_date", "active", "user")
    list_filter = ("frequency", "direction", "active", "user")
    search_fields = ("description", "category", "user__username")
    ordering = ("user", "-start_date")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "parent_project", "level", "budget", "status", "start_date", "end_date", "user", "created_at")
    list_filter = ("status", "level", "user")
    search_fields = ("name", "description", "user__username")
    ordering = ("user", "level", "name")
    filter_horizontal = ("labels",)  # Nice UI for many-to-many


@admin.register(ProjectTransaction)
class ProjectTransactionAdmin(admin.ModelAdmin):
    list_display = ("project", "transaction", "allocation_percentage", "notes", "created_at")
    list_filter = ("project", "project__user")
    search_fields = ("project__name", "transaction__description", "notes")
    ordering = ("-created_at",)


@admin.register(ProjectMilestone)
class ProjectMilestoneAdmin(admin.ModelAdmin):
    list_display = ("project", "name", "status", "due_date", "completed_date", "owner", "budget", "order")
    list_filter = ("status", "project")
    search_fields = ("name", "description", "project__name", "owner")
    ordering = ("project", "order", "due_date")


@admin.register(ProjectBudgetCategory)
class ProjectBudgetCategoryAdmin(admin.ModelAdmin):
    list_display = ("project", "name", "allocated_amount", "color", "created_at")
    list_filter = ("project",)
    search_fields = ("name", "project__name")
    ordering = ("project", "name")
    filter_horizontal = ("labels",)


@admin.register(ProjectActivity)
class ProjectActivityAdmin(admin.ModelAdmin):
    list_display = ("project", "action", "user", "description", "created_at")
    list_filter = ("action", "project", "user")
    search_fields = ("description", "project__name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


# ==================== INVOICING & BILLING ADMIN ====================

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "company", "currency", "active", "user", "created_at")
    list_filter = ("active", "currency", "user")
    search_fields = ("name", "email", "company", "user__username")
    ordering = ("user", "name")


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    fields = ("description", "quantity", "unit_price", "amount", "order")
    readonly_fields = ("amount",)


class InvoicePaymentInline(admin.TabularInline):
    model = InvoicePayment
    extra = 0
    fields = ("amount", "payment_date", "payment_method", "reference", "notes")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "client", "invoice_date", "due_date", "status", "total", "paid_amount", "balance_due", "user")
    list_filter = ("status", "invoice_date", "user", "currency")
    search_fields = ("invoice_number", "client__name", "client__email", "user__username")
    ordering = ("-invoice_date", "-id")
    inlines = [InvoiceItemInline, InvoicePaymentInline]
    readonly_fields = ("invoice_number", "subtotal", "tax_amount", "total", "paid_amount", "created_at", "updated_at")

    def balance_due(self, obj):
        return obj.balance_due
    balance_due.short_description = "Balance Due"


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ("invoice", "description", "quantity", "unit_price", "amount", "order")
    list_filter = ("invoice__status",)
    search_fields = ("description", "invoice__invoice_number")
    ordering = ("invoice", "order")


@admin.register(InvoicePayment)
class InvoicePaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "payment_date", "payment_method", "reference")
    list_filter = ("payment_method", "payment_date")
    search_fields = ("invoice__invoice_number", "reference", "notes")
    ordering = ("-payment_date",)


class InvoiceTemplateItemInline(admin.TabularInline):
    model = InvoiceTemplateItem
    extra = 1
    fields = ("description", "quantity", "unit_price", "order")


@admin.register(InvoiceTemplate)
class InvoiceTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "default_tax_rate", "default_payment_terms", "user", "created_at")
    list_filter = ("user",)
    search_fields = ("name", "description", "user__username")
    ordering = ("user", "name")
    inlines = [InvoiceTemplateItemInline]


@admin.register(InvoiceTemplateItem)
class InvoiceTemplateItemAdmin(admin.ModelAdmin):
    list_display = ("template", "description", "quantity", "unit_price", "order")
    search_fields = ("description", "template__name")
    ordering = ("template", "order")


# ========== TASK/TICKET ADMIN ==========

class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    fields = ("user", "content", "created_at")
    readonly_fields = ("created_at",)


class TaskTimeEntryInline(admin.TabularInline):
    model = TaskTimeEntry
    extra = 0
    fields = ("user", "hours", "description", "date")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("task_number", "title", "project", "status", "priority", "assignee", "due_date", "created_at")
    list_filter = ("status", "priority", "project", "assignee", "organization")
    search_fields = ("title", "description", "task_number", "project__name")
    ordering = ("-created_at",)
    inlines = [TaskCommentInline, TaskTimeEntryInline]
    readonly_fields = ("task_number", "created_at", "updated_at", "completed_at")
    filter_horizontal = ("labels",)

    fieldsets = (
        ("Basic Information", {
            "fields": ("title", "description", "project", "organization", "task_number")
        }),
        ("Status & Priority", {
            "fields": ("status", "priority", "assignee")
        }),
        ("Hierarchy", {
            "fields": ("parent_task", "milestone")
        }),
        ("Time Tracking", {
            "fields": ("estimated_hours", "actual_hours", "start_date", "due_date")
        }),
        ("Labels & Classification", {
            "fields": ("labels",)
        }),
        ("Metadata", {
            "fields": ("created_by", "created_at", "updated_at", "completed_at"),
            "classes": ("collapse",)
        }),
    )


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ("task", "user", "content_preview", "created_at")
    list_filter = ("user", "created_at")
    search_fields = ("content", "task__title", "user__username")
    ordering = ("-created_at",)

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "Content"


@admin.register(TaskTimeEntry)
class TaskTimeEntryAdmin(admin.ModelAdmin):
    list_display = ("task", "user", "hours", "date", "created_at")
    list_filter = ("user", "date")
    search_fields = ("task__title", "description", "user__username")
    ordering = ("-date", "-created_at")


@admin.register(TaskActivity)
class TaskActivityAdmin(admin.ModelAdmin):
    list_display = ("task", "activity_type", "user", "description", "created_at")
    list_filter = ("activity_type", "user", "created_at")
    search_fields = ("task__title", "description", "user__username")
    ordering = ("-created_at",)
