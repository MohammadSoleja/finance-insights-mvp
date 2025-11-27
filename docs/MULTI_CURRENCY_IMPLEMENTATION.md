# Multi-Currency Support - Implementation Guide

**Date:** November 26, 2025  
**Status:** 🔄 IN PROGRESS  
**Priority:** HIGH  

---

## 📋 Overview

Implementing **full currency conversion** with live exchange rates across the entire application. This is an organization-level feature that allows businesses to track finances in their preferred currency while supporting transactions and invoices in multiple currencies.

---

## 🎯 Requirements Summary

1. **✅ Full Conversion** - Not just symbol changes, actual currency conversion using live rates
2. **✅ Organization-Level** - Whole team uses same preferred currency
3. **✅ Database Storage** - Store preferences, exchange rates, historical data
4. **✅ 8 Currencies** - GBP, USD, EUR, JPY, AUD, CAD, CHF, INR
5. **✅ GBP Default** - New organizations default to British Pound
6. **✅ Invoice Flexibility** - User picks invoice currency, converts to org currency

---

## 🏗️ Architecture

### **1. Database Schema Changes**

#### **A. Organization Model**
```python
# app_core/models.py

class Organization(models.Model):
    # ... existing fields ...
    
    preferred_currency = models.CharField(
        max_length=3,
        default='GBP',
        choices=[
            ('GBP', 'British Pound (£)'),
            ('USD', 'US Dollar ($)'),
            ('EUR', 'Euro (€)'),
            ('JPY', 'Japanese Yen (¥)'),
            ('AUD', 'Australian Dollar (A$)'),
            ('CAD', 'Canadian Dollar (C$)'),
            ('CHF', 'Swiss Franc (CHF)'),
            ('INR', 'Indian Rupee (₹)'),
        ],
        help_text="Organization's preferred currency for displaying amounts"
    )
    
    def get_currency_symbol(self):
        symbols = {
            'GBP': '£', 'USD': '$', 'EUR': '€', 'JPY': '¥',
            'AUD': 'A$', 'CAD': 'C$', 'CHF': 'CHF ', 'INR': '₹'
        }
        return symbols.get(self.preferred_currency, '£')
```

#### **B. Transaction Model**
```python
# app_core/models.py

class Transaction(models.Model):
    # ... existing fields ...
    
    # Original amount and currency (as entered by user)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    original_currency = models.CharField(
        max_length=3, 
        default='GBP',
        help_text="Currency this transaction was originally in"
    )
    
    # Display amount (converted to org preferred currency)
    display_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Amount converted to organization's preferred currency"
    )
    exchange_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=6, 
        null=True, 
        blank=True,
        help_text="Exchange rate used for conversion"
    )
    rate_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Date when exchange rate was fetched"
    )
    
    def save(self, *args, **kwargs):
        """Auto-convert on save"""
        if self.original_currency != self.organization.preferred_currency:
            from .currency_service import CurrencyConverter
            self.display_amount = CurrencyConverter.convert_to_org_currency(
                self.amount,
                self.original_currency,
                self.organization
            )
            self.exchange_rate = CurrencyConverter.get_rate(
                self.original_currency,
                self.organization.preferred_currency,
                self.date
            )
            self.rate_date = self.date
        else:
            self.display_amount = self.amount
            self.exchange_rate = Decimal('1.00')
            self.rate_date = self.date
        
        super().save(*args, **kwargs)
    
    def get_display_amount(self):
        """Get amount in org's preferred currency"""
        return self.display_amount or self.amount
```

#### **C. Invoice Model**
```python
# app_core/models.py

class Invoice(models.Model):
    # ... existing fields ...
    
    currency = models.CharField(
        max_length=3,
        default='GBP',
        choices=[
            ('GBP', '£'), ('USD', '$'), ('EUR', '€'), ('JPY', '¥'),
            ('AUD', 'A$'), ('CAD', 'C$'), ('CHF', 'CHF'), ('INR', '₹'),
        ],
        help_text="Currency for this invoice"
    )
    
    def get_total_in_org_currency(self):
        """Convert invoice total to org's preferred currency"""
        if self.currency != self.organization.preferred_currency:
            from .currency_service import CurrencyConverter
            return CurrencyConverter.convert_to_org_currency(
                self.total,
                self.currency,
                self.organization
            )
        return self.total
    
    def get_currency_symbol(self):
        symbols = {
            'GBP': '£', 'USD': '$', 'EUR': '€', 'JPY': '¥',
            'AUD': 'A$', 'CAD': 'C$', 'CHF': 'CHF ', 'INR': '₹'
        }
        return symbols.get(self.currency, '£')
```

