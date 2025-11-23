// Projects JavaScript - Enhanced with Hierarchy Support

let projectsData = [];
let currentView = 'grid'; // 'grid' or 'tree'
let currentTab = 'overview';

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
  // Load projects data from template
  console.log('Loading projects data...');
  console.log('window.projectsData:', window.projectsData);

  if (window.projectsData) {
    try {
      projectsData = JSON.parse(window.projectsData);
      console.log('Parsed projects:', projectsData);
      console.log('Number of projects:', projectsData.length);
      renderProjects();
    } catch (error) {
      console.error('Error parsing projects data:', error);
      console.error('Raw data:', window.projectsData);
      // Show error message
      const container = document.getElementById('projects-container');
      if (container) {
        container.innerHTML = '<div class="alert alert-error">Error loading projects. Check console for details.</div>';
      }
    }
  } else {
    console.log('No projects data found in window.projectsData');
  }

  initializeDatePickers();
  initializeFilters();
  initializeSearch();
  initializeColorPicker();
  initializeParentProjectSync();
});

// Render projects in current view
function renderProjects() {
  console.log('renderProjects called');
  console.log('projectsData:', projectsData);
  console.log('currentView:', currentView);

  const container = document.getElementById('projects-container');
  const emptyState = document.getElementById('empty-state');

  console.log('container element:', container);
  console.log('emptyState element:', emptyState);

  if (!projectsData || projectsData.length === 0) {
    console.log('No projects data or empty array');
    container.innerHTML = '';
    if (emptyState) emptyState.style.display = 'block';
    return;
  }

  console.log('Rendering', projectsData.length, 'projects');
  if (emptyState) emptyState.style.display = 'none';

  if (currentView === 'tree') {
    console.log('Rendering tree view');
    renderTreeView(container, projectsData);
  } else {
    console.log('Rendering grid view');
    renderGridView(container, projectsData);
  }
  console.log('Render complete. Container innerHTML length:', container.innerHTML.length);
}

// Render grid view (flat list)
function renderGridView(container, projects) {
  let html = '';

  function renderProject(project) {
    const indentClass = `indent-level-${project.level}`;
    html += createProjectCard(project, indentClass);

    // Render sub-projects
    if (project.sub_projects && project.sub_projects.length > 0) {
      project.sub_projects.forEach(sub => renderProject(sub));
    }
  }

  projects.forEach(project => renderProject(project));
  container.innerHTML = html;
  container.className = 'projects-grid';
}

// Render tree view (hierarchical)
function renderTreeView(container, projects) {
  let html = '<div class="projects-tree">';

  function renderProjectNode(project, level = 0) {
    const hasChildren = project.sub_projects && project.sub_projects.length > 0;
    const expandedClass = hasChildren ? 'has-children' : '';
    const levelClass = level === 0 ? 'level-parent' : (level === 1 ? 'level-sub' : 'level-task');

    const expandIcon = `
      <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    `;

    html += `
      <div class="tree-node ${expandedClass} ${levelClass}" data-project-id="${project.id}" data-level="${level}">
        <div class="tree-node-header" onclick="navigateToProject(${project.id}, event)" style="cursor: pointer;">
          ${hasChildren ? `<button class="expand-btn" onclick="toggleNode(this); event.stopPropagation();">${expandIcon}</button>` : '<span class="no-children"></span>'}
          ${createProjectCardCompact(project)}
        </div>
        ${hasChildren ? '<div class="tree-node-children">' : ''}
    `;

    if (hasChildren) {
      project.sub_projects.forEach(sub => renderProjectNode(sub, level + 1));
      html += '</div>';
    }

    html += '</div>';
  }

  projects.forEach(project => renderProjectNode(project, 0));
  html += '</div>';

  container.innerHTML = html;
  container.className = 'projects-tree-container';
}

