# app_core/invoicing.py
"""
Helper functions for invoice management
"""
from decimal import Decimal
from datetime import date, timedelta
from django.db.models import Sum, Q
from .models import Invoice, InvoiceItem, InvoicePayment, Client, InvoiceTemplate
import uuid


def generate_invoice_number(user):
    """
    Generate a unique invoice number in format INV-YYYY-NNNN
    """
    today = date.today()
    year = today.year

    # Find the last invoice number for this year
    last_invoice = Invoice.objects.filter(
        user=user,
        invoice_number__startswith=f"INV-{year}-"
    ).order_by('-invoice_number').first()

    if last_invoice:
        try:
            last_num = int(last_invoice.invoice_number.split('-')[-1])
            next_num = last_num + 1
        except (ValueError, IndexError):
            next_num = 1
    else:
        next_num = 1

    return f"INV-{year}-{next_num:04d}"


def calculate_invoice_totals(invoice):
    """
    Recalculate invoice subtotal, tax, and total from line items
    """
    items = invoice.items.all()
    invoice.subtotal = sum(item.amount for item in items) or Decimal('0.00')
    invoice.tax_amount = (invoice.subtotal * invoice.tax_rate / 100).quantize(Decimal('0.01'))
    invoice.total = invoice.subtotal + invoice.tax_amount - invoice.discount
    invoice.save()
    return invoice


def update_invoice_status(invoice):
    """
    Update invoice status based on due date and payment status
    """
    if invoice.status == Invoice.STATUS_CANCELLED:
        return invoice

    # Calculate total paid
    payments = invoice.payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    invoice.paid_amount = payments

    # Determine status
    if payments >= invoice.total:
        invoice.status = Invoice.STATUS_PAID
        if not invoice.paid_date:
            invoice.paid_date = date.today()
    elif payments > 0:
        invoice.status = Invoice.STATUS_PARTIALLY_PAID
        invoice.paid_date = None
    elif invoice.status == Invoice.STATUS_DRAFT:
        pass  # Keep as draft
    elif invoice.due_date < date.today():
        invoice.status = Invoice.STATUS_OVERDUE
    elif invoice.sent_date:
        invoice.status = Invoice.STATUS_SENT

    invoice.save()
    return invoice


def create_invoice_from_template(template, client, user, invoice_date=None, due_date=None):
    """
    Create a new invoice from a template
    """
    if not invoice_date:
        invoice_date = date.today()

    if not due_date:
        # Default to 30 days from invoice date
        due_date = invoice_date + timedelta(days=30)

    invoice = Invoice.objects.create(
        user=user,
        client=client,
        invoice_number=generate_invoice_number(user),
        invoice_date=invoice_date,
        due_date=due_date,
        status=Invoice.STATUS_DRAFT,
        tax_rate=template.default_tax_rate,
        notes=template.default_notes,
        terms=template.default_terms,
        currency=client.currency,
    )

    # Copy template items to invoice
    for template_item in template.items.all():
        InvoiceItem.objects.create(
            invoice=invoice,
            description=template_item.description,
            quantity=template_item.quantity,
            unit_price=template_item.unit_price,
            amount=template_item.quantity * template_item.unit_price,
            order=template_item.order,
        )

    # Calculate totals
    calculate_invoice_totals(invoice)

    return invoice


def record_payment(invoice, amount, payment_date, payment_method, reference="", notes="", transaction=None):
    """
    Record a payment for an invoice
    """
    payment = InvoicePayment.objects.create(
        invoice=invoice,
        transaction=transaction,
        amount=amount,
        payment_date=payment_date,
        payment_method=payment_method,
        reference=reference,
        notes=notes,
    )

    # Update invoice status
    update_invoice_status(invoice)

    return payment


