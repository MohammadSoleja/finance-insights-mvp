# app_core/team_models.py
"""
Team Collaboration Models
- Organizations (multi-tenant)
- Custom Roles & Permissions
- Team Members
- Approval Workflows
- Activity Logging
- Permission Requests
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Organization(models.Model):
    """
    Company/Team that owns financial data.
    Multi-tenant support - all data belongs to an organization.
    """
    name = models.CharField(max_length=128, help_text="Organization name (e.g., 'Acme Corp')")
    slug = models.SlugField(unique=True, help_text="URL-friendly identifier")
    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='owned_organizations',
        help_text="Organization owner (cannot be deleted while org exists)"
    )

    # Settings
    currency = models.CharField(max_length=3, default='GBP', help_text="Default currency code")
    fiscal_year_start = models.IntegerField(default=4, help_text="Fiscal year start month (1-12)")
    timezone = models.CharField(max_length=50, default='Europe/London')

    # Billing & Limits (for future subscription system)
    plan = models.CharField(
        max_length=20,
        default='free',
        choices=[
            ('free', 'Free'),
            ('professional', 'Professional'),
            ('enterprise', 'Enterprise'),
        ]
    )
    max_users = models.IntegerField(default=1, help_text="Maximum team members allowed")

    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['owner']),
        ]

    def __str__(self):
        return self.name

    def get_member_count(self):
        """Get current number of active members"""
        return self.members.filter(is_active=True).count()

    def can_add_member(self):
        """Check if organization can add more members"""
        return self.get_member_count() < self.max_users


class OrganizationRole(models.Model):
    """
    Custom roles with flexible permissions.
    Each organization can create their own roles.
    """
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='roles')
    name = models.CharField(max_length=64, help_text="Role name (e.g., 'Accountant', 'Project Manager')")
    description = models.TextField(blank=True, help_text="Role description")

    # System roles (cannot be deleted/modified)
    is_owner = models.BooleanField(default=False, help_text="Organization owner role")
    is_system = models.BooleanField(default=False, help_text="System-created role")

    # Organization Management
    can_manage_organization = models.BooleanField(default=False, help_text="Change org settings, delete org")
    can_manage_members = models.BooleanField(default=False, help_text="Invite, remove members")
    can_manage_roles = models.BooleanField(default=False, help_text="Create, edit, delete roles")

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

    # Invoices & Clients
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
    can_approve_invoices = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['organization', 'name']
        ordering = ['organization', 'name']
        indexes = [
            models.Index(fields=['organization', 'name']),
        ]

    def __str__(self):
        return f"{self.organization.name} - {self.name}"


class OrganizationMember(models.Model):
    """
    Links Users to Organizations with roles.
    Junction table for many-to-many with additional fields.
    """
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organization_memberships')
    role = models.ForeignKey(OrganizationRole, on_delete=models.PROTECT, related_name='members')

    # Invitation tracking
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_invitations'
    )
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    # Status
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['organization', 'user']
        ordering = ['organization', 'user']
        indexes = [
            models.Index(fields=['organization', 'user']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['organization', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} @ {self.organization.name} ({self.role.name})"

    def has_permission(self, permission_name):
        """Check if member has a specific permission"""
        return getattr(self.role, permission_name, False)


class PermissionRequest(models.Model):
    """
    Temporary permission requests.
    Members can request elevated permissions for a limited time.
    """
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_EXPIRED = 'expired'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_EXPIRED, 'Expired'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='permission_requests')
    member = models.ForeignKey(OrganizationMember, on_delete=models.CASCADE, related_name='permission_requests')

    # Requested permissions (JSON object with permission names as keys)
    # Example: {"can_delete_transactions": true, "can_approve_budgets": true}
    permissions = models.JSONField(help_text="Requested permissions as JSON object")

    # Duration
    start_date = models.DateField(help_text="When permissions should become active")
    end_date = models.DateField(help_text="When permissions should expire")
    reason = models.TextField(help_text="Why these permissions are needed")

    # Approval
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_permission_requests'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status', '-created_at']),
            models.Index(fields=['member', 'status']),
            models.Index(fields=['status', 'end_date']),  # For expiry checks
        ]

    def __str__(self):
        return f"Permission Request by {self.member.user.username} - {self.status}"

    def is_active(self):
        """Check if request is currently active"""
        if self.status != self.STATUS_APPROVED:
            return False
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date

    def approve(self, approver):
        """Approve the permission request"""
        self.status = self.STATUS_APPROVED
        self.approved_by = approver
        self.approved_at = timezone.now()
        self.save()

    def reject(self, rejector, reason):
        """Reject the permission request"""
        self.status = self.STATUS_REJECTED
        self.approved_by = rejector
        self.approved_at = timezone.now()
        self.rejection_reason = reason
        self.save()


class ApprovalWorkflow(models.Model):
    """
    Define approval rules for transactions, budgets, etc.
    """
    ENTITY_TRANSACTION = 'transaction'
    ENTITY_BUDGET = 'budget'
    ENTITY_EXPENSE_CLAIM = 'expense_claim'
    ENTITY_INVOICE = 'invoice'

    ENTITY_TYPES = [
        (ENTITY_TRANSACTION, 'Transaction'),
        (ENTITY_BUDGET, 'Budget'),
        (ENTITY_EXPENSE_CLAIM, 'Expense Claim'),
        (ENTITY_INVOICE, 'Invoice'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='approval_workflows')
    name = models.CharField(max_length=128, help_text="Workflow name (e.g., 'Large Expenses')")
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPES)

    # Conditions (when this workflow is triggered)
    min_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum amount to trigger approval"
    )
    max_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum amount (optional)"
    )
    labels = models.ManyToManyField('Label', blank=True, help_text="Trigger only for specific labels/categories")

    # Approvers
    approver_roles = models.ManyToManyField(OrganizationRole, related_name='approval_workflows')
    approvals_required = models.IntegerField(default=1, help_text="Number of approvals needed")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['organization', 'name']
        indexes = [
            models.Index(fields=['organization', 'is_active']),
        ]

    def __str__(self):
        return f"{self.organization.name} - {self.name}"


class Approval(models.Model):
    """
    Individual approval requests and their status.
    """
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    workflow = models.ForeignKey(ApprovalWorkflow, on_delete=models.CASCADE, related_name='approvals')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='approvals')

    # What's being approved
    entity_type = models.CharField(max_length=20)
    entity_id = models.IntegerField(help_text="ID of the object being approved")
    entity_description = models.CharField(
        max_length=512,
        help_text="Human-readable description (e.g., 'Transaction: Office Supplies - £500')"
    )

    # Requester
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='approval_requests')

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    # Approvers
    approved_by = models.ManyToManyField(User, blank=True, related_name='approvals_given')
    rejected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approvals_rejected'
    )
    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status', '-created_at']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['requested_by', 'status']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"Approval: {self.entity_description} - {self.status}"

    def approve(self, approver):
        """Add an approval from a user"""
        self.approved_by.add(approver)

        # Check if we have enough approvals
        if self.approved_by.count() >= self.workflow.approvals_required:
            self.status = self.STATUS_APPROVED
            self.resolved_at = timezone.now()
            self.save()

    def reject(self, rejector, reason):
        """Reject the approval"""
        self.status = self.STATUS_REJECTED
        self.rejected_by = rejector
        self.rejection_reason = reason
        self.resolved_at = timezone.now()
        self.save()

    def cancel(self):
        """Cancel the approval request"""
        self.status = self.STATUS_CANCELLED
        self.resolved_at = timezone.now()
        self.save()


class ActivityLog(models.Model):
    """
    Audit trail of all actions within an organization.
    Security and compliance feature.
    """
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_VIEW = 'view'
    ACTION_EXPORT = 'export'
    ACTION_INVITE = 'invite'
    ACTION_APPROVE = 'approve'
    ACTION_REJECT = 'reject'
    ACTION_LOGIN = 'login'
    ACTION_LOGOUT = 'logout'

    ACTION_TYPES = [
        (ACTION_CREATE, 'Created'),
        (ACTION_UPDATE, 'Updated'),
        (ACTION_DELETE, 'Deleted'),
        (ACTION_VIEW, 'Viewed'),
        (ACTION_EXPORT, 'Exported'),
        (ACTION_INVITE, 'Invited'),
        (ACTION_APPROVE, 'Approved'),
        (ACTION_REJECT, 'Rejected'),
        (ACTION_LOGIN, 'Logged In'),
        (ACTION_LOGOUT, 'Logged Out'),
    ]

    ENTITY_TRANSACTION = 'transaction'
    ENTITY_BUDGET = 'budget'
    ENTITY_PROJECT = 'project'
    ENTITY_INVOICE = 'invoice'
    ENTITY_MEMBER = 'member'
    ENTITY_ROLE = 'role'
    ENTITY_LABEL = 'label'
    ENTITY_APPROVAL = 'approval'

    ENTITY_TYPES = [
        (ENTITY_TRANSACTION, 'Transaction'),
        (ENTITY_BUDGET, 'Budget'),
        (ENTITY_PROJECT, 'Project'),
        (ENTITY_INVOICE, 'Invoice'),
        (ENTITY_MEMBER, 'Team Member'),
        (ENTITY_ROLE, 'Role'),
        (ENTITY_LABEL, 'Label'),
        (ENTITY_APPROVAL, 'Approval'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='activity_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='activities')

    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPES, blank=True)
    entity_id = models.IntegerField(null=True, blank=True)

    description = models.CharField(max_length=512, help_text="Human-readable description")
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional data (old/new values, etc.)")

    # Security info
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', '-created_at']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]

    def __str__(self):
        username = self.user.username if self.user else 'System'
        return f"{username} - {self.get_action_display()}: {self.description}"

