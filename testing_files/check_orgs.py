#!/usr/bin/env python
"""
Quick diagnostic script to check organization memberships and data
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'financeinsights.settings')
django.setup()

from django.contrib.auth import get_user_model
from app_core.models import Organization, OrganizationMember, Transaction, Project, Invoice

User = get_user_model()

print("=" * 60)
print("ORGANIZATION DIAGNOSTIC")
print("=" * 60)

# Check testuser
try:
    testuser = User.objects.get(username='testuser')
    print("\n📊 TESTUSER'S ORGANIZATIONS:")
    memberships = OrganizationMember.objects.filter(user=testuser, is_active=True)

    if memberships.exists():
        for m in memberships:
            print(f"  ✅ {m.organization.name}")
            print(f"     Role: {m.role.name}")
            print(f"     Org ID: {m.organization.id}")
            print(f"     Owner: {m.organization.owner.username}")
    else:
        print("  ❌ No organizations found!")

except User.DoesNotExist:
    print("\n❌ testuser doesn't exist yet")

print("\n" + "=" * 60)

# Check msoleja
try:
    msoleja = User.objects.get(username='msoleja')
    print("📊 MSOLEJA'S ORGANIZATIONS:")

    memberships = OrganizationMember.objects.filter(user=msoleja, is_active=True)

    for m in memberships:
        org = m.organization
        print(f"\n  ✅ {org.name}")
        print(f"     Role: {m.role.name}")
        print(f"     Org ID: {org.id}")
        print(f"     Plan: {org.plan}")
        print(f"     Max Users: {org.max_users}")

        # Count members
        member_count = OrganizationMember.objects.filter(
            organization=org,
            is_active=True
        ).count()
        print(f"     Current Members: {member_count}")

        # List members
        print(f"     Members:")
        for member in OrganizationMember.objects.filter(organization=org, is_active=True):
            print(f"       - {member.user.username} ({member.role.name})")

        # Count data
        transactions = Transaction.objects.filter(organization=org).count()
        projects = Project.objects.filter(organization=org).count()
        invoices = Invoice.objects.filter(organization=org).count()

        print(f"     Data:")
        print(f"       - Transactions: {transactions}")
        print(f"       - Projects: {projects}")
        print(f"       - Invoices: {invoices}")

except User.DoesNotExist:
    print("  ❌ msoleja doesn't exist")

print("\n" + "=" * 60)
print("✅ Diagnostic complete!")
print("=" * 60)