def get_invoice_statistics(user):
    """
    Get invoice statistics for a user
    """
    invoices = Invoice.objects.filter(user=user)

    total = invoices.aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    paid = invoices.filter(status=Invoice.STATUS_PAID).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    outstanding = invoices.filter(
        status__in=[Invoice.STATUS_SENT, Invoice.STATUS_PARTIALLY_PAID, Invoice.STATUS_OVERDUE]
    ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    overdue = invoices.filter(status=Invoice.STATUS_OVERDUE).aggregate(total=Sum('total'))['total'] or Decimal('0.00')

    outstanding_paid_amount = invoices.filter(
        status__in=[Invoice.STATUS_SENT, Invoice.STATUS_PARTIALLY_PAID, Invoice.STATUS_OVERDUE]
    ).aggregate(total=Sum('paid_amount'))['total'] or Decimal('0.00')

    outstanding_balance = outstanding - outstanding_paid_amount

    return {
        'total_invoiced': total,
        'total_paid': paid,
        'outstanding': outstanding_balance,
        'overdue': overdue,
        'invoice_count': invoices.count(),
        'paid_count': invoices.filter(status=Invoice.STATUS_PAID).count(),
        'overdue_count': invoices.filter(status=Invoice.STATUS_OVERDUE).count(),
    }


def create_recurring_invoices(user, check_date=None):
    """
    Generate recurring invoices that are due
    This should be called periodically (e.g., daily cron job)
    """
    if not check_date:
        check_date = date.today()

    # Find recurring invoices that need to be generated
    recurring_invoices = Invoice.objects.filter(
        user=user,
        is_recurring=True,
        status=Invoice.STATUS_PAID,  # Only generate from fully paid invoices
    ).exclude(recurring_group_id__isnull=True)

    new_invoices = []

    for original_invoice in recurring_invoices:
        # Check if we need to create a new instance
        if not original_invoice.recurrence_frequency:
            continue

        # Calculate next due date
        if original_invoice.recurrence_frequency == "monthly":
            next_date = original_invoice.invoice_date + timedelta(days=30)
        elif original_invoice.recurrence_frequency == "quarterly":
            next_date = original_invoice.invoice_date + timedelta(days=90)
        elif original_invoice.recurrence_frequency == "yearly":
            next_date = original_invoice.invoice_date + timedelta(days=365)
        else:
            continue

        # Check if it's time to create the next invoice
        if next_date <= check_date:
            # Check if already created
            existing = Invoice.objects.filter(
                recurring_group_id=original_invoice.recurring_group_id,
                invoice_date=next_date
            ).exists()

            if not existing:
                # Create new invoice
                new_invoice = Invoice.objects.create(
                    user=original_invoice.user,
                    client=original_invoice.client,
                    invoice_number=generate_invoice_number(user),
                    invoice_date=next_date,
                    due_date=next_date + timedelta(days=30),
                    status=Invoice.STATUS_DRAFT,
                    subtotal=original_invoice.subtotal,
                    tax_rate=original_invoice.tax_rate,
                    tax_amount=original_invoice.tax_amount,
                    discount=original_invoice.discount,
                    total=original_invoice.total,
                    currency=original_invoice.currency,
                    notes=original_invoice.notes,
                    terms=original_invoice.terms,
                    project=original_invoice.project,
                    is_recurring=True,
                    recurrence_frequency=original_invoice.recurrence_frequency,
                    recurrence_count=original_invoice.recurrence_count,
                    recurring_group_id=original_invoice.recurring_group_id,
                )

                # Copy line items
                for item in original_invoice.items.all():
                    InvoiceItem.objects.create(
                        invoice=new_invoice,
                        description=item.description,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        amount=item.amount,
                        order=item.order,
                    )

                new_invoices.append(new_invoice)

    return new_invoices


def get_client_statistics(client):
    """
    Get statistics for a specific client
    """
    invoices = Invoice.objects.filter(client=client)

    total = invoices.aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    paid = invoices.filter(status=Invoice.STATUS_PAID).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    outstanding = invoices.filter(
        status__in=[Invoice.STATUS_SENT, Invoice.STATUS_PARTIALLY_PAID, Invoice.STATUS_OVERDUE]
    ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')

    return {
        'total_invoiced': total,
        'total_paid': paid,
        'outstanding': outstanding,
        'invoice_count': invoices.count(),
    }


CURRENCY_SYMBOLS = {
    'GBP': '£',
    'USD': '$',
    'EUR': '€',
    'JPY': '¥',
    'AUD': 'A$',
    'CAD': 'C$',
    'CHF': 'CHF',
    'INR': '₹',
}


def send_invoice_email(invoice, custom_message=None, cc_emails=None, bcc_emails=None):
    """
    Send invoice email to client with PDF attachment

    Args:
        invoice: Invoice object
        custom_message: Optional custom message to include
        cc_emails: List of CC email addresses
        bcc_emails: List of BCC email addresses

    Returns:
        dict with 'success' bool and 'message' string
    """
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.conf import settings
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT
    from io import BytesIO
    from datetime import datetime

    try:
        # Validate recipient
        if not invoice.client.email:
            return {'success': False, 'message': 'Client email address is required'}

        # Generate PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
        elements = []
        styles = getSampleStyleSheet()

        # Build PDF (same as invoice_pdf_download view)
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#2563eb'), spaceAfter=6, alignment=TA_LEFT)
        heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#374151'), spaceAfter=12, spaceBefore=12)
        normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#111827'))
        small_style = ParagraphStyle('CustomSmall', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#6b7280'))

        elements.append(Paragraph("INVOICE", title_style))
        elements.append(Paragraph(f"#{invoice.invoice_number}", heading_style))
        elements.append(Spacer(1, 0.2*inch))

        status_text = invoice.get_status_display()
        elements.append(Paragraph(f"<b>Status:</b> {status_text}", normal_style))
        elements.append(Spacer(1, 0.3*inch))

        # Bill To and Invoice Details
        info_data = [
            [Paragraph("<b>BILL TO</b>", heading_style), Paragraph("<b>INVOICE DETAILS</b>", heading_style)],
            [
                Paragraph(f"<b>{invoice.client.name}</b><br/>{invoice.client.company if invoice.client.company else ''}<br/>{invoice.client.email}<br/>{invoice.client.phone if invoice.client.phone else ''}", normal_style),
                Paragraph(f"<b>Invoice Date:</b> {invoice.invoice_date.strftime('%B %d, %Y')}<br/><b>Due Date:</b> {invoice.due_date.strftime('%B %d, %Y')}<br/><b>Payment Terms:</b> {invoice.client.payment_terms}", normal_style)
            ]
        ]

        info_table = Table(info_data, colWidths=[3*inch, 3*inch])
        info_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.4*inch))

        # Line Items
        items_data = [['Description', 'Qty', 'Unit Price', 'Amount']]
        for item in invoice.items.all():
            items_data.append([item.description, str(item.quantity), f"{invoice.currency} {item.unit_price:.2f}", f"{invoice.currency} {item.amount:.2f}"])

        items_table = Table(items_data, colWidths=[3*inch, 0.75*inch, 1.25*inch, 1.25*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#e5e7eb')),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 0.3*inch))

        # Totals
        totals_data = [['Subtotal:', f"{invoice.currency} {invoice.subtotal:.2f}"]]
        if invoice.tax_rate > 0:
            totals_data.append(['Tax ({:.1f}%):'.format(invoice.tax_rate), f"{invoice.currency} {invoice.tax_amount:.2f}"])
        if invoice.discount > 0:
            totals_data.append(['Discount:', f"-{invoice.currency} {invoice.discount:.2f}"])
        totals_data.append(['<b>Total:</b>', f"<b>{invoice.currency} {invoice.total:.2f}</b>"])
        if invoice.paid_amount > 0:
            totals_data.append(['Paid:', f"-{invoice.currency} {invoice.paid_amount:.2f}"])
            totals_data.append(['<b>Balance Due:</b>', f"<b>{invoice.currency} {invoice.balance_due:.2f}</b>"])

        totals_data_formatted = []
        for label, value in totals_data:
            totals_data_formatted.append([Paragraph(label, normal_style if '<b>' not in label else heading_style), Paragraph(value, normal_style if '<b>' not in value else heading_style)])

        totals_table = Table(totals_data_formatted, colWidths=[4.5*inch, 1.75*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LINEABOVE', (0, -2), (-1, -2), 1, colors.HexColor('#e5e7eb')),
        ]))
        elements.append(totals_table)

        if invoice.notes:
            elements.append(Spacer(1, 0.3*inch))
            elements.append(Paragraph("<b>Notes:</b>", heading_style))
            elements.append(Paragraph(invoice.notes, normal_style))

        if invoice.terms:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("<b>Payment Terms & Conditions:</b>", heading_style))
            elements.append(Paragraph(invoice.terms, normal_style))

        elements.append(Spacer(1, 0.5*inch))
        footer_text = f"<i>Thank you for your business!<br/>For questions about this invoice, please contact {invoice.user.email}</i>"
        elements.append(Paragraph(footer_text, small_style))

        doc.build(elements)
        pdf_content = buffer.getvalue()
        buffer.close()

        # Prepare email context
        context = {
            'invoice': invoice,
            'custom_message': custom_message,
            'from_email': settings.DEFAULT_FROM_EMAIL,
            'current_year': datetime.now().year,
            'view_online_url': None,  # Can be added later if we create public invoice links
        }

        # Render email templates
        html_content = render_to_string('emails/invoice_email.html', context)
        text_content = render_to_string('emails/invoice_email.txt', context)

        # Create email
        subject = f"Invoice {invoice.invoice_number} from Finance Insights"
        from_email = settings.DEFAULT_FROM_EMAIL
        to_emails = [invoice.client.email]

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=to_emails,
            cc=cc_emails or [],
            bcc=bcc_emails or []
        )

        email.attach_alternative(html_content, "text/html")
        email.attach(f'Invoice_{invoice.invoice_number}.pdf', pdf_content, 'application/pdf')

        # Send email
        email.send(fail_silently=False)

        # Update invoice status and sent date
        if invoice.status == Invoice.STATUS_DRAFT:
            invoice.status = Invoice.STATUS_SENT
        invoice.sent_date = date.today()
        invoice.save()

        return {
            'success': True,
            'message': f'Invoice sent successfully to {invoice.client.email}'
        }

    except Exception as e:
        return {
            'success': False,
            'message': f'Failed to send invoice: {str(e)}'
        }