// Create project card HTML
function createProjectCard(project, indentClass = '') {
  const budgetProgress = project.budget_usage_pct || 0;
  const milestoneProgress = project.milestone_progress || 0;
  const hasSubProjects = project.sub_projects && project.sub_projects.length > 0;
  const levelClass = project.level === 0 ? 'level-parent' : (project.level === 1 ? 'level-sub' : 'level-task');

  // SVG Icons
  const viewIcon = `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const editIcon = `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const addIcon = `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const deleteIcon = `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><polyline points="3 6 5 6 21 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 11v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 11v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

  return `
    <div class="project-card ${indentClass} ${levelClass}" data-project-id="${project.id}" data-status="${project.status}" data-level="${project.level}" style="--project-color: ${project.color};">
      <div class="project-card-header">
        <input type="checkbox" class="project-checkbox" value="${project.id}" onchange="updateBulkDeleteButton()" onclick="event.stopPropagation()">
        <div class="project-color-indicator" style="background: ${project.color};"></div>
        <h3 class="project-name" onclick="navigateToProject(${project.id}, event)" style="cursor: pointer;">${project.name}</h3>
        ${hasSubProjects ? `<span class="sub-count">${project.sub_projects.length} sub</span>` : ''}
        <span class="project-status status-${project.status}">${project.status_display}</span>
      </div>

      <div class="project-card-body">
        ${project.description ? `<p class="project-description">${project.description}</p>` : ''}

        <div class="project-labels">
          ${project.labels && project.labels.length > 0 
            ? project.labels.map(label => `
                <span class="label-tag" style="background: ${label.color}20; color: ${label.color}; border: 1px solid ${label.color}40;">
                  ${label.name}
                </span>
              `).join('')
            : '<span class="text-muted">No labels assigned</span>'}
        </div>

        <div class="project-metrics">
          <div class="metric">
            <span class="metric-label">Budget</span>
            <span class="metric-value">${project.budget ? '£' + project.budget.toLocaleString() : '<span class="text-muted">Not set</span>'}</span>
          </div>
          <div class="metric">
            <span class="metric-label">Spent</span>
            <span class="metric-value ${budgetProgress > 100 ? 'text-danger' : ''}">£${project.total_outflow.toLocaleString()}</span>
          </div>
          <div class="metric">
            <span class="metric-label">Income</span>
            <span class="metric-value text-success">£${project.total_inflow.toLocaleString()}</span>
          </div>
          <div class="metric">
            <span class="metric-label">Net</span>
            <span class="metric-value ${project.net_amount >= 0 ? 'text-success' : 'text-danger'}">£${project.net_amount.toLocaleString()}</span>
          </div>
        </div>

        ${project.budget ? `
          <div class="budget-progress">
            <div class="budget-progress-bar">
              <div class="budget-progress-fill ${budgetProgress > 100 ? 'over-budget' : budgetProgress > 80 ? 'near-limit' : ''}" 
                   style="width: ${Math.min(budgetProgress, 100)}%;"></div>
            </div>
            <div class="budget-progress-text">
              <span>${budgetProgress.toFixed(0)}% Used</span>
              ${project.budget_variance !== null ? `
                <span class="${project.budget_variance < 0 ? 'text-danger' : 'text-success'}">
                  ${project.budget_variance < 0 ? 'Over' : 'Remaining'}: £${project.budget_variance_abs.toLocaleString()}
                </span>
              ` : ''}
            </div>
          </div>
        ` : ''}

        ${project.milestones_total > 0 ? `
          <div class="milestone-progress">
            <div class="milestone-progress-bar">
              <div class="milestone-progress-fill" style="width: ${milestoneProgress}%;"></div>
            </div>
            <span class="milestone-progress-text">${project.milestones_completed} / ${project.milestones_total} Milestones</span>
          </div>
        ` : ''}

        ${project.budget_categories && project.budget_categories.length > 0 ? `
          <div class="budget-categories-preview">
            <span class="categories-label">Budget Categories</span>
            ${project.budget_categories.slice(0, 3).map(cat => `
              <span class="category-tag" style="background: ${cat.color}20; color: ${cat.color}; border: 1px solid ${cat.color}40;">
                ${cat.name}: ${cat.usage_pct.toFixed(0)}%
              </span>
            `).join('')}
            ${project.budget_categories.length > 3 ? `<span class="text-muted">+${project.budget_categories.length - 3} more</span>` : ''}
          </div>
        ` : ''}
      </div>

      <div class="project-actions">
        <button class="btn-icon btn-icon-view" onclick="navigateToProject(${project.id}, event)" title="View Details">
          ${viewIcon}
        </button>
        <button class="btn-icon btn-icon-edit" onclick="openEditModal(${project.id}); event.stopPropagation();" title="Edit Project">
          ${editIcon}
        </button>
        ${project.level < 2 ? `
        <button class="btn-icon btn-icon-add" onclick="openAddSubProjectModal(${project.id}); event.stopPropagation();" title="Add Sub-Project">
          ${addIcon}
        </button>
        ` : ''}
        <button class="btn-icon btn-icon-delete" onclick="confirmDelete(${project.id}, '${project.name.replace(/'/g, "\\'")}'); event.stopPropagation();" title="Delete Project">
          ${deleteIcon}
        </button>
      </div>
    </div>
  `;
}

