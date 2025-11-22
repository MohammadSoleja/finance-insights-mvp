#!/usr/bin/env python
"""Check testuser's invoice permissions"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'financeinsights.settings')
django.setup()

from django.contrib.auth.models import User
from app_core.models import OrganizationMember

testuser = User.objects.get(username='testuser')
member = OrganizationMember.objects.filter(user=testuser, is_active=True).first()

print("=" * 60)
print("TESTUSER INVOICE PERMISSIONS")
print("=" * 60)
print(f"\nUser: {testuser.username}")
print(f"Organization: {member.organization.name}")
print(f"Role: {member.role.name}")
print(f"\n{'Permission':<30} {'Allowed':<10}")
print("-" * 40)
print(f"{'can_view_invoices':<30} {'✅ YES' if member.role.can_view_invoices else '❌ NO'}")
print(f"{'can_create_invoices':<30} {'✅ YES' if member.role.can_create_invoices else '❌ NO'}")
print(f"{'can_edit_invoices':<30} {'✅ YES' if member.role.can_edit_invoices else '❌ NO'}")
print(f"{'can_delete_invoices':<30} {'✅ YES' if member.role.can_delete_invoices else '❌ NO'}")
print(f"{'can_send_invoices':<30} {'✅ YES' if member.role.can_send_invoices else '❌ NO'}")
print("\n" + "=" * 60)

