# app_core/currency_service.py
"""
Currency Conversion Service
Handles exchange rate fetching, caching, and currency conversion using ExchangeRate-API.
"""

import requests
from decimal import Decimal
from datetime import date, timedelta
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class CurrencyConverter:
    """Service for currency conversion using ExchangeRate-API"""

    API_KEY = getattr(settings, 'EXCHANGE_RATE_API_KEY', None)
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
            if from_currency != 'USD' and to_currency != 'USD':
                usd_from = cls.get_rate(from_currency, 'USD', rate_date)
                usd_to = cls.get_rate('USD', to_currency, rate_date)
                return usd_from * usd_to
        except Exception as e:
            logger.error(f"USD intermediary failed: {e}")

        # Ultimate fallback: return 1.0 and log error
        logger.error(f"Could not determine rate for {from_currency} → {to_currency}, returning 1.0")
        return Decimal('1.00')

    @classmethod
    def _fetch_from_api(cls, from_currency, to_currency):
        """Fetch rate from ExchangeRate-API"""
        if not cls.API_KEY:
            raise Exception("EXCHANGE_RATE_API_KEY not configured in settings")

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
                    defaults={'rate': reverse_rate.quantize(Decimal('0.000001'))}
                )

                refreshed += 2

            except Exception as e:
                logger.error(f"Failed to refresh {from_curr} ↔ {to_curr}: {e}")
                errors += 1

        logger.info(f"Refreshed {refreshed} exchange rates with {errors} errors")
        return refreshed, errors

