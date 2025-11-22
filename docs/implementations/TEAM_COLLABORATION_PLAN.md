# Team Collaboration - Implementation Plan

**Feature**: Team Collaboration  
**Start Date**: November 20, 2025  
**Status**: 🚧 IN PROGRESS

---

## 🎯 Overview

Transform the app from single-user to multi-user with organization-based access control, custom roles, approval workflows, and team management.

---

## 🏗️ Architecture

### Current (Single User):
```
User
  └── Transactions (personal)
  └── Budgets (personal)
  └── Projects (personal)
  └── Invoices (personal)
```

### New (Multi-Tenant):
```
Organization
  ├── Members (Users with custom roles)
  ├── Shared Transactions
  ├── Shared Budgets
  ├── Shared Projects
  ├── Shared Invoices
  ├── Approval Workflows
  └── Activity Log
```

---

## 🗄️ Database Models

### 1. Organization Model
```python
class Organization(models.Model):
    """Company/Team that owns financial data"""
    name = models.CharField(max_length=128)
    slug = models.SlugField(unique=True)
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='owned_organizations')
    
    # Settings
    currency = models.CharField(max_length=3, default='GBP')
    fiscal_year_start = models.IntegerField(default=4)  # April
    timezone = models.CharField(max_length=50, default='Europe/London')
    
    # Billing (future)
    plan = models.CharField(max_length=20, default='free')
    max_users = models.IntegerField(default=1)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 2. Custom Role Model
```python
class OrganizationRole(models.Model):
    """Custom roles with flexible naming and permissions"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='roles')
    name = models.CharField(max_length=64)  # e.g., "Accountant", "Project Manager", "Viewer"
    description = models.TextField(blank=True)
    
    # Built-in roles (cannot be deleted)
    is_owner = models.BooleanField(default=False)
    is_system = models.BooleanField(default=False)  # Owner, Admin (system roles)
    
    # Permissions
    can_manage_organization = models.BooleanField(default=False)
    can_manage_members = models.BooleanField(default=False)
    can_manage_roles = models.BooleanField(default=False)
    
    # Transactions
    can_view_transactions = models.BooleanField(default=True)
    can_create_transactions = models.BooleanField(default=False)
    can_edit_transactions = models.BooleanField(default=False)
    can_delete_transactions = models.BooleanField(default=False)
    can_export_transactions = models.BooleanField(default=False)
    
    # Budgets
    can_view_budgets = models.BooleanField(default=True)
    can_create_budgets = models.BooleanField(default=False)
    can_edit_budgets = models.BooleanField(default=False)
    can_delete_budgets = models.BooleanField(default=False)
    
    # Projects
    can_view_projects = models.BooleanField(default=True)
    can_create_projects = models.BooleanField(default=False)
    can_edit_projects = models.BooleanField(default=False)
    can_delete_projects = models.BooleanField(default=False)
    
    # Invoices
    can_view_invoices = models.BooleanField(default=True)
    can_create_invoices = models.BooleanField(default=False)
    can_edit_invoices = models.BooleanField(default=False)
    can_delete_invoices = models.BooleanField(default=False)
    can_send_invoices = models.BooleanField(default=False)
    
    # Reports
    can_view_reports = models.BooleanField(default=True)
    can_export_reports = models.BooleanField(default=False)
    
    # Approvals
    can_approve_transactions = models.BooleanField(default=False)
    can_approve_budgets = models.BooleanField(default=False)
    can_approve_expenses = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['organization', 'name']
        ordering = ['name']
```

### 3. Organization Member Model
```python
class OrganizationMember(models.Model):
    """Links Users to Organizations with roles"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organization_memberships')
    role = models.ForeignKey(OrganizationRole, on_delete=models.PROTECT, related_name='members')
    
    # Invitation
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_invitations')
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['organization', 'user']
        indexes = [
            models.Index(fields=['organization', 'user']),
            models.Index(fields=['user', 'is_active']),
        ]
```

### 4. Temporary Permission Request Model
```python
class PermissionRequest(models.Model):
    """Request temporary elevated permissions"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='permission_requests')
    member = models.ForeignKey(OrganizationMember, on_delete=models.CASCADE, related_name='permission_requests')
    
    # What permissions are being requested
    permissions = models.JSONField()  # e.g., {"can_delete_transactions": true, "can_approve_budgets": true}
    
    # Duration
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    
    # Approval
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_permission_requests')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['organization', 'status', '-created_at']),
            models.Index(fields=['member', 'status']),
        ]
        ordering = ['-created_at']
```

### 5. Approval Workflow Model
```python
class ApprovalWorkflow(models.Model):
    """Define what needs approval and who approves"""
    
    ENTITY_TYPES = [
        ('transaction', 'Transaction'),
        ('budget', 'Budget'),
        ('expense_claim', 'Expense Claim'),
        ('invoice', 'Invoice'),
    ]
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='approval_workflows')
    name = models.CharField(max_length=128)
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPES)
    
    # Conditions (when approval is needed)
    min_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    labels = models.ManyToManyField('Label', blank=True)  # Specific categories
    
    # Approvers
    approver_roles = models.ManyToManyField(OrganizationRole, related_name='approval_workflows')
    approvals_required = models.IntegerField(default=1)  # How many approvals needed
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']

class Approval(models.Model):
    """Track individual approval requests"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    workflow = models.ForeignKey(ApprovalWorkflow, on_delete=models.CASCADE, related_name='approvals')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    
    # What's being approved
    entity_type = models.CharField(max_length=20)
    entity_id = models.IntegerField()
    entity_description = models.CharField(max_length=512)  # e.g., "Transaction: Office Supplies - £500"
    
    # Requester
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='approval_requests')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Approvers
    approved_by = models.ManyToManyField(User, blank=True, related_name='approvals_given')
    rejected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approvals_rejected')
    rejection_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['organization', 'status', '-created_at']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['requested_by', 'status']),
        ]
        ordering = ['-created_at']
