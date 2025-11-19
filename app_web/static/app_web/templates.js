// Invoice Templates JavaScript

let currentTemplateId = null;
let deleteTemplateId = null;
let useTemplateId = null;

// Initialize date pickers
document.addEventListener('DOMContentLoaded', function() {
  initializeDatePickers();
});

function initializeDatePickers() {
  flatpickr('.date-picker', {
    dateFormat: 'Y-m-d',
    defaultDate: new Date()
  });
}

// Load clients for template usage
async function loadClientsForTemplate() {
  try {
    const response = await fetch('/api/clients/');
    const data = await response.json();

    const select = document.getElementById('use-template-client');
    select.innerHTML = '<option value="">Select a client...</option>';

    data.clients.forEach(client => {
      const option = document.createElement('option');
      option.value = client.id;
      option.textContent = client.company ? `${client.name} (${client.company})` : client.name;
      select.appendChild(option);
    });
  } catch (error) {
    console.error('Error loading clients:', error);
  }
}

// Create Template Modal
function openCreateTemplateModal() {
  currentTemplateId = null;
  document.getElementById('modal-title').textContent = 'Create Template';
  document.getElementById('template-form').reset();
  document.getElementById('template-items-container').innerHTML = '';
  addTemplateItem(); // Add one default item
  document.getElementById('template-modal').style.display = 'flex';
}

function closeTemplateModal() {
  document.getElementById('template-modal').style.display = 'none';
  currentTemplateId = null;
}

// Edit Template
async function editTemplate(templateId) {
  currentTemplateId = templateId;

  try {
    const response = await fetch(`/api/template-detail/${templateId}/`);
    const template = await response.json();

    document.getElementById('modal-title').textContent = 'Edit Template';
    document.getElementById('template-name').value = template.name;
    document.getElementById('template-description').value = template.description;
    document.getElementById('template-tax-rate').value = template.default_tax_rate;
    document.getElementById('template-payment-terms').value = template.default_payment_terms;
    document.getElementById('template-notes').value = template.default_notes;
    document.getElementById('template-terms').value = template.default_terms;

    // Load items
    const container = document.getElementById('template-items-container');
    container.innerHTML = '';
    template.items.forEach(item => {
      addTemplateItem(item);
    });

    document.getElementById('template-modal').style.display = 'flex';
  } catch (error) {
    console.error('Error loading template:', error);
    alert('Failed to load template');
  }
}

// Save Template
async function saveTemplate(event) {
  event.preventDefault();

  const items = [];
  document.querySelectorAll('.template-item').forEach((itemEl, index) => {
    items.push({
      description: itemEl.querySelector('.item-description').value,
      quantity: parseFloat(itemEl.querySelector('.item-quantity').value),
      unit_price: parseFloat(itemEl.querySelector('.item-price').value),
      order: index
    });
  });

  const data = {
    name: document.getElementById('template-name').value,
    description: document.getElementById('template-description').value,
    tax_rate: parseFloat(document.getElementById('template-tax-rate').value),
    payment_terms: document.getElementById('template-payment-terms').value,
    notes: document.getElementById('template-notes').value,
    terms: document.getElementById('template-terms').value,
    items: items
  };

  try {
    const url = currentTemplateId
      ? `/templates/${currentTemplateId}/edit/`
      : '/templates/create/';

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
      alert(result.message);
      window.location.reload();
    } else {
      alert('Error: ' + (result.error || 'Failed to save template'));
    }
  } catch (error) {
    console.error('Error saving template:', error);
    alert('Failed to save template');
  }
}

// Add Template Item
function addTemplateItem(item = null) {
  const container = document.getElementById('template-items-container');
  const itemDiv = document.createElement('div');
  itemDiv.className = 'template-item';

  itemDiv.innerHTML = `
    <div class="field">
      <input type="text" class="item-description form-input" placeholder="Description" value="${item ? item.description : ''}" required>
    </div>
    <div class="field">
      <input type="number" class="item-quantity form-input" placeholder="Qty" step="0.01" min="0" value="${item ? item.quantity : 1}" required>
    </div>
    <div class="field">
      <input type="number" class="item-price form-input" placeholder="Price" step="0.01" min="0" value="${item ? item.unit_price : 0}" required>
    </div>
    <button type="button" class="btn-remove-item" onclick="removeTemplateItem(this)" title="Remove">&times;</button>
  `;

  container.appendChild(itemDiv);
}

