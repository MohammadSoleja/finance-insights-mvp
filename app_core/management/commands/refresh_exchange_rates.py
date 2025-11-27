# app_core/management/commands/refresh_exchange_rates.py
"""
Management command to refresh exchange rates from API.
Run daily via cron: python manage.py refresh_exchange_rates
"""

from django.core.management.base import BaseCommand
from app_core.currency_service import CurrencyConverter


class Command(BaseCommand):
    help = 'Refresh today\'s exchange rates from ExchangeRate-API'

    def handle(self, *args, **options):
        self.stdout.write('Refreshing exchange rates...')

        try:
            refreshed, errors = CurrencyConverter.refresh_rates()

            if errors == 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Successfully refreshed {refreshed} exchange rates'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠ Refreshed {refreshed} rates with {errors} errors (check logs)'
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'✗ Failed to refresh exchange rates: {e}'
                )
            )
            raise