#### **D. Exchange Rate Model (NEW)**
```python
# app_core/models.py

class ExchangeRate(models.Model):
    """Cache exchange rates from API"""
    from_currency = models.CharField(max_length=3)
    to_currency = models.CharField(max_length=3)
    rate = models.DecimalField(max_digits=10, decimal_places=6)
    date = models.DateField()
    source = models.CharField(max_length=50, default='exchangerate-api.com')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['from_currency', 'to_currency', 'date']
        indexes = [
            models.Index(fields=['from_currency', 'to_currency', 'date']),
            models.Index(fields=['date']),
        ]
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.from_currency} → {self.to_currency}: {self.rate} ({self.date})"
```

---

### **2. Currency Conversion Service**

```python
# app_core/currency_service.py

import requests
from decimal import Decimal
from datetime import date, timedelta
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class CurrencyConverter:
    """Service for currency conversion using ExchangeRate-API"""
    
    API_KEY = settings.EXCHANGE_RATE_API_KEY  # Add to settings.py
    BASE_URL = 'https://v6.exchangerate-api.com/v6'
    CACHE_TTL = 3600 * 24  # 24 hours
    
    # Currency symbols
    SYMBOLS = {
        'GBP': '£',
        'USD': '$',
        'EUR': '€',
        'JPY': '¥',
        'AUD': 'A$',
        'CAD': 'C$',
        'CHF': 'CHF ',
        'INR': '₹',
    }
    
    @classmethod
    def get_symbol(cls, currency_code):
        """Get currency symbol"""
        return cls.SYMBOLS.get(currency_code, '')
    
    @classmethod
    def get_rate(cls, from_currency, to_currency, rate_date=None):
        """
        Get exchange rate between two currencies
        
        Args:
            from_currency: Source currency code (e.g., 'USD')
            to_currency: Target currency code (e.g., 'GBP')
            rate_date: Date for historical rate (defaults to today)
        
        Returns:
            Decimal: Exchange rate
        """
        # Same currency = 1.0
        if from_currency == to_currency:
            return Decimal('1.00')
        
        if rate_date is None:
            rate_date = date.today()
        
        # Try cache first
        cache_key = f'exrate_{from_currency}_{to_currency}_{rate_date}'
        cached_rate = cache.get(cache_key)
        if cached_rate:
            logger.debug(f"Cache hit for {cache_key}")
            return Decimal(cached_rate)
        
        # Try database
        from .models import ExchangeRate
        db_rate = ExchangeRate.objects.filter(
            from_currency=from_currency,
            to_currency=to_currency,
            date=rate_date
        ).first()
        
        if db_rate:
            logger.debug(f"Database hit for {from_currency} → {to_currency} on {rate_date}")
            cache.set(cache_key, str(db_rate.rate), cls.CACHE_TTL)
            return db_rate.rate
        
        # Fetch from API (only for today or recent dates)
        if rate_date >= date.today() - timedelta(days=7):
            try:
                rate = cls._fetch_from_api(from_currency, to_currency)
                
                # Save to database
                ExchangeRate.objects.create(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    rate=rate,
                    date=rate_date
                )
                
                # Cache it
                cache.set(cache_key, str(rate), cls.CACHE_TTL)
                logger.info(f"Fetched from API: {from_currency} → {to_currency} = {rate}")
                return rate
                
            except Exception as e:
                logger.error(f"API fetch failed: {e}")
                # Fall through to fallback
        
        # Fallback: Use most recent available rate
        recent_rate = ExchangeRate.objects.filter(
            from_currency=from_currency,
            to_currency=to_currency
        ).order_by('-date').first()
        
        if recent_rate:
            logger.warning(f"Using fallback rate from {recent_rate.date}")
            cache.set(cache_key, str(recent_rate.rate), cls.CACHE_TTL)
            return recent_rate.rate
        
        # Last resort: Estimate using USD as intermediary
        logger.warning(f"No rate found for {from_currency} → {to_currency}, using USD intermediary")
        try:
            usd_from = cls.get_rate(from_currency, 'USD', rate_date)
            usd_to = cls.get_rate('USD', to_currency, rate_date)
            return usd_from * usd_to
        except:
            # Ultimate fallback: return 1.0 and log error
            logger.error(f"Could not determine rate for {from_currency} → {to_currency}")
            return Decimal('1.00')
    
    @classmethod
    def _fetch_from_api(cls, from_currency, to_currency):
        """Fetch rate from ExchangeRate-API"""
        url = f'{cls.BASE_URL}/{cls.API_KEY}/latest/{from_currency}'
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data['result'] != 'success':
            raise Exception(f"API error: {data.get('error-type', 'Unknown error')}")
        
        rate = data['conversion_rates'].get(to_currency)
        if not rate:
            raise Exception(f"Rate not found for {to_currency}")
        
        return Decimal(str(rate))
    
    @classmethod
    def convert(cls, amount, from_currency, to_currency, rate_date=None):
        """
        Convert amount between currencies
        
        Args:
            amount: Amount to convert (Decimal or float)
            from_currency: Source currency
            to_currency: Target currency
            rate_date: Date for rate (defaults to today)
        
        Returns:
            Decimal: Converted amount (2 decimal places)
        """
        if from_currency == to_currency:
            return Decimal(str(amount))
        
        rate = cls.get_rate(from_currency, to_currency, rate_date)
        converted = (Decimal(str(amount)) * rate).quantize(Decimal('0.01'))
        
        logger.debug(f"Converted {amount} {from_currency} → {converted} {to_currency} (rate: {rate})")
        return converted
    
    @classmethod
    def convert_to_org_currency(cls, amount, from_currency, organization):
        """Convert to organization's preferred currency"""
        return cls.convert(
            amount,
            from_currency,
            organization.preferred_currency
        )
    
    @classmethod
    def refresh_rates(cls):
        """
        Refresh today's exchange rates for all currency pairs
        Called by daily cron job
        """
        from .models import ExchangeRate
        from itertools import combinations
        
        currencies = ['GBP', 'USD', 'EUR', 'JPY', 'AUD', 'CAD', 'CHF', 'INR']
        today = date.today()
        
        refreshed = 0
        errors = 0
        
        for from_curr, to_curr in combinations(currencies, 2):
            try:
                # Forward rate
                rate = cls._fetch_from_api(from_curr, to_curr)
                ExchangeRate.objects.update_or_create(
                    from_currency=from_curr,
                    to_currency=to_curr,
                    date=today,
                    defaults={'rate': rate}
                )
                
                # Reverse rate
                reverse_rate = Decimal('1.00') / rate
                ExchangeRate.objects.update_or_create(
                    from_currency=to_curr,
                    to_currency=from_curr,
                    date=today,
                    defaults={'rate': reverse_rate}
                )
                
                refreshed += 2
                
            except Exception as e:
                logger.error(f"Failed to refresh {from_curr} ↔ {to_curr}: {e}")
                errors += 1
        
        logger.info(f"Refreshed {refreshed} exchange rates with {errors} errors")
        return refreshed, errors
```

