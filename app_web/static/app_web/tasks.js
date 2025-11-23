// Tasks Page - Core JavaScript
// Handles CRUD operations, modals, filters, and search

(function() {
  'use strict';

  // Initialize on page load
  document.addEventListener('DOMContentLoaded', function() {
    initializeTaskPage();
  });

  function initializeTaskPage() {
    // Add view class to tasks container
    updateViewClass();

    // Initialize event listeners
    initializeSearch();
    initializeFilters();
    initializeCheckboxes();

    // Set up form submission
    const taskForm = document.getElementById('task-form');
    if (taskForm) {
      taskForm.addEventListener('submit', handleTaskSubmit);
    }
  }

  // Update tasks-container class based on current view
  function updateViewClass() {
    const container = document.querySelector('.tasks-container');
    if (!container) return;

    // Remove existing view classes
    container.classList.remove('view-table', 'view-kanban', 'view-roadmap');

    // Add current view class
    const currentView = window.currentView || 'table';
    container.classList.add(`view-${currentView}`);
  }

  // ========== MODAL FUNCTIONS ==========

  window.openTaskModal = function(defaultStatus = null) {
    const modal = document.getElementById('task-modal-backdrop');
    const form = document.getElementById('task-form');
    const title = document.getElementById('task-modal-title');

    // Reset form
    form.reset();
    document.getElementById('task-id').value = '';
    title.textContent = 'New Task';

    // Set default status if provided
    if (defaultStatus) {
      document.getElementById('task-status').value = defaultStatus;
    }

    modal.classList.add('active');
  };

  window.closeTaskModal = function() {
    const modal = document.getElementById('task-modal-backdrop');
    modal.classList.remove('active');
  };

  window.editTask = function(taskId) {
    // Fetch task data and populate form
    fetch(`/tasks/${taskId}/details/`)
      .then(response => response.json())
      .then(data => {
        populateTaskForm(data);
        document.getElementById('task-modal-title').textContent = 'Edit Task';
        document.getElementById('task-modal-backdrop').classList.add('active');
      })
      .catch(error => {
        console.error('Error loading task:', error);
        alert('Failed to load task details');
      });
  };

  function populateTaskForm(task) {
    document.getElementById('task-id').value = task.id;
    document.getElementById('task-title').value = task.title;
    document.getElementById('task-description').value = task.description || '';
    document.getElementById('task-status').value = task.status;
    document.getElementById('task-priority').value = task.priority;
    document.getElementById('task-assignee').value = task.assignee || '';
    document.getElementById('task-milestone').value = task.milestone || '';
    document.getElementById('task-start-date').value = task.start_date || '';
    document.getElementById('task-due-date').value = task.due_date || '';
    document.getElementById('task-estimated-hours').value = task.estimated_hours || '';
    document.getElementById('task-parent').value = task.parent_task || '';

    // Set labels
    const labelCheckboxes = document.querySelectorAll('input[name="labels"]');
    labelCheckboxes.forEach(checkbox => {
      checkbox.checked = task.labels.includes(parseInt(checkbox.value));
    });
  }

  window.openTaskDetails = function(taskId) {
    const modal = document.getElementById('task-details-modal-backdrop');
    const content = document.getElementById('task-details-content');

    content.innerHTML = '<div style="text-align: center; padding: 2rem;"><p>Loading...</p></div>';
    modal.classList.add('active');

    fetch(`/tasks/${taskId}/details/?full=true`)
      .then(response => response.json())
      .then(data => {
        renderTaskDetails(data);
      })
      .catch(error => {
        console.error('Error loading task details:', error);
        content.innerHTML = '<div style="text-align: center; padding: 2rem; color: #ef4444;"><p>Failed to load task details</p></div>';
      });
  };

  window.closeTaskDetailsModal = function() {
    const modal = document.getElementById('task-details-modal-backdrop');
    modal.classList.remove('active');
  };

  function renderTaskDetails(task) {
    const content = document.getElementById('task-details-content');
    const title = document.getElementById('task-details-title');

    title.textContent = `#${task.task_number} ${task.title}`;

    let html = `
      <div style="display: grid; gap: 1.5rem;">
        <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
          <span class="status-select status-${task.status}">${getStatusLabel(task.status)}</span>
          <span class="priority-badge priority-${task.priority}">${getPriorityIcon(task.priority)} ${task.priority_display}</span>
          ${task.assignee ? `<span class="assignee-info"><div class="assignee-avatar">${task.assignee.username[0].toUpperCase()}</div> ${task.assignee.display_name}</span>` : '<span class="text-muted">Unassigned</span>'}
        </div>
        
        ${task.description ? `<div><strong>Description:</strong><p style="margin-top: 0.5rem; color: #6b7280;">${task.description}</p></div>` : ''}
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
          ${task.due_date ? `<div><strong>Due Date:</strong><br>${task.due_date}</div>` : ''}
          ${task.estimated_hours ? `<div><strong>Estimated:</strong><br>${task.estimated_hours}h</div>` : ''}
          ${task.actual_hours ? `<div><strong>Actual:</strong><br>${task.actual_hours}h</div>` : ''}
          ${task.milestone ? `<div><strong>Milestone:</strong><br>${task.milestone_name}</div>` : ''}
        </div>
        
        ${task.labels && task.labels.length > 0 ? `
          <div>
            <strong>Labels:</strong>
            <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem; flex-wrap: wrap;">
              ${task.labels.map(label => `<span class="label-tag" style="background: ${label.color}20; color: ${label.color}; border: 1px solid ${label.color}40; padding: 0.25rem 0.75rem; border-radius: 8px; font-size: 0.875rem;">${label.name}</span>`).join('')}
            </div>
          </div>
        ` : ''}

        <!-- Sub-tasks Section -->
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <strong>Sub-tasks ${task.sub_tasks_count > 0 ? `(${task.completed_sub_tasks || 0}/${task.sub_tasks_count})` : ''}</strong>
            <button class="btn btn-sm btn-secondary" onclick="addSubTask(${task.id})">+ Add Sub-task</button>
          </div>
          <div id="sub-tasks-list" style="display: grid; gap: 0.5rem;">
            ${task.sub_tasks_count > 0 ? '<p style="color: #6b7280; font-size: 0.875rem;">Loading sub-tasks...</p>' : '<p style="color: #9ca3af; font-size: 0.875rem;">No sub-tasks yet</p>'}
          </div>
        </div>

        <!-- Comments Section -->
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <strong>Comments ${task.comments_count > 0 ? `(${task.comments_count})` : ''}</strong>
          </div>
          <div id="comments-list" style="display: grid; gap: 0.75rem; margin-bottom: 1rem;">
            ${task.comments_count > 0 ? '<p style="color: #6b7280; font-size: 0.875rem;">Loading comments...</p>' : '<p style="color: #9ca3af; font-size: 0.875rem;">No comments yet</p>'}
          </div>
          <div style="display: grid; gap: 0.5rem;">
            <div style="position: relative;">
              <textarea id="new-comment" rows="3" placeholder="Add a comment... (Use @ to mention someone)" style="width: 100%; padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.875rem; resize: vertical;"></textarea>
              <div id="mention-dropdown" style="display: none; position: absolute; bottom: 100%; left: 0; background: white; border: 1px solid #d1d5db; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); max-height: 200px; overflow-y: auto; z-index: 1000; min-width: 200px;"></div>
            </div>
            <div id="comment-error" style="display: none; color: #dc2626; font-size: 0.875rem; padding: 0.5rem; background: #fee2e2; border-radius: 6px; border: 1px solid #fca5a5;"></div>
            <button class="btn btn-primary" onclick="addComment(${task.id})">Add Comment</button>
          </div>
        </div>
        
        <div style="display: flex; gap: 0.5rem; padding-top: 1rem; border-top: 1px solid #e5e7eb;">
          <button class="btn btn-primary" onclick="editTask(${task.id})">Edit Task</button>
          <button class="btn btn-danger" onclick="deleteTask(${task.id}, '${task.title.replace(/'/g, "\\'")}')">Delete</button>
        </div>
      </div>
    `;

    content.innerHTML = html;

    // Load sub-tasks and comments if they exist
    if (task.sub_tasks_count > 0) {
      loadSubTasks(task.id);
    }
    if (task.comments_count > 0) {
      loadComments(task.id);
    }

    // Setup @mention functionality
    setupMentions(task.id);
  }

  // Setup @mention functionality
  function setupMentions(taskId) {
    const textarea = document.getElementById('new-comment');
    const dropdown = document.getElementById('mention-dropdown');

    if (!textarea || !dropdown) return;

    let teamMembers = [];

    // Fetch team members
    fetch(`/projects/${window.projectId}/tasks/`)
      .then(() => {
        // Get team members from the global context if available
        const membersSelect = document.getElementById('assignee-filter');
        if (membersSelect) {
          teamMembers = Array.from(membersSelect.options)
            .filter(opt => opt.value)
            .map(opt => ({
              id: opt.value,
              name: opt.textContent
            }));
        }
      });

    let mentionStartPos = -1;

    textarea.addEventListener('input', function(e) {
      const text = textarea.value;
      const cursorPos = textarea.selectionStart;

      // Find @ symbol before cursor
      let atPos = -1;
      for (let i = cursorPos - 1; i >= 0; i--) {
        if (text[i] === '@') {
          atPos = i;
          break;
        }
        if (text[i] === ' ' || text[i] === '\n') {
          break;
        }
      }

      if (atPos !== -1) {
        mentionStartPos = atPos;
        const query = text.substring(atPos + 1, cursorPos).toLowerCase();
        const filtered = teamMembers.filter(m =>
          m.name.toLowerCase().includes(query)
        );

        if (filtered.length > 0) {
          dropdown.innerHTML = filtered.map(m => `
            <div class="mention-item" data-id="${m.id}" data-name="${m.name}" 
                 style="padding: 0.5rem; cursor: pointer; font-size: 0.875rem;"
                 onmouseover="this.style.background='#f3f4f6'"
                 onmouseout="this.style.background='white'"
                 onclick="insertMention('${m.name}')">
              ${m.name}
            </div>
          `).join('');
          dropdown.style.display = 'block';
        } else {
          dropdown.style.display = 'none';
        }
      } else {
        dropdown.style.display = 'none';
        mentionStartPos = -1;
      }
    });

    window.insertMention = function(name) {
      const text = textarea.value;
      const before = text.substring(0, mentionStartPos);
      const after = text.substring(textarea.selectionStart);
      textarea.value = before + '@' + name + ' ' + after;
      dropdown.style.display = 'none';
      textarea.focus();
    };

    // Close dropdown on blur
    textarea.addEventListener('blur', function() {
      setTimeout(() => {
        dropdown.style.display = 'none';
      }, 200);
    });
  }

  // Load sub-tasks
  function loadSubTasks(taskId) {
    fetch(`/tasks/${taskId}/details/?full=true`)
      .then(response => response.json())
      .then(data => {
        const listEl = document.getElementById('sub-tasks-list');
        if (!listEl) return;

        if (data.sub_tasks && data.sub_tasks.length > 0) {
          listEl.innerHTML = data.sub_tasks.map(st => `
            <div style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem; border: 1px solid #e5e7eb; border-radius: 6px; background: #f9fafb;">
              <span style="flex: 1; font-size: 0.875rem; color: #111827;">#${st.task_number} ${st.title}</span>
              <span class="status-badge status-${st.status}" style="font-size: 0.75rem; padding: 0.125rem 0.5rem;">${st.status}</span>
              ${st.assignee ? `<span style="font-size: 0.75rem; color: #6b7280;">${st.assignee}</span>` : ''}
            </div>
          `).join('');
        } else {
          listEl.innerHTML = '<p style="color: #9ca3af; font-size: 0.875rem;">No sub-tasks yet</p>';
        }
      })
      .catch(error => console.error('Error loading sub-tasks:', error));
  }

  // Load comments
  function loadComments(taskId) {
    fetch(`/tasks/${taskId}/details/?full=true`)
      .then(response => response.json())
      .then(data => {
        const listEl = document.getElementById('comments-list');
        if (!listEl) return;

        if (data.comments && data.comments.length > 0) {
          listEl.innerHTML = data.comments.map(c => `
            <div style="padding: 0.75rem; border: 1px solid #e5e7eb; border-radius: 6px; background: #f9fafb;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <strong style="font-size: 0.875rem; color: #111827;">${c.user}</strong>
                <span style="font-size: 0.75rem; color: #6b7280;">${c.created_at}</span>
              </div>
              <p style="margin: 0; font-size: 0.875rem; color: #374151; white-space: pre-wrap;">${c.comment}</p>
            </div>
          `).join('');
        } else {
          listEl.innerHTML = '<p style="color: #9ca3af; font-size: 0.875rem;">No comments yet</p>';
        }
      })
      .catch(error => console.error('Error loading comments:', error));
  }

  // Add comment
  window.addComment = function(taskId) {
    const textarea = document.getElementById('new-comment');
    const errorEl = document.getElementById('comment-error');
    const comment = textarea.value.trim();

    // Clear any existing error first
    if (errorEl) {
      errorEl.style.display = 'none';
      errorEl.textContent = '';
    }

    if (!comment) {
      // Show inline error instead of alert
      if (errorEl) {
        errorEl.textContent = 'Comment cannot be empty';
        errorEl.style.display = 'block';
        setTimeout(() => {
          errorEl.style.display = 'none';
        }, 3000);
      }
      return;
    }

    // Show loading state
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = 'Adding...';
    btn.disabled = true;

    fetch(`/tasks/${taskId}/comments/create/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': window.csrfToken
      },
      body: `content=${encodeURIComponent(comment)}`
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Clear textarea and reload
        textarea.value = '';
        if (errorEl) {
          errorEl.style.display = 'none';
        }
        // Reload task details
        openTaskDetails(taskId);
      } else {
        // Show error
        btn.textContent = originalText;
        btn.disabled = false;
        if (errorEl) {
          errorEl.textContent = data.error || 'Failed to add comment';
          errorEl.style.display = 'block';
          setTimeout(() => {
            errorEl.style.display = 'none';
          }, 3000);
        }
      }
    })
    .catch(error => {
      console.error('Error adding comment:', error);
      btn.textContent = originalText;
      btn.disabled = false;
      if (errorEl) {
        errorEl.textContent = 'Failed to add comment. Please try again.';
        errorEl.style.display = 'block';
        setTimeout(() => {
          errorEl.style.display = 'none';
        }, 3000);
      }
    });
  };

  // Add sub-task
  window.addSubTask = function(parentTaskId) {
    openTaskModal('todo', parentTaskId);
  };

  function getStatusLabel(status) {
    const labels = {
      'backlog': '📝 Backlog',
      'todo': '📋 To Do',
      'in_progress': '⚡ In Progress',
      'review': '👀 Review',
      'done': '✅ Done',
      'blocked': '🚫 Blocked'
    };
    return labels[status] || status;
  }

  function getPriorityIcon(priority) {
    const icons = {
      'low': '🟢',
      'medium': '🟡',
      'high': '🟠',
      'critical': '🔴'
    };
    return icons[priority] || '';
  }

  // ========== FORM SUBMISSION ==========

  function handleTaskSubmit(e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);
    const taskId = formData.get('task_id');
    const url = taskId ? `/tasks/${taskId}/update/` : `/tasks/create/${window.projectId}/`;

    fetch(url, {
      method: 'POST',
      body: formData,
      headers: {
        'X-CSRFToken': window.csrfToken
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        closeTaskModal();
        window.location.reload();
      } else {
        alert(data.error || 'Failed to save task');
      }
    })
    .catch(error => {
      console.error('Error saving task:', error);
      alert('Failed to save task');
    });
  }

  // ========== TASK OPERATIONS ==========

  window.updateTaskStatus = function(taskId, newStatus) {
    fetch(`/tasks/${taskId}/status/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window.csrfToken
      },
      body: JSON.stringify({ status: newStatus })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Update UI without reload
        const row = document.querySelector(`tr[data-task-id="${taskId}"]`);
        if (row) {
          row.dataset.status = newStatus;
          const select = row.querySelector('.status-select');
          if (select) {
            select.className = `status-select status-${newStatus}`;
          }
        }
      } else {
        alert(data.error || 'Failed to update status');
      }
    })
    .catch(error => {
      console.error('Error updating status:', error);
      alert('Failed to update status');
    });
  };

  window.deleteTask = function(taskId, taskTitle) {
    if (!confirm(`Are you sure you want to delete "${taskTitle}"?`)) {
      return;
    }

    fetch(`/tasks/${taskId}/delete/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': window.csrfToken
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        window.location.reload();
      } else {
        alert(data.error || 'Failed to delete task');
      }
    })
    .catch(error => {
      console.error('Error deleting task:', error);
      alert('Failed to delete task');
    });
  };

  // ========== SEARCH & FILTERS ==========

  function initializeSearch() {
    const searchInput = document.getElementById('task-search');
    if (!searchInput) return;

    let searchTimeout;
    searchInput.addEventListener('input', function(e) {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        filterTasks();
      }, 300);
    });
  }

  function initializeFilters() {
    const filters = ['status-filter', 'priority-filter', 'assignee-filter'];
    filters.forEach(filterId => {
      const filter = document.getElementById(filterId);
      if (filter) {
        filter.addEventListener('change', filterTasks);
      }
    });
  }

  function filterTasks() {
    const searchTerm = document.getElementById('task-search')?.value.toLowerCase() || '';
    const statusFilter = document.getElementById('status-filter')?.value || '';
    const priorityFilter = document.getElementById('priority-filter')?.value || '';
    const assigneeFilter = document.getElementById('assignee-filter')?.value || '';

    const rows = document.querySelectorAll('.task-row');
    rows.forEach(row => {
      const title = row.querySelector('.task-title')?.textContent.toLowerCase() || '';
      const status = row.dataset.status || '';
      const priority = row.dataset.priority || '';
      const assigneeId = row.querySelector('.assignee-info')?.dataset.userId || '';

      const matchesSearch = !searchTerm || title.includes(searchTerm);
      const matchesStatus = !statusFilter || status === statusFilter;
      const matchesPriority = !priorityFilter || priority === priorityFilter;
      const matchesAssignee = !assigneeFilter || assigneeId === assigneeFilter;

      const matches = matchesSearch && matchesStatus && matchesPriority && matchesAssignee;
      row.style.display = matches ? '' : 'none';
    });
  }

  // ========== CHECKBOXES & BULK OPERATIONS ==========

  function initializeCheckboxes() {
    const selectAll = document.getElementById('select-all-tasks');
    if (selectAll) {
      selectAll.addEventListener('change', function(e) {
        toggleSelectAll(e.target);
      });
    }

    // Listen to individual checkboxes
    document.addEventListener('change', function(e) {
      if (e.target.classList.contains('task-checkbox')) {
        updateBulkButtons();
      }
    });
  }

  window.toggleSelectAll = function(checkbox) {
    const taskCheckboxes = document.querySelectorAll('.task-checkbox');
    taskCheckboxes.forEach(cb => {
      cb.checked = checkbox.checked;
    });
    updateBulkButtons();
  };

  function updateBulkButtons() {
    const checked = document.querySelectorAll('.task-checkbox:checked');
    const bulkAssignBtn = document.getElementById('bulk-assign-btn');
    const bulkStatusBtn = document.getElementById('bulk-status-btn');
    const bulkDeleteBtn = document.getElementById('bulk-delete-btn');

    const show = checked.length > 0;
    if (bulkAssignBtn) bulkAssignBtn.style.display = show ? '' : 'none';
    if (bulkStatusBtn) bulkStatusBtn.style.display = show ? '' : 'none';
    if (bulkDeleteBtn) bulkDeleteBtn.style.display = show ? '' : 'none';
  }

  window.bulkDelete = function() {
    const checked = Array.from(document.querySelectorAll('.task-checkbox:checked'));
    const taskIds = checked.map(cb => cb.value);

    if (taskIds.length === 0) return;

    if (!confirm(`Delete ${taskIds.length} task(s)?`)) return;

    fetch('/tasks/bulk-delete/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window.csrfToken
      },
      body: JSON.stringify({ task_ids: taskIds })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        window.location.reload();
      } else {
        alert(data.error || 'Failed to delete tasks');
      }
    })
    .catch(error => {
      console.error('Error deleting tasks:', error);
      alert('Failed to delete tasks');
    });
  };

  // ========== VIEW SWITCHING ==========

  window.switchView = function(view) {
    const currentUrl = new URL(window.location);
    currentUrl.searchParams.set('view', view);
    window.location.href = currentUrl.toString();
  };

})();

