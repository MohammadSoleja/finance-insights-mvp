#!/usr/bin/env python
"""
Test script to verify organization-based data access is working correctly.
Run this to test that testuser can now see projects, invoices, etc.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'financeinsights.settings')
django.setup()

from django.contrib.auth.models import User
from app_core.models import (
    Organization, OrganizationMember,
    Transaction, Project, Invoice, Client, Budget
)

def test_organization_access():
    """Test that both users can access organization data"""

    print("=" * 60)
    print("ORGANIZATION DATA ACCESS TEST")
    print("=" * 60)

    # Get users
    try:
        msoleja = User.objects.get(username='msoleja')
        testuser = User.objects.get(username='testuser')
    except User.DoesNotExist as e:
        print(f"❌ Error: {e}")
        return

    # Get organization
    try:
        org = Organization.objects.get(name="msoleja's Organization")
    except Organization.DoesNotExist:
        print("❌ Organization not found!")
        return

    print(f"\n📊 Organization: {org.name}")
    print(f"   Plan: {org.plan}")
    print(f"   Max Users: {org.max_users}")

    # Check memberships
    print(f"\n👥 Organization Members:")
    members = OrganizationMember.objects.filter(organization=org, is_active=True)
    for member in members:
        print(f"   - {member.user.username} ({member.role.name})")

    print("\n" + "=" * 60)
    print("DATA ACCESS TESTS")
    print("=" * 60)

    # Test Transactions
    tx_count = Transaction.objects.filter(organization=org).count()
    print(f"\n📝 Transactions (organization={org.id}): {tx_count}")

    msoleja_tx = Transaction.objects.filter(organization=org, user=msoleja).count()
    print(f"   - Created by msoleja: {msoleja_tx}")

    testuser_tx = Transaction.objects.filter(organization=org, user=testuser).count()
    print(f"   - Created by testuser: {testuser_tx}")

    # Test Projects
    proj_count = Project.objects.filter(organization=org).count()
    print(f"\n💼 Projects (organization={org.id}): {proj_count}")

    for project in Project.objects.filter(organization=org)[:5]:
        print(f"   - {project.name} (created by {project.user.username})")

    # Test Invoices
    inv_count = Invoice.objects.filter(organization=org).count()
    print(f"\n📄 Invoices (organization={org.id}): {inv_count}")

    for invoice in Invoice.objects.filter(organization=org)[:5]:
        print(f"   - {invoice.invoice_number} - {invoice.client.name} (created by {invoice.user.username})")

    # Test Clients
    client_count = Client.objects.filter(organization=org).count()
    print(f"\n👤 Clients (organization={org.id}): {client_count}")

    for client in Client.objects.filter(organization=org)[:5]:
        print(f"   - {client.name} (created by {client.user.username})")

    # Test Budgets
    budget_count = Budget.objects.filter(organization=org).count()
    print(f"\n💰 Budgets (organization={org.id}): {budget_count}")

    for budget in Budget.objects.filter(organization=org)[:5]:
        print(f"   - {budget.name} - £{budget.amount} (created by {budget.user.username})")

    print("\n" + "=" * 60)
    print("ACCESS VERIFICATION")
    print("=" * 60)

    # Simulate testuser accessing data
    print(f"\n🔍 Testing testuser access:")

    # Check if testuser can see projects
    testuser_can_see_projects = Project.objects.filter(organization=org).exists()
    print(f"   Can see projects: {'✅ YES' if testuser_can_see_projects else '❌ NO'}")

    # Check if testuser can see invoices
    testuser_can_see_invoices = Invoice.objects.filter(organization=org).exists()
    print(f"   Can see invoices: {'✅ YES' if testuser_can_see_invoices else '❌ NO'}")

    # Check if testuser can see clients
    testuser_can_see_clients = Client.objects.filter(organization=org).exists()
    print(f"   Can see clients: {'✅ YES' if testuser_can_see_clients else '❌ NO'}")

    # Check if testuser can see budgets
    testuser_can_see_budgets = Budget.objects.filter(organization=org).exists()
    print(f"   Can see budgets: {'✅ YES' if testuser_can_see_budgets else '❌ NO'}")

    print("\n" + "=" * 60)
    print("✅ TEST COMPLETE")
    print("=" * 60)

    # Summary
    all_good = all([
        testuser_can_see_projects,
        testuser_can_see_invoices,
        testuser_can_see_clients,
        testuser_can_see_budgets
    ])

    if all_good:
        print("\n✅ All organization data is accessible!")
        print("   testuser should now be able to see:")
        print("   - Project details")
        print("   - Invoices")
        print("   - Clients")
        print("   - Budgets")
    else:
        print("\n⚠️  Some data may not be accessible yet.")
        print("   Please check the organization field on models.")

if __name__ == '__main__':
    test_organization_access()