---

### **3. Settings Configuration**

```python
# settings.py

# Exchange Rate API
EXCHANGE_RATE_API_KEY = env('EXCHANGE_RATE_API_KEY', default='YOUR_API_KEY_HERE')

# Register at: https://www.exchangerate-api.com/
# Free tier: 1,500 requests/month
```

**Get API Key:**
1. Go to https://www.exchangerate-api.com/
2. Click "Get Free Key"
3. Enter email
4. Verify email
5. Copy API key
6. Add to `.env` file: `EXCHANGE_RATE_API_KEY=your_key_here`

---

### **4. Management Commands**

```python
# app_core/management/commands/refresh_exchange_rates.py

from django.core.management.base import BaseCommand
from app_core.currency_service import CurrencyConverter

class Command(BaseCommand):
    help = 'Refresh today\'s exchange rates'
    
    def handle(self, *args, **options):
        self.stdout.write('Refreshing exchange rates...')
        
        refreshed, errors = CurrencyConverter.refresh_rates()
        
        if errors == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully refreshed {refreshed} exchange rates'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'Refreshed {refreshed} rates with {errors} errors'
                )
            )
```

**Cron setup (run daily):**
```bash
# crontab -e
0 1 * * * cd /path/to/project && python manage.py refresh_exchange_rates
```

