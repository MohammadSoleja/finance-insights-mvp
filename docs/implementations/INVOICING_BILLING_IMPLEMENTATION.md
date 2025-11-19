# Invoicing & Billing Feature Documentation

## Overview
Complete invoicing and billing system for creating professional invoices, tracking payments, and managing clients.

## Implementation Date
November 17, 2025

## Features Implemented

### 1. Client Management ✅
- **Client Directory**: Full CRUD operations for clients
- **Client Information**: Name, email, company, phone, address, tax ID
- **Payment Terms**: Configurable payment terms (Net 30, Net 60, etc.)
- **Multi-Currency Support**: Each client can have their own currency
- **Client Statistics**: Track total invoiced, paid, and outstanding amounts per client
- **Active/Inactive Status**: Soft delete clients by deactivating them

### 2. Invoice Creation & Management ✅
- **Professional Invoices**: Create detailed invoices with line items
- **Auto-Generated Invoice Numbers**: Format: INV-YYYY-NNNN (e.g., INV-2025-0001)
- **Invoice Status Tracking**:
  - Draft
  - Sent
  - Paid
  - Partially Paid
  - Overdue
  - Cancelled
- **Line Items**: Multiple line items with quantity, unit price, and amount
- **Tax Calculation**: Automatic tax calculation based on configurable rate
- **Discounts**: Apply discounts to invoices
- **Project Linkage**: Link invoices to projects for better tracking

### 3. Payment Tracking ✅
- **Record Payments**: Track partial and full payments
- **Payment Methods**: Bank transfer, card, cash, cheque, other
- **Payment History**: Full payment history for each invoice
- **Auto-Status Updates**: Invoice status automatically updates based on payments
- **Transaction Linking**: Optional linking to actual transaction records

### 4. Recurring Invoices ✅
- **Automatic Generation**: Set up recurring invoices (monthly, quarterly, yearly)
- **Recurrence Count**: Define how many times to recur
- **Recurring Groups**: Link related recurring invoices together
- **Smart Generation**: Only create new invoices when previous ones are paid

### 5. Invoice Statistics & Reports ✅
- **Dashboard Metrics**:
  - Total invoiced amount
  - Total paid amount
  - Outstanding balance
  - Overdue amount
  - Invoice counts by status
- **Client Statistics**: Per-client spending and payment history
- **Filtering**: Filter by status, client, date range, search query

### 6. Multi-Currency Support ✅
- **Currency Selection**: Support for GBP, USD, EUR, JPY, AUD, CAD, CHF, INR
- **Currency Symbols**: Proper currency symbol display
- **Per-Client Currency**: Each client can have their preferred currency

## Database Models

### Client
```python
- user (ForeignKey)
- name (CharField)
- email (EmailField)
- company (CharField, optional)
- phone (CharField, optional)
- address (TextField, optional)
- tax_id (CharField, optional)
- payment_terms (CharField, default='Net 30')
- currency (CharField, default='GBP')
- notes (TextField, optional)
- active (BooleanField, default=True)
```

### Invoice
```python
- user (ForeignKey)
- client (ForeignKey)
- invoice_number (CharField, unique, auto-generated)
- invoice_date (DateField)
- due_date (DateField)
- sent_date (DateField, optional)
- paid_date (DateField, optional)
- status (CharField: draft/sent/paid/partially_paid/overdue/cancelled)
- subtotal (DecimalField)
- tax_rate (DecimalField)
- tax_amount (DecimalField)
- discount (DecimalField)
- total (DecimalField)
- paid_amount (DecimalField)
- currency (CharField)
- notes (TextField)
- terms (TextField)
- internal_notes (TextField)
- project (ForeignKey, optional)
- is_recurring (BooleanField)
- recurrence_frequency (CharField: monthly/quarterly/yearly)
- recurrence_count (IntegerField)
- recurring_group_id (CharField)
```

### InvoiceItem
```python
- invoice (ForeignKey)
- description (CharField)
- quantity (DecimalField)
- unit_price (DecimalField)
- amount (DecimalField, auto-calculated)
- order (IntegerField)
```

### InvoicePayment
```python
- invoice (ForeignKey)
- transaction (ForeignKey, optional)
- amount (DecimalField)
- payment_date (DateField)
- payment_method (CharField: bank_transfer/card/cash/cheque/other)
- reference (CharField)
- notes (TextField)
```

### InvoiceTemplate
```python
- user (ForeignKey)
- name (CharField)
- description (TextField)
- default_tax_rate (DecimalField)
- default_payment_terms (CharField)
- default_notes (TextField)
- default_terms (TextField)
```

### InvoiceTemplateItem
```python
- template (ForeignKey)
- description (CharField)
- quantity (DecimalField)
- unit_price (DecimalField)
- order (IntegerField)
```

