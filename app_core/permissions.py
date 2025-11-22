# app_core/permissions.py
"""
Permission checking utilities and decorators for team collaboration.
"""

from functools import wraps
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from app_core.models import ActivityLog


def has_permission(user, organization, permission_name):
    """
    Check if a user has a specific permission in an organization.

    Args:
        user: User object
        organization: Organization object
        permission_name: String (e.g., 'can_view_transactions')

    Returns:
        Boolean
    """
    if not user.is_authenticated or not organization:
        return False

    try:
        from app_core.models import OrganizationMember, PermissionRequest
        from django.utils import timezone

        # Get user's membership
        member = OrganizationMember.objects.select_related('role').get(
            user=user,
            organization=organization,
            is_active=True
        )

        # Check base role permission
        has_perm = getattr(member.role, permission_name, False)

        if has_perm:
            return True

        # Check for active temporary permission request
        today = timezone.now().date()
        temp_perm = PermissionRequest.objects.filter(
            member=member,
            status=PermissionRequest.STATUS_APPROVED,
            start_date__lte=today,
            end_date__gte=today
        ).first()

        if temp_perm and temp_perm.permissions.get(permission_name, False):
            return True

        return False

    except:
        return False


def require_permission(permission_name, redirect_url='/'):
    """
    Decorator to require a specific permission.

    Usage:
        @require_permission('can_delete_transactions')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            if not hasattr(request, 'organization') or not request.organization:
                messages.error(request, 'No organization selected.')
                return redirect(redirect_url)

            if not has_permission(request.user, request.organization, permission_name):
                messages.error(request, 'You do not have permission to perform this action.')
                return redirect(redirect_url)

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_permission_ajax(permission_name):
    """
    Decorator for AJAX views that require a specific permission.
    Returns JSON error instead of redirect.

    Usage:
        @require_permission_ajax('can_create_invoices')
        def create_invoice_ajax(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'ok': False, 'error': 'Authentication required'}, status=401)

            if not hasattr(request, 'organization') or not request.organization:
                return JsonResponse({'ok': False, 'error': 'No organization selected'}, status=403)

            if not has_permission(request.user, request.organization, permission_name):
                return JsonResponse({'ok': False, 'error': 'Permission denied'}, status=403)

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def log_activity(organization, user, action, entity_type=None, entity_id=None, description='', metadata=None, request=None):
    """
    Log an activity to the audit trail.

    Args:
        organization: Organization object
        user: User object
        action: String (e.g., 'create', 'update', 'delete')
        entity_type: String (e.g., 'transaction', 'budget')
        entity_id: Integer (ID of the affected object)
        description: String (human-readable description)
        metadata: Dict (additional data to store)
        request: HttpRequest object (optional, for IP/user agent)
    """
    if not organization or not user:
        return None

    ip_address = None
    user_agent = ''

    if request:
        # Get IP and user agent from request metadata
        if hasattr(request, '_activity_metadata'):
            ip_address = request._activity_metadata.get('ip_address')
            user_agent = request._activity_metadata.get('user_agent', '')

    activity = ActivityLog.objects.create(
        organization=organization,
        user=user,
        action=action,
        entity_type=entity_type or '',
        entity_id=entity_id,
        description=description,
        metadata=metadata or {},
        ip_address=ip_address,
        user_agent=user_agent
    )

    return activity


def get_user_permissions(user, organization):
    """
    Get all permissions for a user in an organization.

    Returns:
        Dict of permission_name: boolean
    """
    if not user.is_authenticated or not organization:
        return {}

    try:
        from app_core.models import OrganizationMember

        member = OrganizationMember.objects.select_related('role').get(
            user=user,
            organization=organization,
            is_active=True
        )

        # Get all permission fields from the role
        permissions = {}
        for field in member.role._meta.fields:
            if field.name.startswith('can_'):
                permissions[field.name] = getattr(member.role, field.name, False)

        return permissions

    except:
        return {}

