# core/admin.py
from django.contrib import admin
from .models import (
    Transaction, Rule, Budget, Label, RecurringTransaction,
    Project, ProjectTransaction, ProjectMilestone, ProjectBudgetCategory, ProjectActivity
)

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


