# app_core/templatetags/currency_tags.py
"""
Template tags for currency display and conversion.
Usage: {% load currency_tags %}
"""

from django import template
from django.utils.safestring import mark_safe
from decimal import Decimal

register = template.Library()


@register.simple_tag(takes_context=True)
def currency_symbol(context):
    """
    Get organization's currency symbol.
    Usage: {% currency_symbol %}
    """
    request = context.get('request')
    if request and hasattr(request, 'organization') and request.organization:
        return request.organization.get_currency_symbol()
    return '£'


@register.simple_tag(takes_context=True)
def org_currency(context):
    """
    Get organization's currency code.
    Usage: {% org_currency %}
    """
    request = context.get('request')
    if request and hasattr(request, 'organization') and request.organization:
        return request.organization.preferred_currency
    return 'GBP'


@register.filter
def currency_format(value, currency_code='GBP'):
    """
    Format a value with currency symbol.
    Usage: {{ amount|currency_format:currency_code }}
    """
    from app_core.currency_service import CurrencyConverter

    try:
        amount = Decimal(str(value))
        symbol = CurrencyConverter.get_symbol(currency_code)
        return mark_safe(f'{symbol}{amount:,.2f}')
    except (ValueError, TypeError, Exception):
        symbol = CurrencyConverter.get_symbol(currency_code)
        return mark_safe(f'{symbol}0.00')


@register.simple_tag(takes_context=True)
def currency_amount(context, amount, original_currency=None):
    """
    Display amount in organization's preferred currency.
    Shows conversion if original currency differs from org currency.

    Usage: {% currency_amount transaction.amount transaction.original_currency %}
    """
    from app_core.currency_service import CurrencyConverter

    request = context.get('request')
    if not request or not hasattr(request, 'organization') or not request.organization:
        # No org context, just format in GBP
        symbol = CurrencyConverter.get_symbol('GBP')
        try:
            amt = Decimal(str(amount))
            return mark_safe(f'{symbol}{amt:,.2f}')
        except:
            return mark_safe(f'{symbol}0.00')

    org = request.organization
    org_currency = org.preferred_currency
    org_symbol = org.get_currency_symbol()

    # If no original currency specified, assume it's in org currency
    if not original_currency:
        original_currency = org_currency

    try:
        amt = Decimal(str(amount))

        # Same currency - just display
        if original_currency == org_currency:
            return mark_safe(f'{org_symbol}{amt:,.2f}')

        # Different currency - show original and converted
        orig_symbol = CurrencyConverter.get_symbol(original_currency)
        converted = CurrencyConverter.convert(amt, original_currency, org_currency)

        return mark_safe(
            f'{orig_symbol}{amt:,.2f} '
            f'<span class="text-muted small">({org_symbol}{converted:,.2f})</span>'
        )
    except Exception as e:
        # Fallback to just showing the amount
        return mark_safe(f'{org_symbol}{amount:,.2f}')


@register.filter
def convert_currency(amount, to_currency):
    """
    Convert amount to specified currency (assumes from GBP).
    Usage: {{ amount|convert_currency:'USD' }}
    """
    from app_core.currency_service import CurrencyConverter

    try:
        amt = Decimal(str(amount))
        converted = CurrencyConverter.convert(amt, 'GBP', to_currency)
        symbol = CurrencyConverter.get_symbol(to_currency)
        return mark_safe(f'{symbol}{converted:,.2f}')
    except:
        symbol = CurrencyConverter.get_symbol(to_currency)
        return mark_safe(f'{symbol}0.00')


@register.simple_tag(takes_context=True)
def display_amount_in_org_currency(context, amount, from_currency='GBP'):
    """
    Display amount converted to org's currency.
    Usage: {% display_amount_in_org_currency invoice.total invoice.currency %}
    """
    from app_core.currency_service import CurrencyConverter

    request = context.get('request')
    if not request or not hasattr(request, 'organization') or not request.organization:
        symbol = CurrencyConverter.get_symbol(from_currency)
        try:
            amt = Decimal(str(amount))
            return mark_safe(f'{symbol}{amt:,.2f}')
        except:
            return mark_safe(f'{symbol}0.00')

    org = request.organization
    org_currency = org.preferred_currency
    org_symbol = org.get_currency_symbol()

    try:
        amt = Decimal(str(amount))

        if from_currency == org_currency:
            return mark_safe(f'{org_symbol}{amt:,.2f}')

        converted = CurrencyConverter.convert(amt, from_currency, org_currency)
        return mark_safe(f'{org_symbol}{converted:,.2f}')
    except:
        return mark_safe(f'{org_symbol}{amount:,.2f}')


@register.filter
def abs_value(value):
    """
    Return the absolute value of a number.
    Usage: {{ value|abs_value }}
    """
    try:
        return abs(value)
    except (ValueError, TypeError):
        return value