function removeTemplateItem(button) {
  button.closest('.template-item').remove();
}

// Use Template
function useTemplate(templateId) {
  useTemplateId = templateId;

  // Set default dates
  const today = new Date();
  const dueDate = new Date(today);
  dueDate.setDate(dueDate.getDate() + 30);

  const dateEl = document.getElementById('use-template-date');
  const dueEl = document.getElementById('use-template-due-date');
  if (dateEl) dateEl.value = today.toISOString().split('T')[0];
  if (dueEl) dueEl.value = dueDate.toISOString().split('T')[0];

  // Load clients into dropdown and show modal after loaded
  loadClientsForTemplate().then(() => {
    const modal = document.getElementById('use-template-modal');
    if (modal) modal.style.display = 'flex';
  }).catch(err => {
    console.error('Error loading clients for template use:', err);
    const msg = document.getElementById('use-template-message');
    if (msg) {
      msg.style.display = 'block';
      msg.style.background = '#fde68a';
      msg.style.color = '#92400e';
      msg.textContent = 'Failed to load clients. Please try again.';
    } else {
      alert('Failed to load clients. Please try again.');
    }
  });
}

function closeUseTemplateModal() {
  document.getElementById('use-template-modal').style.display = 'none';
  useTemplateId = null;
  const msg = document.getElementById('use-template-message');
  if (msg) {
    msg.style.display = 'none';
    msg.textContent = '';
  }
}


async function createFromTemplate(event) {
  event.preventDefault();

  if (!useTemplateId) return;

  const clientIdEl = document.getElementById('use-template-client');
  const invoiceDateEl = document.getElementById('use-template-date');
  const dueDateEl = document.getElementById('use-template-due-date');
  const messageEl = document.getElementById('use-template-message');

  if (!clientIdEl || !invoiceDateEl || !dueDateEl) {
    alert('Required form elements are missing');
    return;
  }

  const data = {
    client_id: clientIdEl.value,
    invoice_date: invoiceDateEl.value,
    due_date: dueDateEl.value
  };

  try {
    const response = await fetch(`/templates/${useTemplateId}/use/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify(data)
    });

    const result = await response.json();

    if (result.success) {
      if (messageEl) {
        messageEl.style.display = 'block';
        messageEl.style.background = '#d1fae5';
        messageEl.style.color = '#065f46';
        messageEl.textContent = result.message || 'Invoice created successfully';
      } else {
        alert(result.message || 'Invoice created successfully');
      }
      // short delay so user can see message, then redirect
      setTimeout(() => { window.location.href = '/invoices/'; }, 600);

    } else {
      if (messageEl) {
        messageEl.style.display = 'block';
        messageEl.style.background = '#fee2e2';
        messageEl.style.color = '#991b1b';
        messageEl.textContent = result.error || 'Failed to create invoice from template';
      } else {
        alert('Error: ' + (result.error || 'Failed to create invoice'));
      }
    }
  } catch (error) {
    console.error('Error creating invoice from template:', error);
    if (messageEl) {
      messageEl.style.display = 'block';
      messageEl.style.background = '#fee2e2';
      messageEl.style.color = '#991b1b';
      messageEl.textContent = 'Failed to create invoice from template';
    } else {
      alert('Failed to create invoice from template');
    }
  }
}

// Delete Template
function deleteTemplate(templateId) {
  deleteTemplateId = templateId;
  document.getElementById('delete-modal').style.display = 'flex';
}

function closeDeleteModal() {
  document.getElementById('delete-modal').style.display = 'none';
  deleteTemplateId = null;
}

async function confirmDeleteTemplate() {
  if (!deleteTemplateId) return;

  try {
    const response = await fetch(`/templates/${deleteTemplateId}/delete/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken')
      }
    });

    const result = await response.json();

    if (result.success) {
      closeDeleteModal();
      window.location.reload();
    } else {
      alert('Error: ' + (result.error || 'Failed to delete template'));
    }
  } catch (error) {
    console.error('Error deleting template:', error);
    alert('Failed to delete template');
  }
}

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
