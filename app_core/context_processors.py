# app_core/context_processors.py
"""
Context processors to add organization data to all templates.
"""

from app_core.models import OrganizationMember


def organization_context(request):
    """
    Add organization context to all templates.
    This makes current_organization and user_organizations available in all templates.
    """
    context = {
        'current_organization': None,
        'organization_member': None,
        'user_organizations': [],
    }

    if request.user.is_authenticated:
        # Add current organization (set by middleware)
        if hasattr(request, 'organization'):
            context['current_organization'] = request.organization

        if hasattr(request, 'organization_member'):
            context['organization_member'] = request.organization_member

        # Add all user's organizations for switcher
        context['user_organizations'] = OrganizationMember.objects.filter(
            user=request.user,
            is_active=True,
            organization__is_active=True
        ).select_related('organization', 'role')

    return context

