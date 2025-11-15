# app_core/recurring.py
"""
Utility functions for managing recurring transactions.
"""
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from django.utils import timezone
from .models import RecurringTransaction, Transaction


def get_next_occurrence_date(current_date, frequency):
    """
    Calculate the next occurrence date based on frequency.
    """
    if frequency == RecurringTransaction.FREQUENCY_DAILY:
        return current_date + timedelta(days=1)
    elif frequency == RecurringTransaction.FREQUENCY_WEEKLY:
        return current_date + timedelta(weeks=1)
    elif frequency == RecurringTransaction.FREQUENCY_MONTHLY:
        return current_date + relativedelta(months=1)
    elif frequency == RecurringTransaction.FREQUENCY_YEARLY:
        return current_date + relativedelta(years=1)
    return current_date


def generate_recurring_transactions(user=None, days_ahead=30):
    """
    Generate transactions from recurring templates.

    Args:
        user: Optional user to limit generation to specific user
        days_ahead: How many days in the future to generate (default 30)

    Returns:
        Number of transactions created
    """
    today = timezone.now().date()
    end_generation_date = today + timedelta(days=days_ahead)

    # Get active recurring transactions
    query = RecurringTransaction.objects.filter(active=True)
    if user:
        query = query.filter(user=user)

    recurring_txs = query.all()
    transactions_created = 0

    for recurring_tx in recurring_txs:
        # Determine the next date to generate from
        if recurring_tx.last_generated_date:
            next_date = get_next_occurrence_date(recurring_tx.last_generated_date, recurring_tx.frequency)
        else:
            next_date = recurring_tx.start_date

        # Generate transactions up to end_generation_date or recurring end_date
        max_date = end_generation_date
        if recurring_tx.end_date and recurring_tx.end_date < max_date:
            max_date = recurring_tx.end_date

        while next_date <= max_date:
            # Check if transaction already exists for this date
            existing = Transaction.objects.filter(
                user=recurring_tx.user,
                date=next_date,
                description=recurring_tx.description,
                amount=recurring_tx.amount,
                direction=recurring_tx.direction,
                source='recurring'
            ).exists()

            if not existing:
                # Create the transaction
                Transaction.objects.create(
                    user=recurring_tx.user,
                    date=next_date,
                    description=recurring_tx.description,
                    amount=recurring_tx.amount,
                    direction=recurring_tx.direction,
                    label=recurring_tx.label,
                    category=recurring_tx.category or (recurring_tx.label.name if recurring_tx.label else ''),
                    subcategory=recurring_tx.subcategory,
                    account=recurring_tx.account,
                    source='recurring'
                )
                transactions_created += 1

            # Update last_generated_date
            recurring_tx.last_generated_date = next_date
            recurring_tx.save(update_fields=['last_generated_date', 'updated_at'])

            # Move to next occurrence
            next_date = get_next_occurrence_date(next_date, recurring_tx.frequency)

        # Check if we should deactivate (past end_date)
        if recurring_tx.end_date and recurring_tx.end_date < today:
            recurring_tx.active = False
            recurring_tx.save(update_fields=['active', 'updated_at'])

    return transactions_created


def preview_recurring_occurrences(recurring_tx, num_occurrences=12):
    """
    Preview the next N occurrences of a recurring transaction.

    Args:
        recurring_tx: RecurringTransaction instance
        num_occurrences: Number of future occurrences to show

    Returns:
        List of dates
    """
    if recurring_tx.last_generated_date:
        current_date = get_next_occurrence_date(recurring_tx.last_generated_date, recurring_tx.frequency)
    else:
        current_date = recurring_tx.start_date

    occurrences = []
    for _ in range(num_occurrences):
        if recurring_tx.end_date and current_date > recurring_tx.end_date:
            break
        occurrences.append(current_date)
        current_date = get_next_occurrence_date(current_date, recurring_tx.frequency)

    return occurrences