def send_payment_reminder(invoice, custom_message=None):
    """
    Send a payment reminder email for an overdue or unpaid invoice

    Args:
        invoice: Invoice object
        custom_message: Optional custom reminder message

    Returns:
        dict with 'success' bool and 'message' string
    """
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.conf import settings
    from datetime import datetime

    try:
        if not invoice.client.email:
            return {'success': False, 'message': 'Client email address is required'}

        # Calculate days overdue
        days_overdue = (date.today() - invoice.due_date).days

        # Default message based on status
        if not custom_message:
            if days_overdue > 0:
                custom_message = f"This invoice is {days_overdue} day{'s' if days_overdue != 1 else ''} overdue. Please remit payment at your earliest convenience."
            else:
                custom_message = "This is a friendly reminder that payment is due soon. Please ensure payment is made by the due date to avoid any late fees."

        context = {
            'invoice': invoice,
            'custom_message': custom_message,
            'from_email': settings.DEFAULT_FROM_EMAIL,
            'current_year': datetime.now().year,
            'days_overdue': days_overdue if days_overdue > 0 else None,
            'is_reminder': True,
        }

        html_content = render_to_string('emails/invoice_reminder.html', context)
        text_content = render_to_string('emails/invoice_reminder.txt', context)

        subject = f"Payment Reminder: Invoice {invoice.invoice_number}"
        if days_overdue > 0:
            subject = f"OVERDUE: Invoice {invoice.invoice_number}"

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[invoice.client.email]
        )

        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        return {
            'success': True,
            'message': f'Reminder sent successfully to {invoice.client.email}'
        }

    except Exception as e:
        return {
            'success': False,
            'message': f'Failed to send reminder: {str(e)}'
        }


