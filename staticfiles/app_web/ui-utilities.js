// ========================================
// GLOBAL UI UTILITIES
// Toast, Loading, Confirm Dialog, etc.
// ========================================

// Toast Notifications
const Toast = {
  container: null,

  init() {
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.className = 'toast-container';
      document.body.appendChild(this.container);
    }
  },

  show(message, type = 'info', duration = 4000) {
    this.init();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icons = {
      success: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
      error: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
      warning: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
      info: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
    };

    const titles = {
      success: 'Success',
      error: 'Error',
      warning: 'Warning',
      info: 'Info'
    };

    const colors = {
      success: '#10b981',
      error: '#ef4444',
      warning: '#f59e0b',
      info: '#2563eb'
    };

    toast.innerHTML = `
      <div class="toast-icon" style="color: ${colors[type]}">${icons[type]}</div>
      <div class="toast-content">
        <div class="toast-title">${titles[type]}</div>
        <div class="toast-message">${message}</div>
      </div>
      <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    this.container.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => {
        toast.classList.add('toast-exit');
        setTimeout(() => toast.remove(), 300);
      }, duration);
    }

    return toast;
  },

  success(message, duration) {
    return this.show(message, 'success', duration);
  },

  error(message, duration) {
    return this.show(message, 'error', duration);
  },

  warning(message, duration) {
    return this.show(message, 'warning', duration);
  },

  info(message, duration) {
    return this.show(message, 'info', duration);
  }
};

// Confirmation Dialog
const ConfirmDialog = {
  show(options = {}) {
    return new Promise((resolve) => {
      const {
        title = 'Confirm Action',
        message = 'Are you sure you want to proceed?',
        confirmText = 'Confirm',
        cancelText = 'Cancel',
        type = 'warning', // 'danger', 'warning', 'info'
        onConfirm = null,
        onCancel = null
      } = options;

      const backdrop = document.createElement('div');
      backdrop.className = 'confirm-modal-backdrop';

      const icons = {
        danger: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        warning: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
        info: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
      };

      backdrop.innerHTML = `
        <div class="confirm-modal">
          <div class="confirm-modal-header">
            <div class="confirm-modal-icon ${type}">
              ${icons[type]}
            </div>
            <div class="confirm-modal-title">
              <h3>${title}</h3>
            </div>
          </div>
          <div class="confirm-modal-body">
            ${message}
          </div>
          <div class="confirm-modal-footer">
            <button class="btn btn-secondary" data-action="cancel">${cancelText}</button>
            <button class="btn ${type === 'danger' ? 'btn-danger' : 'btn-primary'}" data-action="confirm">${confirmText}</button>
          </div>
        </div>
      `;

      const handleAction = (confirmed) => {
        backdrop.style.animation = 'fadeOut 0.2s ease-out';
        setTimeout(() => {
          backdrop.remove();
          resolve(confirmed);
          if (confirmed && onConfirm) onConfirm();
          if (!confirmed && onCancel) onCancel();
        }, 200);
      };

      backdrop.querySelector('[data-action="confirm"]').addEventListener('click', () => handleAction(true));
      backdrop.querySelector('[data-action="cancel"]').addEventListener('click', () => handleAction(false));
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) handleAction(false);
      });

      document.body.appendChild(backdrop);
    });
  },

  delete(itemName = 'this item') {
    return this.show({
      title: 'Delete Confirmation',
      message: `Are you sure you want to delete ${itemName}? This action cannot be undone.`,
      confirmText: 'Delete',
      cancelText: 'Cancel',
      type: 'danger'
    });
  }
};

// Loading State for Buttons
const ButtonLoader = {
  start(button) {
    if (!button) return;
    button.disabled = true;
    button.classList.add('btn-loading');
    button.dataset.originalText = button.innerHTML;
  },

  stop(button) {
    if (!button) return;
    button.disabled = false;
    button.classList.remove('btn-loading');
    if (button.dataset.originalText) {
      button.innerHTML = button.dataset.originalText;
      delete button.dataset.originalText;
    }
  }
};

// Page Loader
const PageLoader = {
  show() {
    let loader = document.getElementById('page-loader');
    if (!loader) {
      loader = document.createElement('div');
      loader.id = 'page-loader';
      loader.style.cssText = `
        position: fixed;
        inset: 0;
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(4px);
        z-index: 9998;
        display: flex;
        align-items: center;
        justify-content: center;
      `;
      loader.innerHTML = '<div class="spinner spinner-large spinner-primary"></div>';
      document.body.appendChild(loader);
    }
    loader.style.display = 'flex';
  },

  hide() {
    const loader = document.getElementById('page-loader');
    if (loader) {
      loader.style.display = 'none';
    }
  }
};

// Debounce utility
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Format currency
function formatCurrency(amount, currency = '£') {
  const num = parseFloat(amount);
  if (isNaN(num)) return `${currency}0.00`;
  return `${currency}${num.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// Format date
function formatDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: 'numeric' });
}

// Simple Sparkline (mini chart for KPI cards)
function createSparkline(data, width = 60, height = 24, color = '#2563eb') {
  if (!data || data.length === 0) return '';

  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;

  const points = data.map((value, index) => {
    const x = (index / (data.length - 1)) * width;
    const y = height - ((value - min) / range) * height;
    return `${x},${y}`;
  }).join(' ');

  return `
    <svg width="${width}" height="${height}" class="sparkline">
      <polyline
        fill="none"
        stroke="${color}"
        stroke-width="2"
        points="${points}"
      />
    </svg>
  `;
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { Toast, ConfirmDialog, ButtonLoader, PageLoader, debounce, formatCurrency, formatDate, createSparkline };
}