```

### 6. Activity Log Model
```python
class ActivityLog(models.Model):
    """Audit trail of all actions"""
    
    ACTION_TYPES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('delete', 'Deleted'),
        ('view', 'Viewed'),
        ('export', 'Exported'),
        ('invite', 'Invited'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('login', 'Logged In'),
        ('logout', 'Logged Out'),
    ]
    
    ENTITY_TYPES = [
        ('transaction', 'Transaction'),
        ('budget', 'Budget'),
        ('project', 'Project'),
        ('invoice', 'Invoice'),
        ('member', 'Team Member'),
        ('role', 'Role'),
        ('label', 'Label'),
        ('approval', 'Approval'),
    ]
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='activity_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='activities')
    
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPES, blank=True)
    entity_id = models.IntegerField(null=True, blank=True)
    
    description = models.CharField(max_length=512)
    metadata = models.JSONField(default=dict, blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['organization', '-created_at']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['user', '-created_at']),
        ]
        ordering = ['-created_at']
```

---

## 🔄 Migration Strategy

### Update Existing Models:
Add `organization` field to:
- Transaction
- Budget
- Project
- Invoice
- Client
- Label

### Migration Steps:
1. Add nullable `organization` field to all models
2. Create "Personal" organization for each existing user
3. Assign all existing data to user's personal organization
4. Create default "Owner" role for each organization
5. Make organization field required (non-nullable)

---

## 🎨 UI Components

### 1. User Dropdown (Top Right)
**Location**: Navigation bar, top right  
**Trigger**: Click on user avatar/name

**Structure**:
```
┌────────────────────────────┐
│ [Avatar] John Smith        │
├────────────────────────────┤
│ My Profile                 │
│ Switch Organization ▶      │
│ Team Dashboard             │
│ Activity Log               │
│ Settings                   │
├────────────────────────────┤
│ Logout                     │
└────────────────────────────┘

Switch Organization Submenu:
┌────────────────────────────┐
│ Personal                   │
│ ✓ Acme Corp (Owner)        │
│ Startup LLC (Admin)        │
├────────────────────────────┤
│ + Create Organization      │
└────────────────────────────┘
```

### 2. Team/Organization Page (`/team/`)
**Layout**: Left sidebar navigation + main content area

**Left Sidebar**:
- Overview (Dashboard)
- Members
- Roles & Permissions
- Approval Requests
- Activity Log
- Settings

**Main Content**: Dynamic based on selection

---

## 📋 Features to Implement

### ✅ Phase 1: Foundation (Week 1)
- [x] Design database models
- [ ] Create migration files
- [ ] Run migrations
- [ ] Create default roles (Owner, Admin, Viewer)
- [ ] Migrate existing data to personal organizations
- [ ] Add organization context middleware

### ✅ Phase 2: Team Management (Week 1-2)
- [ ] Team page with left sidebar
- [ ] Members list view
- [ ] Invite member modal
- [ ] Custom roles CRUD
- [ ] Permission matrix UI
- [ ] Role assignment

### ✅ Phase 3: Navigation & Switching (Week 2)
- [ ] User dropdown with org switcher
- [ ] Organization selection persistence
- [ ] Update all views with org context
- [ ] Permission checks in views

### ✅ Phase 4: Approvals (Week 2-3)
- [ ] Approval workflow setup
- [ ] Approval request creation
- [ ] Approval dashboard
- [ ] Approve/reject functionality
- [ ] Email notifications

### ✅ Phase 5: Permission Requests (Week 3)
- [ ] Temporary permission request form
- [ ] Request approval workflow
- [ ] Auto-expire permissions
- [ ] Request history

### ✅ Phase 6: Activity Log (Week 3-4)
- [ ] Activity logging middleware
- [ ] Activity log viewer
- [ ] Filters and search
- [ ] Export capability

### ✅ Phase 7: Team Dashboard (Week 4)
- [ ] Team-wide KPIs
- [ ] Member activity summary
- [ ] Pending approvals widget
- [ ] Recent activity feed

---

## 🔐 Permission Matrix

### System Roles:

| Permission | Owner | Admin | Viewer |
|-----------|-------|-------|--------|
| Manage Organization | ✅ | ❌ | ❌ |
| Manage Members | ✅ | ✅ | ❌ |
| Manage Roles | ✅ | ✅ | ❌ |
| View All Data | ✅ | ✅ | ✅ |
| Create/Edit | ✅ | ✅ | ❌ |
| Delete | ✅ | ✅ | ❌ |
| Export | ✅ | ✅ | ❌ |
| Approve | ✅ | ✅ | ❌ |

**Note**: Custom roles can have any combination of permissions

---

## 🚀 Next Steps

1. ✅ Review and approve plan
2. Create database models
3. Create migrations
4. Build team page structure
5. Implement org switcher
6. Add permission system

---

**Status**: Ready to implement Phase 1! 🚀

