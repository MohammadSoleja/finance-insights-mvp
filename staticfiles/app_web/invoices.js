// Invoices Management JavaScript

let currentInvoiceId = null;
let lineItemCount = 0;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
  // Set default dates
  const today = new Date().toISOString().split('T')[0];
  const invoiceDateEl = document.getElementById('invoice-date');
  const dueDateEl = document.getElementById('due-date');
  const paymentDateEl = document.getElementById('payment-date');

  if (invoiceDateEl) invoiceDateEl.value = today;

  if (dueDateEl) {
    const dueDate = new Date();
    dueDate.setDate(dueDate.getDate() + 30);
    dueDateEl.value = dueDate.toISOString().split('T')[0];
  }

  if (paymentDateEl) paymentDateEl.value = today;

  // Add event listeners for calculation
  const taxRateEl = document.getElementById('tax-rate');
  const discountEl = document.getElementById('discount');
  if (taxRateEl) taxRateEl.addEventListener('input', calculateTotals);
  if (discountEl) discountEl.addEventListener('input', calculateTotals);
});

// Filters
function applyFilters() {
  const search = document.getElementById('search').value;
  const status = document.getElementById('status-filter').value;
  const client = document.getElementById('client-filter').value;
  const dateFrom = document.getElementById('date-from').value;
  const dateTo = document.getElementById('date-to').value;

  const params = new URLSearchParams();
  if (search) params.set('q', search);
  if (status) params.set('status', status);
  if (client) params.set('client', client);
  if (dateFrom) params.set('date_from', dateFrom);
  if (dateTo) params.set('date_to', dateTo);

  window.location.href = '/invoices/?' + params.toString();
}

function clearFilters() {
  window.location.href = '/invoices/';
}

// Modal Management
function openCreateInvoiceModal() {
  currentInvoiceId = null;
  document.getElementById('modal-title').textContent = 'Create Invoice';
  document.getElementById('invoice-form').reset();
  document.getElementById('line-items').innerHTML = '';
  lineItemCount = 0;
  addLineItem();
  document.getElementById('invoice-modal').style.display = 'flex';
}

function closeInvoiceModal() {
  document.getElementById('invoice-modal').style.display = 'none';
}

function openPaymentModal() {
  document.getElementById('payment-modal').style.display = 'flex';
}

function closePaymentModal() {
  document.getElementById('payment-modal').style.display = 'none';
}

// Line Items
function addLineItem() {
  lineItemCount++;
  const container = document.getElementById('line-items');
  const lineItem = document.createElement('div');
  lineItem.className = 'line-item';
  lineItem.dataset.id = lineItemCount;

  lineItem.innerHTML = `
    <input type="text" placeholder="Description" class="item-description" required>
    <input type="number" placeholder="Qty" class="item-quantity" value="1" step="1" min="1" required>
    <input type="number" placeholder="Price" class="item-price" value="0" step="0.01" min="0" required>
    <input type="number" placeholder="Amount" class="item-amount" value="0" step="0.01" readonly>
    <button type="button" class="remove-line-item" onclick="removeLineItem(${lineItemCount})">×</button>
  `;

  container.appendChild(lineItem);

  // Add event listeners for calculation
  const qtyInput = lineItem.querySelector('.item-quantity');
  const priceInput = lineItem.querySelector('.item-price');
  const amountInput = lineItem.querySelector('.item-amount');

  function updateAmount() {
    const qty = parseFloat(qtyInput.value) || 0;
    const price = parseFloat(priceInput.value) || 0;
    amountInput.value = (qty * price).toFixed(2);
    calculateTotals();
  }

  qtyInput.addEventListener('input', updateAmount);
  priceInput.addEventListener('input', updateAmount);
}

function removeLineItem(id) {
  const lineItem = document.querySelector(`.line-item[data-id="${id}"]`);
  if (lineItem) {
    lineItem.remove();
    calculateTotals();
  }
}

// Calculations
function calculateTotals() {
  const lineItems = document.querySelectorAll('.line-item');
  let subtotal = 0;

  lineItems.forEach(item => {
    const amount = parseFloat(item.querySelector('.item-amount').value) || 0;
    subtotal += amount;
  });

  const taxRate = parseFloat(document.getElementById('tax-rate').value) || 0;
  const discount = parseFloat(document.getElementById('discount').value) || 0;

  const tax = (subtotal * taxRate) / 100;
  const total = subtotal + tax - discount;

  document.getElementById('subtotal-display').textContent = `£${subtotal.toFixed(2)}`;
  document.getElementById('tax-display').textContent = `£${tax.toFixed(2)}`;
  document.getElementById('discount-display').textContent = `£${discount.toFixed(2)}`;
  document.getElementById('total-display').textContent = `£${total.toFixed(2)}`;
}

