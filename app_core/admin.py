# core/admin.py
from django.contrib import admin
from .models import Transaction, Rule

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "description", "amount", "direction", "category", "account", "user_id")
    list_filter = ("direction", "category", "account", "source")
    search_fields = ("description", "category", "subcategory", "account")
    date_hierarchy = "date"

@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ("pattern", "is_regex", "category", "subcategory", "priority", "active", "user_id")
    list_filter = ("active", "is_regex")
    search_fields = ("pattern", "category", "subcategory", "notes")
    ordering = ("priority",)
from django.contrib import admin

# Register your models here.