---

### **5. Migrations**

**Step 1: Add currency fields**
```bash
python manage.py makemigrations --name add_currency_support
```

**Step 2: Backfill existing data**
```python
# migrations/0XXX_backfill_currency.py

from django.db import migrations
from decimal import Decimal

def backfill_currency_data(apps, schema_editor):
    Transaction = apps.get_model('app_core', 'Transaction')
    Invoice = apps.get_model('app_core', 'Invoice')
    
    # Backfill transactions (assume GBP)
    Transaction.objects.update(
        original_currency='GBP',
        display_amount=models.F('amount'),
        exchange_rate=Decimal('1.00'),
        rate_date=models.F('date')
    )
    
    # Backfill invoices (assume GBP)
    Invoice.objects.update(currency='GBP')

class Migration(migrations.Migration):
    dependencies = [
        ('app_core', '0XXX_add_currency_support'),
    ]
    
    operations = [
        migrations.RunPython(backfill_currency_data),
    ]
```

---

### **6. Template Tags**

```python
# app_core/templatetags/currency_tags.py

from django import template
from django.utils.safestring import mark_safe
from app_core.currency_service import CurrencyConverter

register = template.Library()

@register.simple_tag(takes_context=True)
def currency_amount(context, amount, original_currency=None):
    """
    Display amount in organization's preferred currency
    
    Usage:
        {% currency_amount transaction.amount transaction.original_currency %}
    """
    request = context.get('request')
    if not request or not hasattr(request, 'organization'):
        symbol = CurrencyConverter.get_symbol('GBP')
        return mark_safe(f'{symbol}{amount:,.2f}')
    
    org = request.organization
    org_symbol = org.get_currency_symbol()
    
    if original_currency and original_currency != org.preferred_currency:
        # Convert and show both
        converted = CurrencyConverter.convert_to_org_currency(
            amount, original_currency, org
        )
        orig_symbol = CurrencyConverter.get_symbol(original_currency)
        
        return mark_safe(
            f'{orig_symbol}{amount:,.2f} '
            f'<span class="text-muted small">({org_symbol}{converted:,.2f})</span>'
        )
    else:
        # Just show in org currency
        return mark_safe(f'{org_symbol}{amount:,.2f}')

@register.simple_tag(takes_context=True)
def currency_symbol(context):
    """Get organization's currency symbol"""
    request = context.get('request')
    if request and hasattr(request, 'organization'):
        return request.organization.get_currency_symbol()
    return '£'

@register.filter
def convert_currency(amount, to_currency):
    """Convert amount to specified currency"""
    # Assumes amount is in GBP
    return CurrencyConverter.convert(amount, 'GBP', to_currency)
```

---

## 📝 Implementation Checklist

### **Phase 1: Database & Models** (Day 1)
- [ ] Add `preferred_currency` to Organization model
- [ ] Add currency fields to Transaction model
- [ ] Add `currency` field to Invoice model
- [ ] Create ExchangeRate model
- [ ] Create migrations
- [ ] Run migrations
- [ ] Backfill existing data

### **Phase 2: Currency Service** (Day 2)
- [ ] Create `currency_service.py`
- [ ] Implement `CurrencyConverter` class
- [ ] Get ExchangeRate-API key
- [ ] Test API integration
- [ ] Add rate caching (memory + database)
- [ ] Create management command for rate refresh
- [ ] Set up daily cron job

