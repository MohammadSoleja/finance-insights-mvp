// Clients Management JavaScript

let currentClientId = null;

// Modal Management
function openCreateClientModal() {
  currentClientId = null;
  document.getElementById('modal-title').textContent = 'Add Client';
  document.getElementById('client-form').reset();
  document.getElementById('client-active').checked = true;
  document.getElementById('client-modal').style.display = 'flex';
}

function closeClientModal() {
  document.getElementById('client-modal').style.display = 'none';
}

// CRUD Operations
async function saveClient() {
  const name = document.getElementById('client-name').value;
  const email = document.getElementById('client-email').value;
  const company = document.getElementById('client-company').value;
  const phone = document.getElementById('client-phone').value;
  const address = document.getElementById('client-address').value;
  const taxId = document.getElementById('client-tax-id').value;
  const paymentTerms = document.getElementById('client-payment-terms').value;
  const currency = document.getElementById('client-currency').value;
  const notes = document.getElementById('client-notes').value;
  const active = document.getElementById('client-active').checked;

  if (!name || !email) {
    alert('Name and email are required');
    return;
  }

  const data = {
    name,
    email,
    company,
    phone,
    address,
    tax_id: taxId,
    payment_terms: paymentTerms,
    currency,
    notes,
    active
  };

  try {
    const url = currentClientId
      ? `/clients/${currentClientId}/edit/`
      : '/clients/create/';

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
      closeClientModal();
      window.location.reload();
    } else {
      alert('Error: ' + (result.error || 'Failed to save client'));
    }
  } catch (error) {
    console.error('Error saving client:', error);
    alert('Failed to save client');
  }
}

function editClient(clientId) {
  // Find the client card
  const clientCard = document.querySelector(`.client-card[data-client-id="${clientId}"]`);
  if (!clientCard) {
    alert('Client not found');
    return;
  }

  currentClientId = clientId;
  document.getElementById('modal-title').textContent = 'Edit Client';

  // Extract data from card (this is a simplified version - in production, fetch from API)
  const clientData = getClientDataFromCard(clientCard);

  // Populate form
  document.getElementById('client-name').value = clientData.name;
  document.getElementById('client-email').value = clientData.email;
  document.getElementById('client-company').value = clientData.company || '';
  document.getElementById('client-phone').value = clientData.phone || '';
  document.getElementById('client-address').value = clientData.address || '';
  document.getElementById('client-tax-id').value = clientData.taxId || '';
  document.getElementById('client-payment-terms').value = clientData.paymentTerms || '';
  document.getElementById('client-currency').value = clientData.currency || 'GBP';
  document.getElementById('client-notes').value = clientData.notes || '';
  document.getElementById('client-active').checked = clientData.active;

  document.getElementById('client-modal').style.display = 'flex';
}

function getClientDataFromCard(card) {
  // Extract data from the card DOM elements
  const name = card.querySelector('h3').textContent.trim();
  const companyEl = card.querySelector('.client-company');
  const company = companyEl ? companyEl.textContent.trim() : '';

  const infoItems = card.querySelectorAll('.info-item');
  let email = '';
  let phone = '';
  let paymentTerms = '';
  let currency = 'GBP';

  infoItems.forEach(item => {
    const label = item.querySelector('.info-label').textContent.trim();
    const value = item.querySelector('span:last-child').textContent.trim();

    if (label.includes('Email')) email = value;
    if (label.includes('Phone')) phone = value;
    if (label.includes('Payment Terms')) paymentTerms = value;
  });

  // Check for currency in stats
  const statValue = card.querySelector('.stat-value');
  if (statValue) {
    const text = statValue.textContent.trim();
    if (text.startsWith('£')) currency = 'GBP';
    else if (text.startsWith('$')) currency = 'USD';
    else if (text.startsWith('€')) currency = 'EUR';
    // Add more as needed
  }

  const isActive = !card.querySelector('.status-inactive');

  return {
    name,
    email,
    company,
    phone,
    address: '', // Can't extract from card
    taxId: '', // Can't extract from card
    paymentTerms,
    currency,
    notes: '', // Can't extract from card
    active: isActive
  };
}

async function deleteClient(clientId) {
  if (!confirm('Are you sure you want to delete this client? This will only work if the client has no invoices.')) {
    return;
  }

  try {
    const response = await fetch(`/clients/${clientId}/delete/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken')
      }
    });

    const result = await response.json();

    if (result.success) {
      window.location.reload();
    } else {
      alert('Error: ' + (result.error || 'Failed to delete client'));
    }
  } catch (error) {
    console.error('Error deleting client:', error);
    alert('Failed to delete client');
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

// Close modal on outside click
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('modal-backdrop')) {
    closeClientModal();
  }
});