// CRUD Operations
async function saveInvoice() {
  const clientId = document.getElementById('client-select').value;
  const invoiceDate = document.getElementById('invoice-date').value;
  const dueDate = document.getElementById('due-date').value;
  const taxRate = document.getElementById('tax-rate').value;
  const discount = document.getElementById('discount').value;
  const notes = document.getElementById('notes').value;
  const terms = document.getElementById('terms').value;

  if (!clientId) {
    alert('Please select a client');
    return;
  }

  // Collect line items
  const lineItems = [];
  const lineItemElements = document.querySelectorAll('.line-item');

  lineItemElements.forEach((item, index) => {
    const description = item.querySelector('.item-description').value;
    const quantity = parseFloat(item.querySelector('.item-quantity').value);
    const unitPrice = parseFloat(item.querySelector('.item-price').value);

    if (description && quantity && unitPrice) {
      lineItems.push({
        description,
        quantity,
        unit_price: unitPrice,
        order: index
      });
    }
  });

  if (lineItems.length === 0) {
    alert('Please add at least one line item');
    return;
  }

  const data = {
    client_id: parseInt(clientId),
    invoice_date: invoiceDate,
    due_date: dueDate,
    tax_rate: parseFloat(taxRate),
    discount: parseFloat(discount),
    notes,
    terms,
    items: lineItems,
    status: 'draft'
  };

  try {
    const url = currentInvoiceId
      ? `/invoices/${currentInvoiceId}/edit/`
      : '/invoices/create/';

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify(data)
    });

    const result = await response.json();

    if (result.success) {
      closeInvoiceModal();
      window.location.reload();
    } else {
      alert('Error: ' + (result.error || 'Failed to save invoice'));
    }
  } catch (error) {
    console.error('Error saving invoice:', error);
    alert('Failed to save invoice');
  }
}

async function editInvoice(invoiceId) {
  // Fetch invoice details
  try {
    const response = await fetch(`/api/invoice-detail/${invoiceId}/`);
    const invoice = await response.json();

    currentInvoiceId = invoiceId;
    document.getElementById('modal-title').textContent = 'Edit Invoice';

    // Populate form
    document.getElementById('client-select').value = invoice.client.id;
    document.getElementById('invoice-date').value = invoice.invoice_date;
    document.getElementById('due-date').value = invoice.due_date;
    document.getElementById('tax-rate').value = invoice.tax_rate;
    document.getElementById('discount').value = invoice.discount;
    document.getElementById('notes').value = invoice.notes || '';
    document.getElementById('terms').value = invoice.terms || '';

    // Clear and populate line items
    document.getElementById('line-items').innerHTML = '';
    lineItemCount = 0;

    invoice.items.forEach(item => {
      addLineItem();
      const lineItem = document.querySelector(`.line-item[data-id="${lineItemCount}"]`);
      lineItem.querySelector('.item-description').value = item.description;
      lineItem.querySelector('.item-quantity').value = item.quantity;
      lineItem.querySelector('.item-price').value = item.unit_price;
      lineItem.querySelector('.item-amount').value = item.amount;
    });

    calculateTotals();
    document.getElementById('invoice-modal').style.display = 'flex';
  } catch (error) {
    console.error('Error loading invoice:', error);
    alert('Failed to load invoice');
  }
}

// Delete Modal Management
let deleteInvoiceId = null;

function deleteInvoice(invoiceId) {
  deleteInvoiceId = invoiceId;
  document.getElementById('delete-modal').style.display = 'flex';
}

function closeDeleteModal() {
  document.getElementById('delete-modal').style.display = 'none';
  deleteInvoiceId = null;
}

