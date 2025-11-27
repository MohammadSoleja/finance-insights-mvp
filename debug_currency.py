#!/usr/bin/env python
"""Debug script to check organization and currency settings"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'financeinsights.settings')
django.setup()

from app_core.models import Organization, OrganizationMember
from django.contrib.auth import get_user_model

User = get_user_model()

print("=== Currency Settings Debug ===\n")

# Check organizations
orgs = Organization.objects.all()
print(f"Total organizations: {orgs.count()}")

for org in orgs:
    print(f"\nOrganization: {org.name}")
    print(f"  - ID: {org.id}")
    print(f"  - Slug: {org.slug}")
    print(f"  - Owner: {org.owner.username}")

    # Check if preferred_currency field exists
    if hasattr(org, 'preferred_currency'):
        print(f"  - Preferred Currency: {org.preferred_currency}")
        print(f"  - Currency Symbol: {org.get_currency_symbol()}")
    else:
        print(f"  - ⚠️  NO preferred_currency field found!")

    # Check members
    members = OrganizationMember.objects.filter(organization=org)
    print(f"  - Members: {members.count()}")
    for member in members:
        print(f"    • {member.user.username} - Role: {member.role}")

print("\n=== API Key Check ===")
from django.conf import settings
api_key = settings.EXCHANGE_RATE_API_KEY
if api_key:
    print(f"✓ API Key configured: {api_key[:10]}...")
else:
    print("✗ API Key NOT configured")

print("\n=== Exchange Rates ===")
from app_core.models import ExchangeRate
rates = ExchangeRate.objects.all()[:5]
print(f"Cached exchange rates: {ExchangeRate.objects.count()}")
for rate in rates:
    print(f"  {rate.from_currency} → {rate.to_currency}: {rate.rate} ({rate.date})")

print("\n=== Test Currency Conversion ===")
try:
    from app_core.currency_service import CurrencyConverter
    rate = CurrencyConverter.get_rate('USD', 'GBP')
    print(f"✓ 1 USD = {rate} GBP")

    converted = CurrencyConverter.convert(100, 'USD', 'GBP')
    print(f"✓ $100 USD = £{converted} GBP")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n=== Done ===")

