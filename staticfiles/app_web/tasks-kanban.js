// Kanban Board - Drag and Drop Functionality

(function() {
  'use strict';

  let draggedElement = null;
  let draggedTaskId = null;

  // Initialize on page load
  document.addEventListener('DOMContentLoaded', function() {
    if (window.currentView === 'kanban') {
      initializeKanban();
    }
  });

  function initializeKanban() {
    setupDragAndDrop();
  }

  function setupDragAndDrop() {
    // Set up drag events for all task cards
    const cards = document.querySelectorAll('.task-card');
    cards.forEach(card => {
      card.addEventListener('dragstart', handleDragStart);
      card.addEventListener('dragend', handleDragEnd);
    });

    // Set up drop zones for all kanban columns
    const columns = document.querySelectorAll('.kanban-cards');
    columns.forEach(column => {
      column.addEventListener('dragover', handleDragOver);
      column.addEventListener('drop', handleDrop);
      column.addEventListener('dragenter', handleDragEnter);
      column.addEventListener('dragleave', handleDragLeave);
    });
  }

  window.handleDragStart = function(e) {
    draggedElement = e.target;
    draggedTaskId = e.target.dataset.taskId;

    e.target.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', e.target.innerHTML);
  };

  window.handleDragEnd = function(e) {
    e.target.classList.remove('dragging');

    // Remove hover states from all columns
    const columns = document.querySelectorAll('.kanban-cards');
    columns.forEach(column => {
      column.classList.remove('drag-over');
    });
  };

  function handleDragOver(e) {
    if (e.preventDefault) {
      e.preventDefault();
    }

    e.dataTransfer.dropEffect = 'move';
    return false;
  };

  function handleDragEnter(e) {
    if (e.target.classList.contains('kanban-cards')) {
      e.target.classList.add('drag-over');
    }
  };

  function handleDragLeave(e) {
    if (e.target.classList.contains('kanban-cards')) {
      e.target.classList.remove('drag-over');
    }
  };

  function handleDrop(e) {
    if (e.stopPropagation) {
      e.stopPropagation();
    }

    e.target.classList.remove('drag-over');

    const dropZone = e.target.closest('.kanban-cards');
    if (!dropZone || !draggedElement) return false;

    const newStatus = dropZone.dataset.status;
    const oldColumn = draggedElement.closest('.kanban-cards');

    // Move the card visually
    dropZone.appendChild(draggedElement);

    // Update task status on backend
    updateTaskStatusKanban(draggedTaskId, newStatus, oldColumn, dropZone);

    return false;
  };

  function updateTaskStatusKanban(taskId, newStatus, oldColumn, newColumn) {
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
        // Update column counts
        updateColumnCount(oldColumn);
        updateColumnCount(newColumn);

        // Show success feedback
        showNotification('Task moved successfully', 'success');
      } else {
        // Revert the move if it failed
        oldColumn.appendChild(draggedElement);
        showNotification(data.error || 'Failed to update task', 'error');
      }
    })
    .catch(error => {
      console.error('Error updating task:', error);
      // Revert the move
      oldColumn.appendChild(draggedElement);
      showNotification('Failed to update task', 'error');
    });
  }

  function updateColumnCount(column) {
    if (!column) return;

    const kanbanColumn = column.closest('.kanban-column');
    if (!kanbanColumn) return;

    const countBadge = kanbanColumn.querySelector('.task-count');
    if (!countBadge) return;

    const cardCount = column.querySelectorAll('.task-card').length;
    countBadge.textContent = cardCount;
  }

  function showNotification(message, type = 'info') {
    // Simple notification system
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 1rem 1.5rem;
      background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
      color: white;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      z-index: 10000;
      animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
      notification.style.animation = 'slideOut 0.3s ease';
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  // Add CSS animations
  const style = document.createElement('style');
  style.textContent = `
    @keyframes slideIn {
      from {
        transform: translateX(400px);
        opacity: 0;
      }
      to {
        transform: translateX(0);
        opacity: 1;
      }
    }
    
    @keyframes slideOut {
      from {
        transform: translateX(0);
        opacity: 1;
      }
      to {
        transform: translateX(400px);
        opacity: 0;
      }
    }
    
    .kanban-cards.drag-over {
      background: #eff6ff;
      border: 2px dashed #3b82f6;
      border-radius: 8px;
    }
  `;
  document.head.appendChild(style);

})();

