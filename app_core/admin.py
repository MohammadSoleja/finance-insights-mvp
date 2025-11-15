# core/admin.py
from django.contrib import admin
from .models import Transaction, Rule, Budget, Label, RecurringTransaction

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

