// Budgets Page JavaScript
(function() {
  'use strict';

  // Make budget data available globally
  window.budgetSummaryData = window.budgetSummaryData || [];

  // Label Selector (GitHub-style)
  function initLabelSelector(containerId, hiddenSelectId) {
    const container = document.getElementById(containerId);
    const hiddenSelect = document.getElementById(hiddenSelectId);

    if (!container || !hiddenSelect) return;

    const allLabels = Array.from(hiddenSelect.options)
      .map(opt => ({ id: opt.value, name: opt.text }))
      .filter(l => l.id);

    const preSelected = Array.from(hiddenSelect.options)
      .filter(opt => opt.selected)
      .map(opt => opt.value);

    function renderLabels() {
      container.innerHTML = '';
      if (allLabels.length === 0) {
        container.classList.add('empty');
        return;
      }
      container.classList.remove('empty');

      allLabels.forEach(label => {
        const pill = document.createElement('span');
        pill.className = 'label-pill';
        pill.textContent = label.name;
        pill.dataset.labelId = label.id;

        if (preSelected.includes(label.id)) {
          pill.classList.add('selected');
        }

        pill.onclick = () => toggleLabel(label.id);
        container.appendChild(pill);
      });
    }

    function toggleLabel(id) {
      const pill = container.querySelector(`[data-label-id="${id}"]`);
      if (!pill) return;

      pill.classList.toggle('selected');

      Array.from(hiddenSelect.options).forEach(opt => {
        if (opt.value === id) {
          opt.selected = pill.classList.contains('selected');
        }
      });
    }

    renderLabels();
  }

  // Initialize label selectors
  if (document.getElementById('labels-container')) {
    initLabelSelector('labels-container', 'id_labels');
  }
  if (document.getElementById('modal-labels-container')) {
    initLabelSelector('modal-labels-container', 'modal_labels');
  }

  // Modal state
  let currentDeleteId = null;
  let currentDeleteIds = [];

  // Add Budget Modal
  window.openAddBudgetModal = function() {
    const form = document.getElementById('add-budget-form');
    const hiddenSelect = document.createElement('select');
    hiddenSelect.id = 'modal_labels';
    hiddenSelect.name = 'labels';
    hiddenSelect.multiple = true;
    hiddenSelect.style.display = 'none';

    const mainSelect = document.getElementById('id_labels');
    if (mainSelect) {
      Array.from(mainSelect.options).forEach(opt => {
        if (opt.value) {
          const newOpt = document.createElement('option');
          newOpt.value = opt.value;
          newOpt.text = opt.text;
          hiddenSelect.appendChild(newOpt);
        }
      });
    }
    form.appendChild(hiddenSelect);

    initLabelSelector('modal-labels-container', 'modal_labels');

    flatpickr('#modal_start_date', { dateFormat: 'Y-m-d', altInput: true, altFormat: 'M j, Y' });
    flatpickr('#modal_end_date', { dateFormat: 'Y-m-d', altInput: true, altFormat: 'M j, Y' });

    document.getElementById('addBudgetModal').classList.add('active');
  };

  window.closeAddBudgetModal = function() {
    document.getElementById('addBudgetModal').classList.remove('active');
  };

  // Edit Budget Modal
  window.openEditModal = async function(budgetId) {
    const card = document.querySelector(`[data-budget-id="${budgetId}"]`);
    if (!card) return;

    const name = card.querySelector('.budget-category').textContent.trim();
    const period = card.dataset.period;
    const amount = card.dataset.amount;

    document.getElementById('edit_budget_id').value = budgetId;
    document.getElementById('edit_name').value = name;
    document.getElementById('edit_amount').value = amount;
    document.getElementById('edit_period').value = period;

    const budgetData = window.budgetSummaryData || [];
    const budget = budgetData.find(b => b.id == budgetId);

    let hiddenSelect = document.getElementById('edit_labels');
    if (!hiddenSelect) {
      hiddenSelect = document.createElement('select');
      hiddenSelect.id = 'edit_labels';
      hiddenSelect.name = 'labels';
      hiddenSelect.multiple = true;
      hiddenSelect.style.display = 'none';
      document.getElementById('edit-budget-form').appendChild(hiddenSelect);

      const mainSelect = document.getElementById('id_labels');
      if (mainSelect) {
        Array.from(mainSelect.options).forEach(opt => {
          if (opt.value) {
            const newOpt = document.createElement('option');
            newOpt.value = opt.value;
            newOpt.text = opt.text;
            hiddenSelect.appendChild(newOpt);
          }
        });
      }
    }

    initLabelSelector('edit-labels-container', 'edit_labels');

    if (budget && budget.labels) {
      budget.labels.forEach(labelName => {
        const allPills = document.querySelectorAll('#edit-labels-container .label-pill');
        allPills.forEach(p => {
          if (p.textContent.trim() === labelName) {
            p.classList.add('selected');
            Array.from(hiddenSelect.options).forEach(opt => {
              if (opt.text === labelName) {
                opt.selected = true;
              }
            });
          }
        });
      });
    }

    if (period === 'custom') {
      document.getElementById('edit-date-range-fields').classList.add('visible');
    } else {
      document.getElementById('edit-date-range-fields').classList.remove('visible');
    }

    const isActive = !card.dataset.inactive;
    document.getElementById('edit_active').checked = isActive;

    const recurringOptions = document.getElementById('edit-recurring-options');
    if (budget && budget.recurring_group_id) {
      document.getElementById('edit_recurring_group_id').value = budget.recurring_group_id;
      recurringOptions.style.display = 'block';
      document.querySelector('input[name="edit_scope"][value="this"]').checked = true;
    } else {
      recurringOptions.style.display = 'none';
    }

    if (!document.getElementById('edit_start_date')._flatpickr) {
      flatpickr('#edit_start_date', { dateFormat: 'Y-m-d', altInput: true, altFormat: 'M j, Y' });
      flatpickr('#edit_end_date', { dateFormat: 'Y-m-d', altInput: true, altFormat: 'M j, Y' });
    }

    document.getElementById('editModal').classList.add('active');
  };

  window.closeEditModal = function() {
    document.getElementById('editModal').classList.remove('active');
  };

  // Delete Modals
  window.confirmDelete = function(budgetId, budgetName) {
    currentDeleteId = budgetId;
    currentDeleteIds = [];

    document.getElementById('deleteModalTitle').textContent = 'Delete Budget';
    document.getElementById('deleteSingleContent').style.display = 'block';
    document.getElementById('deleteBulkContent').style.display = 'none';
    document.getElementById('deleteBudgetName').textContent = budgetName;
    document.getElementById('deleteButtonText').textContent = 'Delete Budget';
    document.getElementById('deleteModal').classList.add('active');
  };

  window.closeDeleteModal = function() {
    document.getElementById('deleteModal').classList.remove('active');
    currentDeleteId = null;
    currentDeleteIds = [];
  };

  window.deleteBudget = function() {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '';

    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = document.querySelector('[name=csrfmiddlewaretoken]').value;

    const actionInput = document.createElement('input');
    actionInput.type = 'hidden';
    actionInput.name = 'action';

    if (currentDeleteIds.length > 0) {
      actionInput.value = 'bulk_delete';
      const idsInput = document.createElement('input');
      idsInput.type = 'hidden';
      idsInput.name = 'budget_ids';
      idsInput.value = currentDeleteIds.join(',');
      form.appendChild(idsInput);
    } else if (currentDeleteId) {
      actionInput.value = 'delete';
      const idInput = document.createElement('input');
      idInput.type = 'hidden';
      idInput.name = 'budget_id';
      idInput.value = currentDeleteId;
      form.appendChild(idInput);
    } else {
      return;
    }

    form.appendChild(csrfInput);
    form.appendChild(actionInput);
    document.body.appendChild(form);
    form.submit();
  };

  // Bulk Delete
  window.confirmBulkDelete = function() {
    const checkboxes = document.querySelectorAll('.budget-checkbox:checked');
    if (checkboxes.length === 0) return;

    currentDeleteIds = Array.from(checkboxes).map(cb => cb.dataset.budgetId);
    currentDeleteId = null;

    document.getElementById('deleteModalTitle').textContent = 'Delete Multiple Budgets';
    document.getElementById('deleteSingleContent').style.display = 'none';
    document.getElementById('deleteBulkContent').style.display = 'block';
    document.getElementById('deleteBulkCount').textContent = currentDeleteIds.length;
    document.getElementById('deleteButtonText').textContent = 'Delete Budgets';
    document.getElementById('deleteModal').classList.add('active');
  };

  function updateBulkDeleteButton() {
    const checkboxes = document.querySelectorAll('.budget-checkbox:checked');
    const count = checkboxes.length;
    const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
    const selectedCount = document.getElementById('selected-count');

    if (count > 0) {
      bulkDeleteBtn.style.display = 'block';
      selectedCount.textContent = count;
    } else {
      bulkDeleteBtn.style.display = 'none';
    }
  }

  // Budget Filtering
  function filterBudgets() {
    const statusFilter = document.getElementById('filter-status').value;
    const periodFilter = document.getElementById('filter-period').value;
    const usageFilter = document.getElementById('filter-usage').value;
    const sortFilter = document.getElementById('filter-sort').value;
    const cards = Array.from(document.querySelectorAll('.budget-card'));

    cards.forEach(card => {
      let show = true;

      if (statusFilter === 'active') {
        show = show && !card.dataset.inactive;
      } else if (statusFilter === 'inactive') {
        show = show && card.dataset.inactive;
      }

      if (periodFilter !== 'all') {
        show = show && card.dataset.period === periodFilter;
      }

      if (usageFilter === 'over') {
        show = show && card.classList.contains('over-budget');
      } else if (usageFilter === 'warning') {
        show = show && card.classList.contains('warning');
      } else if (usageFilter === 'ok') {
        show = show && card.classList.contains('ok');
      }

      card.style.display = show ? '' : 'none';
    });

    const grid = document.getElementById('budget-grid');
    if (!grid) return;

    const visibleCards = cards.filter(c => c.style.display !== 'none');
    visibleCards.sort((a, b) => {
      if (sortFilter === 'name') {
        return a.querySelector('.budget-category').textContent.localeCompare(
          b.querySelector('.budget-category').textContent
        );
      } else if (sortFilter === 'amount') {
        return parseFloat(b.dataset.amount || 0) - parseFloat(a.dataset.amount || 0);
      } else {
        return parseFloat(b.dataset.usage || 0) - parseFloat(a.dataset.usage || 0);
      }
    });

    visibleCards.forEach(card => grid.appendChild(card));
  }

  // Event Listeners
  document.addEventListener('DOMContentLoaded', function() {
    // Checkbox listeners
    document.querySelectorAll('.budget-checkbox').forEach(checkbox => {
      checkbox.addEventListener('change', updateBulkDeleteButton);
    });

    // Filter listeners
    ['filter-status', 'filter-period', 'filter-usage', 'filter-sort'].forEach(id => {
      const elem = document.getElementById(id);
      if (elem) elem.addEventListener('change', filterBudgets);
    });

    // Edit period change
    const editPeriod = document.getElementById('edit_period');
    const editDateFields = document.getElementById('edit-date-range-fields');
    if (editPeriod && editDateFields) {
      editPeriod.addEventListener('change', function() {
        editDateFields.classList.toggle('visible', this.value === 'custom');
      });
    }

    // Modal period change
    const modalPeriod = document.getElementById('modal_period');
    const modalDateFields = document.getElementById('modal-date-range-fields');
    const modalRecurringCheckbox = document.getElementById('modal_is_recurring');
    const modalRecurringOptions = document.getElementById('modal-recurring-options');
    const modalSubmitBtn = document.getElementById('modal-submit-btn');

    if (modalPeriod && modalDateFields) {
      modalPeriod.addEventListener('change', function() {
        if (this.value === 'custom') {
          modalDateFields.classList.add('visible');
          if (modalRecurringCheckbox) {
            modalRecurringCheckbox.checked = false;
            modalRecurringCheckbox.disabled = true;
            if (modalRecurringOptions) modalRecurringOptions.style.display = 'none';
          }
        } else {
          modalDateFields.classList.remove('visible');
          if (modalRecurringCheckbox) {
            modalRecurringCheckbox.disabled = false;
          }
        }
      });
    }

    // Recurring checkbox
    if (modalRecurringCheckbox && modalRecurringOptions) {
      modalRecurringCheckbox.addEventListener('change', function() {
        if (this.checked) {
          modalRecurringOptions.style.display = 'block';
          if (modalSubmitBtn) modalSubmitBtn.textContent = 'Create Recurring Budget';
        } else {
          modalRecurringOptions.style.display = 'none';
          if (modalSubmitBtn) modalSubmitBtn.textContent = 'Create Budget';
        }
      });
    }

    // Date pickers
    const startDateInput = document.getElementById('id_start_date');
    const endDateInput = document.getElementById('id_end_date');

    if (startDateInput) {
      flatpickr(startDateInput, {
        dateFormat: 'Y-m-d',
        altInput: true,
        altFormat: 'M j, Y',
        onChange: function(selectedDates) {
          if (selectedDates[0] && endDateInput._flatpickr) {
            endDateInput._flatpickr.set('minDate', selectedDates[0]);
          }
        }
      });
    }

    if (endDateInput) {
      flatpickr(endDateInput, {
        dateFormat: 'Y-m-d',
        altInput: true,
        altFormat: 'M j, Y'
      });
    }

    // Period select handling
    const periodSelect = document.getElementById('id_period');
    const dateRangeFields = document.getElementById('date-range-fields');

    if (periodSelect && dateRangeFields) {
      function toggleDateFields() {
        if (periodSelect.value === 'custom') {
          dateRangeFields.classList.add('visible');
          if (startDateInput) startDateInput.required = true;
          if (endDateInput) endDateInput.required = true;
        } else {
          dateRangeFields.classList.remove('visible');
          if (startDateInput) startDateInput.required = false;
          if (endDateInput) endDateInput.required = false;
        }
      }

      toggleDateFields();
      periodSelect.addEventListener('change', toggleDateFields);
    }

    // Close modals on outside click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
      overlay.addEventListener('click', function(e) {
        if (e.target === this) {
          this.classList.remove('active');
        }
      });
    });
  });

  // Auto-refresh budgets
  function formatMoney(num) {
    return new Intl.NumberFormat('en-GB', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(num);
  }

  function updateBudgetCard(card, budgetData) {
    if (!card) return;

    card.classList.remove('over-budget', 'warning', 'ok');
    if (budgetData.is_over) {
      card.classList.add('over-budget');
    } else if (budgetData.percent_used >= 80) {
      card.classList.add('warning');
    } else {
      card.classList.add('ok');
    }

    const progressBar = card.querySelector('.progress-bar');
    if (progressBar) {
      const width = budgetData.percent_used > 100 ? 100 : budgetData.percent_used;
      progressBar.style.width = width + '%';
      progressBar.classList.remove('over', 'warning', 'ok');
      if (budgetData.is_over) {
        progressBar.classList.add('over');
      } else if (budgetData.percent_used >= 80) {
        progressBar.classList.add('warning');
      } else {
        progressBar.classList.add('ok');
      }
    }

    const percentElem = card.querySelector('.budget-percent');
    if (percentElem) {
      percentElem.textContent = budgetData.percent_used + '% used';
      let color = '#16a34a';
      if (budgetData.is_over) {
        color = '#ef4444';
      } else if (budgetData.percent_used >= 80) {
        color = '#f59e0b';
      }
      percentElem.style.color = color;
    }

    const spentElem = card.querySelector('.budget-spent');
    if (spentElem) {
      spentElem.textContent = '£' + formatMoney(budgetData.spent);
      spentElem.classList.toggle('over', budgetData.is_over);
    }

    const remainingElem = card.querySelector('.budget-remaining');
    if (remainingElem) {
      remainingElem.textContent = '£' + formatMoney(budgetData.remaining);
      remainingElem.classList.remove('ok', 'over');
      remainingElem.classList.add(budgetData.remaining >= 0 ? 'ok' : 'over');
    }

    const totalElem = card.querySelector('.budget-total');
    if (totalElem) {
      totalElem.textContent = '£' + formatMoney(budgetData.budget_amount);
    }

    card.style.animation = 'none';
    setTimeout(() => {
      card.style.animation = 'budget-update-pulse 0.5s ease';
    }, 10);
  }

  function refreshBudgets() {
    fetch('/api/budget-list/')
      .then(response => response.json())
      .then(data => {
        if (data.ok && data.budgets) {
          data.budgets.forEach(budget => {
            const card = document.querySelector(`[data-budget-id="${budget.id}"]`);
            if (card) {
              updateBudgetCard(card, budget);
            }
          });
          showRefreshIndicator();
        }
      })
      .catch(error => {
        console.error('Failed to refresh budgets:', error);
      });
  }

  function showRefreshIndicator() {
    const header = document.querySelector('.budget-header h1');
    if (!header) return;

    const indicator = document.createElement('span');
    indicator.textContent = '●';
    indicator.style.cssText = 'color: #16a34a; margin-left: 0.5rem; font-size: 0.5rem; opacity: 0; transition: opacity 0.3s;';
    header.appendChild(indicator);

    setTimeout(() => { indicator.style.opacity = '1'; }, 10);
    setTimeout(() => { indicator.style.opacity = '0'; }, 1500);
    setTimeout(() => { indicator.remove(); }, 1800);
  }

  const refreshInterval = setInterval(refreshBudgets, 30000);

  document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
      clearInterval(refreshInterval);
    }
  });

  const style = document.createElement('style');
  style.textContent = `
    @keyframes budget-update-pulse {
      0% { transform: scale(1); }
      50% { transform: scale(1.01); }
      100% { transform: scale(1); }
    }
  `;
  document.head.appendChild(style);

})();