async function confirmDeleteInvoice() {
  if (!deleteInvoiceId) return;

  const confirmed = await ConfirmDialog.show({
    title: 'Delete Invoice',
    message: 'Are you sure you want to delete this invoice? This action cannot be undone.',
    confirmText: 'Delete',
    cancelText: 'Cancel',
    type: 'danger'
  });

  if (!confirmed) return;

  const deleteBtn = document.querySelector(`[onclick="deleteInvoice(${deleteInvoiceId})"]`);
  if (deleteBtn) ButtonLoader.start(deleteBtn);

  try {
    const response = await fetch(`/invoices/${deleteInvoiceId}/delete/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken')
      }
    });

    const result = await response.json();

    if (result.success) {
      closeDeleteModal();
      Toast.success('Invoice deleted successfully');
      setTimeout(() => window.location.reload(), 500);
    } else {
      Toast.error(result.error || 'Failed to delete invoice');
    }
  } catch (error) {
    console.error('Error deleting invoice:', error);
    Toast.error('Failed to delete invoice');
  } finally {
    if (deleteBtn) ButtonLoader.stop(deleteBtn);
  }
}

// Send Modal Management
let sendInvoiceId = null;

function sendInvoice(invoiceId) {
  sendInvoiceId = invoiceId;
  document.getElementById('send-modal').style.display = 'flex';
}

function closeSendModal() {
  document.getElementById('send-modal').style.display = 'none';
  sendInvoiceId = null;
}

async function confirmSendInvoice() {
  if (!sendInvoiceId) return;

  const sendBtn = document.querySelector('.modal-footer .btn-primary');
  if (sendBtn) ButtonLoader.start(sendBtn);

  try {
    const response = await fetch(`/invoices/${sendInvoiceId}/send/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify({})
    });

    const result = await response.json();

    if (result.success) {
      closeSendModal();
      Toast.success(result.message || 'Invoice sent successfully');
      setTimeout(() => window.location.reload(), 500);
    } else {
      Toast.error(result.error || 'Failed to send invoice');
    }
  } catch (error) {
    console.error('Error sending invoice:', error);
    Toast.error('Failed to send invoice');
  } finally {
    if (sendBtn) ButtonLoader.stop(sendBtn);
  }
}

// Send Payment Reminder
async function sendReminder(invoiceId) {
  const confirmed = await ConfirmDialog.show({
    title: 'Send Reminder',
    message: 'Send payment reminder to client?',
    confirmText: 'Send Reminder',
    cancelText: 'Cancel',
    type: 'info'
  });

  if (!confirmed) return;

  const reminderBtn = document.querySelector(`[onclick="sendReminder(${invoiceId})"]`);
  if (reminderBtn) ButtonLoader.start(reminderBtn);

  try {
    const response = await fetch(`/invoices/${invoiceId}/reminder/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify({})
    });

    const result = await response.json();

    if (result.success) {
      Toast.success(result.message || 'Reminder sent successfully');
    } else {
      Toast.error(result.error || 'Failed to send reminder');
    }
  } catch (error) {
    console.error('Error sending reminder:', error);
    Toast.error('Failed to send reminder');
  } finally {
    if (reminderBtn) ButtonLoader.stop(reminderBtn);
  }
}

let currentPaymentInvoiceId = null;

function recordPayment(invoiceId) {
  currentPaymentInvoiceId = invoiceId;
  document.getElementById('payment-form').reset();
  document.getElementById('payment-date').value = new Date().toISOString().split('T')[0];
  openPaymentModal();
}

async function savePayment() {
  const amount = document.getElementById('payment-amount').value;
  const paymentDate = document.getElementById('payment-date').value;
  const paymentMethod = document.getElementById('payment-method').value;
  const reference = document.getElementById('payment-reference').value;
  const notes = document.getElementById('payment-notes').value;

  if (!amount || !paymentDate) {
    alert('Please fill in required fields');
    return;
  }

  const data = {
    amount: parseFloat(amount),
    payment_date: paymentDate,
    payment_method: paymentMethod,
    reference,
    notes
  };

  try {
    const response = await fetch(`/invoices/${currentPaymentInvoiceId}/payment/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify(data)
    });

    const result = await response.json();

    if (result.success) {
      closePaymentModal();
      window.location.reload();
    } else {
      alert('Error: ' + (result.error || 'Failed to record payment'));
    }
  } catch (error) {
    console.error('Error recording payment:', error);
    alert('Failed to record payment');
  }
}

function viewInvoice(invoiceId) {
  // Redirect to PDF view page
  window.location.href = `/invoices/${invoiceId}/pdf/`;
}

// Utility function to get CSRF token
// Utility function to get CSRF token
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Save Invoice as Template
async function saveAsTemplate(invoiceId) {
  const templateName = prompt('Enter a name for this template:');
  if (!templateName) return;

  const description = prompt('Enter a description (optional):') || '';

  try {
    const response = await fetch('/templates/create/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify({
        invoice_id: invoiceId,
        name: templateName,
        description: description
      })
    });

    const result = await response.json();

    if (result.success) {
      alert(result.message || 'Template created successfully');
    } else {
      alert('Error: ' + (result.error || 'Failed to create template'));
    }
  } catch (error) {
    console.error('Error saving template:', error);
    alert('Failed to save template');
  }
}

// Close modal on outside click
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('modal-backdrop')) {
    closeInvoiceModal();
    closePaymentModal();
    closeDeleteModal();
    closeSendModal();
  }
});