// Create compact project card for tree view
function createProjectCardCompact(project) {
  const budgetProgress = project.budget_usage_pct || 0;
  const progressClass = budgetProgress > 100 ? 'over-budget' : budgetProgress > 80 ? 'near-limit' : 'on-track';

  const viewIcon = `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const editIcon = `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const addIcon = `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

  return `
    <div class="project-card-compact" data-project-id="${project.id}">
      <div class="compact-header">
        <div class="project-color" style="background: ${project.color};"></div>
        <span class="project-name">${project.name}</span>
        <span class="project-status status-${project.status}">${project.status_display}</span>
      </div>
      <div class="compact-metrics">
        <span class="metric">Budget: £${project.budget ? project.budget.toLocaleString() : '0'}</span>
        <span class="metric ${progressClass}">Spent: £${project.total_outflow.toLocaleString()} (${budgetProgress.toFixed(0)}%)</span>
        <span class="metric ${project.net_amount >= 0 ? 'text-success' : 'text-danger'}">Net: £${project.net_amount.toLocaleString()}</span>
      </div>
      <div class="compact-actions">
        <button class="btn-icon btn-view" onclick="navigateToProject(${project.id}, event)" title="View Details">
          ${viewIcon}
        </button>
        <button class="btn-icon btn-edit" onclick="openEditModal(${project.id}); event.stopPropagation();" title="Edit">
          ${editIcon}
        </button>
        ${project.level < 2 ? `<button class="btn-icon btn-add" onclick="openAddSubProjectModal(${project.id}); event.stopPropagation();" title="Add Sub-Project">
          ${addIcon}
        </button>` : ''}
      </div>
    </div>
  `;
}

// Toggle between grid and tree view
function toggleView() {
  console.log('toggleView called, currentView before:', currentView);
  currentView = currentView === 'grid' ? 'tree' : 'grid';
  console.log('currentView after:', currentView);

  const viewBtn = document.getElementById('toggle-view-btn');

  console.log('viewBtn:', viewBtn);

  if (currentView === 'tree') {
    if (viewBtn) viewBtn.textContent = 'Grid View';
  } else {
    if (viewBtn) viewBtn.textContent = 'Tree View';
  }

  console.log('About to call renderProjects');
  renderProjects();
  console.log('renderProjects completed');
}

// Toggle tree node expansion
function toggleNode(btn) {
  const node = btn.closest('.tree-node');
  const children = node.querySelector('.tree-node-children');

  if (node.classList.contains('collapsed')) {
    node.classList.remove('collapsed');
    if (children) children.style.display = 'flex';
  } else {
    node.classList.add('collapsed');
    if (children) children.style.display = 'none';
  }
}

// Open add sub-project modal
function openAddSubProjectModal(parentId) {
  const modal = document.getElementById('project-modal');
  const form = document.getElementById('project-form');
  const title = document.getElementById('modal-title');
  const submitBtn = document.getElementById('submit-btn');
  const parentSelect = document.getElementById('parent-project');
  const parentHidden = document.getElementById('parent-project-hidden');

  // Reset form
  form.reset();
  document.getElementById('form-action').value = 'create';
  document.getElementById('form-project-id').value = '';

  // Set parent project in both hidden input and select
  if (parentHidden) {
    parentHidden.value = parentId;
  }
  parentSelect.value = parentId;
  parentSelect.disabled = true; // Lock the parent selection

  // Find parent project name
  const parentProject = findProjectById(parentId);
  const parentName = parentProject ? parentProject.name : 'Unknown';

  title.textContent = `Add Sub-Project to "${parentName}"`;
  submitBtn.textContent = 'Create Sub-Project';

  // Reset color and labels
  const defaultColor = '#3b82f6';
  document.getElementById('project-color').value = defaultColor;
  const colorPreview = document.getElementById('color-preview');
  if (colorPreview) {
    colorPreview.style.background = defaultColor;
  }

  document.querySelectorAll('.color-option').forEach(option => {
    if (option.getAttribute('data-color') === defaultColor) {
      option.classList.add('active');
    } else {
      option.classList.remove('active');
    }
  });

  document.querySelectorAll('.label-checkbox input[type="checkbox"]').forEach(cb => {
    cb.checked = false;
  });

  modal.classList.add('active');
}

// Find project by ID (recursive)
function findProjectById(id, projects = projectsData) {
  for (const project of projects) {
    if (project.id === id) return project;
    if (project.sub_projects) {
      const found = findProjectById(id, project.sub_projects);
      if (found) return found;
    }
  }
  return null;
}

// View project details with tabs
// Navigate to project detail page
function navigateToProject(projectId, event) {
  // Prevent navigation if clicking on buttons or checkboxes
  if (event && (event.target.tagName === 'BUTTON' || event.target.tagName === 'INPUT' || event.target.closest('button') || event.target.closest('.project-checkbox'))) {
    return;
  }
  window.location.href = `/projects/${projectId}/`;
}

// View project details (legacy - keeping for backward compatibility)
function viewProjectDetails(projectId) {
  navigateToProject(projectId);
}

// Old modal-based view function (replaced by navigation)
function viewProjectDetailsModal(projectId) {
  const modal = document.getElementById('details-modal');
  const content = document.getElementById('details-content');
  const projectName = document.getElementById('details-project-name');

  // Show loading state
  content.innerHTML = '<div class="loading">Loading project details...</div>';
  modal.classList.add('active');

  // Reset to overview tab
  currentTab = 'overview';
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelector('.tab-btn').classList.add('active');

  // Fetch project details
  fetch(`/api/project-detail/${projectId}/`)
    .then(response => response.json())
    .then(data => {
      if (data.ok) {
        displayProjectDetails(data);
      } else {
        content.innerHTML = '<div class="alert alert-error">Failed to load project details</div>';
      }
    })
    .catch(error => {
      console.error('Error fetching project details:', error);
      content.innerHTML = '<div class="alert alert-error">Failed to load project details</div>';
    });
}

// Switch between detail tabs
function switchTab(tabName) {
  currentTab = tabName;
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  event.target.classList.add('active');

  // Re-render content for current tab
  const content = document.getElementById('details-content');
  if (content.projectData) {
    renderTabContent(content.projectData, tabName);
  }
}

// Display project details
function displayProjectDetails(data) {
  const content = document.getElementById('details-content');
  const projectName = document.getElementById('details-project-name');

  projectName.textContent = data.project.name;
  content.projectData = data; // Store for tab switching

  renderTabContent(data, currentTab);
}

// Render tab content
function renderTabContent(data, tab) {
  const content = document.getElementById('details-content');

  switch(tab) {
    case 'overview':
      content.innerHTML = renderOverviewTab(data);
      break;
    case 'financials':
      content.innerHTML = renderFinancialsTab(data);
      break;
    case 'milestones':
      content.innerHTML = renderMilestonesTab(data);
      break;
    case 'categories':
      content.innerHTML = renderCategoriesTab(data);
      break;
    case 'activity':
      content.innerHTML = renderActivityTab(data);
      break;
  }
}

// Render overview tab
function renderOverviewTab(data) {
  const project = data.project;
  const pl = data.pl;

  return `
    <div class="overview-grid">
      <div class="overview-card">
        <h3>Project Information</h3>
        <div class="info-grid" style="display: flex; flex-wrap: wrap; gap: 1.5rem; align-items: center;">
          <div class="info-item" style="display: flex; gap: 0.5rem; align-items: center;">
            <span class="info-label">Status:</span>
            <span class="project-status status-${project.status}">${project.status}</span>
          </div>
          <div class="info-item" style="display: flex; gap: 0.5rem; align-items: center;">
            <span class="info-label">Level:</span>
            <span>${project.level === 0 ? 'Parent Project' : project.level === 1 ? 'Sub-Project' : 'Task'}</span>
          </div>
          ${project.start_date ? `
            <div class="info-item" style="display: flex; gap: 0.5rem; align-items: center;">
              <span class="info-label">Start Date:</span>
              <span>${new Date(project.start_date).toLocaleDateString()}</span>
            </div>
          ` : ''}
          ${project.end_date ? `
            <div class="info-item" style="display: flex; gap: 0.5rem; align-items: center;">
              <span class="info-label">End Date:</span>
              <span>${new Date(project.end_date).toLocaleDateString()}</span>
            </div>
          ` : ''}
        </div>
        ${project.description ? `<p class="project-description" style="margin-top: 1rem;">${project.description}</p>` : ''}
      </div>
      
      <div class="overview-card">
        <h3>Financial Summary</h3>
        <div class="metrics-grid" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;">
          <div class="metric-card">
            <span class="metric-label">Total Inflow</span>
            <span class="metric-value text-success">£${pl.total_inflow.toLocaleString()}</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Total Outflow</span>
            <span class="metric-value text-danger">£${pl.total_outflow.toLocaleString()}</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Net P&L</span>
            <span class="metric-value ${pl.net_profit >= 0 ? 'text-success' : 'text-danger'}">£${pl.net_profit.toLocaleString()}</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Profit Margin</span>
            <span class="metric-value">${pl.profit_margin_pct.toFixed(1)}%</span>
          </div>
        </div>
      </div>
      
      ${data.sub_projects && data.sub_projects.length > 0 ? `
        <div class="overview-card">
          <h3>Sub-Projects (${data.sub_projects.length})</h3>
          <div class="sub-projects-list">
            ${data.sub_projects.map(sub => `
              <div class="sub-project-item">
                <span class="sub-project-name">${sub.name}</span>
                <span class="sub-project-budget">£${(sub.budget || 0).toLocaleString()}</span>
                <span class="project-status status-${sub.status}">${sub.status}</span>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}
      
      ${data.milestones && data.milestones.length > 0 ? `
        <div class="overview-card">
          <h3>Milestones (${data.milestones.length})</h3>
          <div class="milestones-summary">
            ${data.milestones.slice(0, 5).map(m => `
              <div class="milestone-item status-${m.status}">
                <span class="milestone-name">${m.name}</span>
                <span class="milestone-date">${new Date(m.due_date).toLocaleDateString()}</span>
                <span class="milestone-status">${m.status_display}</span>
              </div>
            `).join('')}
            ${data.milestones.length > 5 ? `<p class="text-muted">+ ${data.milestones.length - 5} more milestones</p>` : ''}
          </div>
        </div>
      ` : ''}
    </div>
  `;
}

// Render financials tab
function renderFinancialsTab(data) {
  const pl = data.pl;

  return `
    <div class="financials-content">
      <div class="pl-section">
        <h3>Income Breakdown</h3>
        ${Object.keys(pl.inflow_by_label).length > 0 ? `
          <div class="breakdown-list">
            ${Object.entries(pl.inflow_by_label).map(([label, amount]) => `
              <div class="breakdown-item">
                <span class="breakdown-label">${label}</span>
                <span class="breakdown-amount text-success">£${amount.toLocaleString()}</span>
              </div>
            `).join('')}
          </div>
        ` : '<p class="text-muted">No income recorded</p>'}
      </div>
      
      <div class="pl-section">
        <h3>Expense Breakdown</h3>
        ${Object.keys(pl.outflow_by_label).length > 0 ? `
          <div class="breakdown-list">
            ${Object.entries(pl.outflow_by_label).map(([label, amount]) => `
              <div class="breakdown-item">
                <span class="breakdown-label">${label}</span>
                <span class="breakdown-amount text-danger">£${amount.toLocaleString()}</span>
              </div>
            `).join('')}
          </div>
        ` : '<p class="text-muted">No expenses recorded</p>'}
      </div>
      
      <div class="pl-section">
        <h3>Recent Transactions (${data.transaction_count} total)</h3>
        ${data.transactions && data.transactions.length > 0 ? `
          <div class="transactions-list">
            ${data.transactions.map(tx => `
              <div class="transaction-item">
                <div class="transaction-date">${new Date(tx.date).toLocaleDateString()}</div>
                <div class="transaction-description">${tx.description}</div>
                <div class="transaction-label" style="color: ${tx.label_color};">${tx.label}</div>
                <div class="transaction-amount ${tx.direction === 'inflow' ? 'text-success' : 'text-danger'}">
                  ${tx.direction === 'inflow' ? '+' : '-'}£${tx.amount.toFixed(2)}
                </div>
              </div>
            `).join('')}
          </div>
          ${data.transaction_count > 100 ? '<p class="text-muted">Showing 100 most recent transactions</p>' : ''}
        ` : '<p class="text-muted">No transactions yet</p>'}
      </div>
    </div>
  `;
}

// Render milestones tab
function renderMilestonesTab(data) {
  return `
    <div class="milestones-content">
      <div class="milestones-header">
        <h3>Project Milestones</h3>
        <button class="btn btn-sm btn-primary" onclick="alert('Add milestone feature coming soon!')">+ Add Milestone</button>
      </div>
      
      ${data.milestones && data.milestones.length > 0 ? `
        <div class="milestones-timeline">
          ${data.milestones.map(milestone => `
            <div class="milestone-card status-${milestone.status}">
              <div class="milestone-header">
                <div>
                  <h4>${milestone.name}</h4>
                  ${milestone.description ? `<p class="milestone-description">${milestone.description}</p>` : ''}
                </div>
                <span class="milestone-status-badge status-${milestone.status}">${milestone.status_display}</span>
              </div>
              <div class="milestone-details">
                <div class="milestone-detail">
                  <span class="detail-label">Due Date:</span>
                  <span>${new Date(milestone.due_date).toLocaleDateString()}</span>
                </div>
                ${milestone.completed_date ? `
                  <div class="milestone-detail">
                    <span class="detail-label">Completed:</span>
                    <span class="text-success">${new Date(milestone.completed_date).toLocaleDateString()}</span>
                  </div>
                ` : ''}
                ${milestone.budget ? `
                  <div class="milestone-detail">
                    <span class="detail-label">Budget:</span>
                    <span>£${milestone.budget.toLocaleString()}</span>
                  </div>
                ` : ''}
                ${milestone.owner ? `
                  <div class="milestone-detail">
                    <span class="detail-label">Owner:</span>
                    <span>${milestone.owner}</span>
                  </div>
                ` : ''}
              </div>
            </div>
          `).join('')}
        </div>
      ` : `
        <div class="empty-state-small">
          <p>No milestones yet. Add milestones to track project deliverables and progress.</p>
          <button class="btn btn-primary" onclick="alert('Add milestone feature coming soon!')">+ Add First Milestone</button>
        </div>
      `}
    </div>
  `;
}

// Render budget categories tab
function renderCategoriesTab(data) {
  return `
    <div class="categories-content">
      <div class="categories-header">
        <h3>Budget Categories</h3>
        <button class="btn btn-sm btn-primary" onclick="alert('Add category feature coming soon!')">+ Add Category</button>
      </div>
      
      ${data.budget_categories && data.budget_categories.length > 0 ? `
        <div class="categories-grid">
          ${data.budget_categories.map(category => `
            <div class="category-card">
              <div class="category-header" style="border-left: 4px solid ${category.color};">
                <h4>${category.name}</h4>
              </div>
              <div class="category-metrics">
                <div class="category-metric">
                  <span class="metric-label">Allocated:</span>
                  <span class="metric-value">£${category.allocated.toLocaleString()}</span>
                </div>
                <div class="category-metric">
                  <span class="metric-label">Spent:</span>
                  <span class="metric-value">£${category.spent.toLocaleString()}</span>
                </div>
                <div class="category-metric">
                  <span class="metric-label">Remaining:</span>
                  <span class="metric-value ${category.remaining < 0 ? 'text-danger' : 'text-success'}">£${category.remaining.toLocaleString()}</span>
                </div>
              </div>
              <div class="category-progress">
                <div class="category-progress-bar">
                  <div class="category-progress-fill ${category.usage_pct > 100 ? 'over-budget' : category.usage_pct > 80 ? 'near-limit' : ''}" 
                       style="width: ${Math.min(category.usage_pct, 100)}%; background: ${category.color};"></div>
                </div>
                <span class="category-progress-text">${category.usage_pct.toFixed(0)}% used</span>
              </div>
            </div>
          `).join('')}
        </div>
      ` : `
        <div class="empty-state-small">
          <p>No budget categories yet. Add categories to track different types of spending (Labor, Materials, etc.).</p>
          <button class="btn btn-primary" onclick="alert('Add category feature coming soon!')">+ Add First Category</button>
        </div>
      `}
    </div>
  `;
}

// Render activity tab
function renderActivityTab(data) {
  return `
    <div class="activity-content">
      <h3>Activity Feed</h3>
      
      ${data.activities && data.activities.length > 0 ? `
        <div class="activity-feed">
          ${data.activities.map(activity => `
            <div class="activity-item">
              <div class="activity-icon">${getActivityIcon(activity.action)}</div>
              <div class="activity-details">
                <div class="activity-description">${activity.description}</div>
                <div class="activity-meta">
                  <span class="activity-user">${activity.user}</span>
                  <span class="activity-time">${formatRelativeTime(activity.created_at)}</span>
                </div>
              </div>
            </div>
          `).join('')}
        </div>
      ` : `
        <div class="empty-state-small">
          <p>No activity yet.</p>
        </div>
      `}
    </div>
  `;
}

// Get icon for activity type
function getActivityIcon(action) {
  const icons = {
    'created': 'Created',
    'updated': 'Updated',
    'deleted': 'Deleted',
    'status_changed': 'Status',
    'budget_changed': 'Budget',
    'milestone_added': 'Milestone',
    'milestone_completed': 'Complete',
    'sub_project_added': 'Sub-Project',
    'transaction_added': 'Transaction'
  };
  return icons[action] || 'Activity';
}

// Format relative time
function formatRelativeTime(isoString) {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  return date.toLocaleDateString();
}

// Initialize Flatpickr date pickers
function initializeDatePickers() {
  const dateInputs = document.querySelectorAll('.date-picker');
  dateInputs.forEach(input => {
    flatpickr(input, {
      dateFormat: 'Y-m-d',
      allowInput: true,
    });
  });
}

// Initialize filters
function initializeFilters() {
  const statusFilter = document.getElementById('filter-status');
  const levelFilter = document.getElementById('filter-level');

  if (statusFilter) {
    statusFilter.addEventListener('change', filterProjects);
  }

  if (levelFilter) {
    levelFilter.addEventListener('change', filterProjects);
  }
}

// Initialize search
function initializeSearch() {
  const searchInput = document.getElementById('search-input');
  if (searchInput) {
    searchInput.addEventListener('input', filterProjects);
  }
}

// Filter projects
function filterProjects() {
  const statusFilter = document.getElementById('filter-status').value;
  const levelFilter = document.getElementById('filter-level').value;
  const searchQuery = document.getElementById('search-input').value.toLowerCase();
  const projectCards = document.querySelectorAll('.project-card');

  projectCards.forEach(card => {
    const status = card.dataset.status;
    const level = card.dataset.level;
    const name = card.querySelector('.project-name')?.textContent.toLowerCase() || '';
    const description = card.querySelector('.project-description')?.textContent.toLowerCase() || '';

    let showStatus = statusFilter === 'all' || status === statusFilter;
    let showLevel = levelFilter === 'all' || level === levelFilter;
    let showSearch = searchQuery === '' || name.includes(searchQuery) || description.includes(searchQuery);

    if (showStatus && showLevel && showSearch) {
      card.style.display = '';
    } else {
      card.style.display = 'none';
    }
  });
}

// Initialize color picker
function initializeColorPicker() {
  const colorOptions = document.querySelectorAll('.color-option');
  const colorInput = document.getElementById('project-color');
  const colorPreview = document.getElementById('color-preview');

  if (!colorOptions.length || !colorInput || !colorPreview) return;

  colorOptions.forEach(option => {
    option.addEventListener('click', function(e) {
      e.preventDefault();
      const color = this.getAttribute('data-color');

      colorInput.value = color;
      colorPreview.style.background = color;

      colorOptions.forEach(opt => opt.classList.remove('active'));
      this.classList.add('active');
    });
  });

  // Set initial active state
  const currentColor = colorInput.value;
  colorOptions.forEach(option => {
    if (option.getAttribute('data-color') === currentColor) {
      option.classList.add('active');
    }
  });
}

// Initialize parent project sync
function initializeParentProjectSync() {
  const parentSelect = document.getElementById('parent-project');
  const parentHidden = document.getElementById('parent-project-hidden');

  if (parentSelect && parentHidden) {
    parentSelect.addEventListener('change', function() {
      parentHidden.value = this.value;
    });
  }
}

// Open Add Project Modal
function openAddProjectModal() {
  const modal = document.getElementById('project-modal');
  const form = document.getElementById('project-form');
  const title = document.getElementById('modal-title');
  const submitBtn = document.getElementById('submit-btn');
  const parentSelect = document.getElementById('parent-project');
  const parentHidden = document.getElementById('parent-project-hidden');

  form.reset();
  document.getElementById('form-action').value = 'create';
  document.getElementById('form-project-id').value = '';
  title.textContent = 'Add New Project';
  submitBtn.textContent = 'Create Project';

  // Enable parent selection and clear hidden input
  if (parentSelect) {
    parentSelect.disabled = false;
    parentSelect.value = '';
  }
  if (parentHidden) {
    parentHidden.value = '';
  }

  document.querySelectorAll('.label-checkbox input[type="checkbox"]').forEach(cb => {
    cb.checked = false;
  });

  const defaultColor = '#3b82f6';
  document.getElementById('project-color').value = defaultColor;
  const colorPreview = document.getElementById('color-preview');
  if (colorPreview) {
    colorPreview.style.background = defaultColor;
  }

  document.querySelectorAll('.color-option').forEach(option => {
    if (option.getAttribute('data-color') === defaultColor) {
      option.classList.add('active');
    } else {
      option.classList.remove('active');
    }
  });

  modal.classList.add('active');
}

// Open Edit Modal
function openEditModal(projectId) {
  const modal = document.getElementById('project-modal');
  const form = document.getElementById('project-form');
  const title = document.getElementById('modal-title');
  const submitBtn = document.getElementById('submit-btn');
  const parentSelect = document.getElementById('parent-project');

  document.getElementById('form-action').value = 'edit';
  document.getElementById('form-project-id').value = projectId;
  title.textContent = 'Edit Project';
  submitBtn.textContent = 'Save Changes';

  // Disable parent selection when editing
  if (parentSelect) {
    parentSelect.disabled = true;
  }

  fetch(`/api/project-detail/${projectId}/`)
    .then(response => response.json())
    .then(data => {
      if (data.ok) {
        const project = data.project;

        document.getElementById('project-name').value = project.name;
        document.getElementById('project-description').value = project.description || '';
        document.getElementById('project-budget').value = project.budget || '';
        document.getElementById('project-status').value = project.status;
        document.getElementById('project-color').value = project.color;

        const colorPreview = document.getElementById('color-preview');
        if (colorPreview) {
          colorPreview.style.background = project.color;
        }

        document.querySelectorAll('.color-option').forEach(option => {
          if (option.getAttribute('data-color') === project.color) {
            option.classList.add('active');
          } else {
            option.classList.remove('active');
          }
        });

        if (project.start_date) {
          const startPicker = document.getElementById('project-start-date')._flatpickr;
          if (startPicker) startPicker.setDate(project.start_date);
        }
        if (project.end_date) {
          const endPicker = document.getElementById('project-end-date')._flatpickr;
          if (endPicker) endPicker.setDate(project.end_date);
        }

        const labelIds = project.label_ids || [];
        document.querySelectorAll('.label-checkbox input[type="checkbox"]').forEach(cb => {
          cb.checked = labelIds.includes(parseInt(cb.value));
        });

        modal.classList.add('active');
      } else {
        alert('Error loading project data');
      }
    })
    .catch(error => {
      console.error('Error fetching project:', error);
      alert('Failed to load project data');
    });
}

// Close Project Modal
function closeProjectModal() {
  const modal = document.getElementById('project-modal');
  modal.classList.remove('active');
}

// Close Details Modal
function closeDetailsModal() {
  const modal = document.getElementById('details-modal');
  modal.classList.remove('active');
}

// Confirm Delete
function confirmDelete(projectId, projectName) {
  if (confirm(`Are you sure you want to delete the project "${projectName}"? This action cannot be undone.`)) {
    deleteProject(projectId);
  }
}

// Delete Project
function deleteProject(projectId) {
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

  fetch(window.location.href, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'X-CSRFToken': csrfToken,
    },
    body: `action=delete&project_id=${projectId}`
  })
  .then(response => response.json())
  .then(data => {
    if (data.ok) {
      window.location.reload();
    } else {
      alert('Error: ' + data.error);
    }
  })
  .catch(error => {
    console.error('Error deleting project:', error);
    alert('Failed to delete project');
  });
}

// Bulk Delete
function updateBulkDeleteButton() {
  const checkboxes = document.querySelectorAll('.project-checkbox:checked');
  const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
  const selectedCount = document.getElementById('selected-count');

  if (checkboxes.length > 0) {
    bulkDeleteBtn.style.display = 'block';
    selectedCount.textContent = checkboxes.length;
  } else {
    bulkDeleteBtn.style.display = 'none';
  }
}

function confirmBulkDelete() {
  const checkboxes = document.querySelectorAll('.project-checkbox:checked');
  const count = checkboxes.length;

  if (count === 0) return;

  if (confirm(`Are you sure you want to delete ${count} project(s)? This action cannot be undone.`)) {
    const projectIds = Array.from(checkboxes).map(cb => cb.value);
    bulkDeleteProjects(projectIds);
  }
}

function bulkDeleteProjects(projectIds) {
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
  const formData = new URLSearchParams();
  formData.append('action', 'bulk_delete');
  projectIds.forEach(id => formData.append('project_ids[]', id));

  fetch(window.location.href, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'X-CSRFToken': csrfToken,
    },
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    if (data.ok) {
      window.location.reload();
    } else {
      alert('Error: ' + data.error);
    }
  })
  .catch(error => {
    console.error('Error deleting projects:', error);
    alert('Failed to delete projects');
  });
}

// Form submission
document.getElementById('project-form')?.addEventListener('submit', function(e) {
  e.preventDefault();

  const formData = new FormData(this);
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

  fetch(window.location.href, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken,
    },
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    if (data.ok) {
      closeProjectModal();
      window.location.reload();
    } else {
      alert('Error: ' + data.error);
    }
  })
  .catch(error => {
    console.error('Error saving project:', error);
    alert('Failed to save project');
  });
});

// Close modals when clicking outside
document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
  backdrop.addEventListener('click', function(e) {
    if (e.target === this) {
      this.classList.remove('active');
    }
  });
});