### **Phase 3: UI - Settings** (Day 3)
- [ ] Add currency selector to organization settings page
- [ ] Add save endpoint for currency preference
- [ ] Test currency switching
- [ ] Add validation

### **Phase 4: UI - Invoices** (Day 3-4)
- [ ] Add currency dropdown to invoice form
- [ ] Update invoice display to show currency
- [ ] Show converted amounts in reports
- [ ] Update invoice PDF generation

### **Phase 5: UI - Transactions** (Day 4)
- [ ] Add currency field to transaction form (optional)
- [ ] Update transaction list to show converted amounts
- [ ] Update dashboard KPIs
- [ ] Update charts

### **Phase 6: UI - Global** (Day 5)
- [ ] Create currency template tags
- [ ] Update all amount displays across site
- [ ] Update budgets to use org currency
- [ ] Update projects to use org currency
- [ ] Update reports (P&L, Cash Flow, etc.)

### **Phase 7: Testing** (Day 6)
- [ ] Test currency switching
- [ ] Test invoice creation in different currencies
- [ ] Test transaction conversion
- [ ] Test reports with mixed currencies
- [ ] Test API failure scenarios
- [ ] Test caching

### **Phase 8: Documentation** (Day 6-7)
- [ ] User guide for currency settings
- [ ] Developer documentation
- [ ] API documentation
- [ ] Update FEATURE_ROADMAP.md

---

## 🧪 Testing Scenarios

### **Test 1: Organization Currency Change**
1. Create org with GBP
2. Add transactions in GBP
3. Change org currency to USD
4. Verify all amounts convert to USD
5. Check historical rates used

### **Test 2: Multi-Currency Invoices**
1. Create invoice in USD
2. Verify shows USD on invoice
3. View in reports
4. Verify converts to org currency (GBP)
5. Check conversion note displayed

### **Test 3: API Failure Handling**
1. Disable internet
2. Try to convert currency
3. Verify uses cached rates
4. Verify fallback to database rates
5. Verify graceful error handling

### **Test 4: Historical Rates**
1. Create transaction 6 months ago in EUR
2. Verify uses historical rate from that date
3. Change org currency
4. Verify historical conversion accurate

---

## 📊 Expected Results

### **Dashboard Before (all GBP)**
```
Total Income: £10,000
Total Expenses: £7,500
Net: £2,500
```

### **Dashboard After (org = USD, mixed currencies)**
```
Total Income: $12,700 (£10,000 @ 1.27)
Total Expenses: $9,525 (£7,500 @ 1.27)
Net: $3,175
```

### **Invoice Display**
```
Invoice #INV-001
Client: Acme Corp
Currency: USD

Items:
- Consulting: $1,000
- Development: $2,000
Total: $3,000

Converted to GBP: £2,362 (rate 1.27 on Nov 26, 2025)
```

---

## 🚀 Go-Live Plan

1. **Pre-deployment:**
   - Get API key
   - Test on staging
   - Seed exchange rates for last 30 days
   - Prepare rollback plan

2. **Deployment:**
   - Run migrations
   - Backfill existing data
   - Deploy code
   - Test in production

3. **Post-deployment:**
   - Monitor API usage
   - Check logs for errors
   - Verify conversions accurate
   - Set up daily rate refresh

4. **Announce:**
   - Email users about new feature
   - Update help docs
   - Create tutorial video

---

## 📈 Success Metrics

- ✅ All amounts display correctly in org currency
- ✅ Exchange rates update daily
- ✅ API usage < 1,500 requests/month (free tier)
- ✅ Conversion accuracy within 0.1%
- ✅ No user-reported bugs in first week
- ✅ 90%+ cache hit rate
- ✅ <100ms average conversion time

---

## 🎯 Timeline

**Total: 6-7 days**

- Days 1-2: Database + Service Layer
- Days 3-5: UI Updates
- Day 6: Testing
- Day 7: Documentation + Deployment

---

**Status:** Ready to implement! Let me know when you'd like to start. 🚀