def save_invoice_as_template(invoice, template_name, description=""):
    """
    Save an existing invoice as a reusable template

    Args:
        invoice: Invoice object to save as template
        template_name: Name for the template
        description: Optional description

    Returns:
        InvoiceTemplate object
    """
    # Create template
    template = InvoiceTemplate.objects.create(
        user=invoice.user,
        name=template_name,
        description=description,
        default_tax_rate=invoice.tax_rate,
        default_payment_terms=invoice.client.payment_terms,
        default_notes=invoice.notes,
        default_terms=invoice.terms,
    )

    # Copy invoice items to template
    for item in invoice.items.all():
        InvoiceTemplateItem.objects.create(
            template=template,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            order=item.order,
        )

    return template


def get_user_templates(user):
    """
    Get all invoice templates for a user with item counts

    Returns:
        List of template dicts with metadata
    """
    templates = InvoiceTemplate.objects.filter(user=user).prefetch_related('items')

    result = []
    for template in templates:
        item_count = template.items.count()
        total = sum(item.quantity * item.unit_price for item in template.items.all())

        result.append({
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'item_count': item_count,
            'estimated_total': float(total),
            'default_tax_rate': float(template.default_tax_rate),
            'default_payment_terms': template.default_payment_terms,
            'created_at': template.created_at,
            'updated_at': template.updated_at,
        })

    return result


def delete_template(template):
    """Delete an invoice template"""
    template.delete()


def get_currency_symbol(currency_code):
    """Get currency symbol for a currency code"""
    return CURRENCY_SYMBOLS.get(currency_code, currency_code)

