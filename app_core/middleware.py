# app_core/middleware.py
"""
Team Collaboration Middleware
- Organization context provider
- Permission checking
- Activity logging
"""

from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from app_core.models import Organization, OrganizationMember


def organization_required(view_func):
    """
    Decorator that ensures user has an organization context.
    Redirects to organization creation if user has no organization.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        if not hasattr(request, 'organization') or request.organization is None:
            messages.warning(request, 'You need to be part of an organization to access this page.')
            return redirect('home')

        return view_func(request, *args, **kwargs)

    return wrapper


class OrganizationMiddleware(MiddlewareMixin):
    """
    Provides organization context to all requests.
    Sets request.organization based on session or user's primary organization.
    """

    def process_request(self, request):
        """Add organization context to request"""

        # Skip for anonymous users
        if not request.user.is_authenticated:
            request.organization = None
            request.organization_member = None
            return None

        # Get organization from session (if user switched)
        org_id = request.session.get('current_organization_id')

        if org_id:
            # Try to get the organization from session
            try:
                org = Organization.objects.get(id=org_id, members__user=request.user, is_active=True)
                member = OrganizationMember.objects.get(organization=org, user=request.user, is_active=True)
                request.organization = org
                request.organization_member = member
                return None
            except (Organization.DoesNotExist, OrganizationMember.DoesNotExist):
                # Session org is invalid, clear it
                del request.session['current_organization_id']

        # No session org, get user's primary organization (first one they're a member of)
        try:
            member = OrganizationMember.objects.filter(
                user=request.user,
                is_active=True,
                organization__is_active=True
            ).select_related('organization').first()

            if member:
                request.organization = member.organization
                request.organization_member = member
                # Save to session for next request
                request.session['current_organization_id'] = member.organization.id
            else:
                # User has no organizations (shouldn't happen with migration, but handle it)
                request.organization = None
                request.organization_member = None
        except Exception as e:
            # Log error in production
            request.organization = None
            request.organization_member = None

        return None


class ActivityLoggingMiddleware(MiddlewareMixin):
    """
    Logs user activity for audit trail.
    Can be enabled/disabled based on organization settings.
    """

    def process_request(self, request):
        """Prepare for activity logging"""
        # Store request metadata for later logging
        request._activity_metadata = {
            'ip_address': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:512],
        }
        return None

    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