## API Endpoints

### Invoices
- `GET /invoices/` - List all invoices with filters
- `POST /invoices/create/` - Create new invoice
- `POST /invoices/<id>/edit/` - Edit invoice
- `POST /invoices/<id>/delete/` - Delete invoice
- `POST /invoices/<id>/send/` - Mark invoice as sent
- `POST /invoices/<id>/payment/` - Record payment
- `GET /api/invoice-detail/<id>/` - Get invoice details

### Clients
- `GET /clients/` - List all clients
- `POST /clients/create/` - Create new client
- `POST /clients/<id>/edit/` - Edit client
- `POST /clients/<id>/delete/` - Delete client (only if no invoices)

## Helper Functions

### invoicing.py
- `generate_invoice_number(user)` - Generate unique invoice number
- `calculate_invoice_totals(invoice)` - Recalculate invoice totals
- `update_invoice_status(invoice)` - Update status based on payments
- `create_invoice_from_template(template, client, user)` - Create from template
- `record_payment(invoice, amount, ...)` - Record a payment
- `get_invoice_statistics(user)` - Get user's invoice stats
- `get_client_statistics(client)` - Get client's invoice stats
- `create_recurring_invoices(user)` - Generate recurring invoices
- `get_currency_symbol(currency_code)` - Get currency symbol

## UI Components (To Be Created)

### Invoices Page
- Invoice list table with sorting and filtering
- Status badges (color-coded)
- Quick actions: View, Edit, Delete, Send, Record Payment
- Statistics dashboard at top
- Create invoice button
- Bulk actions (future enhancement)

### Clients Page
- Client list table
- Client statistics
- Quick actions: View, Edit, Delete
- Create client button
- Client details modal/panel

### Invoice Detail View
- Professional invoice layout
- Line items table
- Payment history
- Actions: Send, Record Payment, Edit, Delete
- PDF export (future enhancement)
- Email sending (future enhancement)

## Future Enhancements

### Phase 1 (High Priority)
1. **PDF Generation** - Generate professional PDF invoices
2. **Email Sending** - Send invoices directly to clients via email
3. **Invoice Templates** - UI for managing invoice templates
4. **Payment Reminders** - Automated email reminders for overdue invoices

### Phase 2 (Medium Priority)
5. **Custom Invoice Branding** - Logo, colors, custom fields
6. **Invoice Numbering Customization** - Custom prefix, starting number
7. **Multi-Tax Support** - Different tax rates per line item
8. **Credit Notes** - Issue credit notes and refunds
9. **Estimates/Quotes** - Convert estimates to invoices

### Phase 3 (Advanced)
10. **Online Payment Integration** - Stripe, PayPal, etc.
11. **Client Portal** - Allow clients to view and pay invoices online
12. **Automated Accounting Sync** - Export to QuickBooks, Xero
13. **Invoice Analytics** - Advanced reporting and analytics
14. **Multi-Language Support** - Invoices in different languages

## Testing Checklist

- [ ] Create client
- [ ] Edit client
- [ ] Delete client (with and without invoices)
- [ ] Create invoice with multiple line items
- [ ] Edit invoice
- [ ] Delete invoice
- [ ] Mark invoice as sent
- [ ] Record full payment
- [ ] Record partial payment
- [ ] Check overdue status update
- [ ] Filter invoices by status
- [ ] Filter invoices by client
- [ ] Search invoices
- [ ] View client statistics
- [ ] View invoice statistics
- [ ] Create recurring invoice
- [ ] Test multi-currency
- [ ] Link invoice to project

## Known Limitations

1. **Email Sending**: Currently marks as sent but doesn't actually email
2. **PDF Generation**: Not yet implemented
3. **Online Payments**: Manual payment recording only
4. **Templates UI**: Templates exist in database but no UI yet
5. **Recurring Generation**: Requires manual trigger (needs cron job)

## Performance Considerations

- Indexes on user, status, dates, invoice_number
- Select_related for client and project
- Pagination needed for large invoice lists
- Consider caching for statistics

## Security Considerations

- All views require login (@login_required)
- User isolation (can only access own invoices/clients)
- Client email uniqueness per user
- Invoice number uniqueness globally
- Protected client deletion (prevents if invoices exist)

## Integration Points

- **Projects**: Invoices can be linked to projects
- **Transactions**: Payments can be linked to transactions
- **Labels**: Future - auto-categorize invoice payments

## Success Metrics

- Number of invoices created per user
- Average time to payment
- Percentage of overdue invoices
- Client retention rate
- Invoice-to-payment conversion rate

---

**Status**: ✅ Core functionality complete, ready for UI implementation
**Next Step**: Create HTML templates for invoices and clients pages

