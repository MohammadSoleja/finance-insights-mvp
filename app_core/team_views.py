# app_core/team_views.py
"""
Team Collaboration Views
- Organization switching
- Team management
- Member management
- Role management
- Approval workflows
- Activity log
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.paginator import Paginator

from app_core.models import (
    Organization, OrganizationRole, OrganizationMember,
    PermissionRequest, ApprovalWorkflow, Approval, ActivityLog
)
from app_core.permissions import require_permission, require_permission_ajax, log_activity

User = get_user_model()


# ==================== ORGANIZATION SWITCHING ====================

@login_required
def switch_organization(request, org_id):
    """Switch the user's active organization"""
    try:
        # Verify user is a member of this organization
        member = OrganizationMember.objects.get(
            organization_id=org_id,
            user=request.user,
            is_active=True,
            organization__is_active=True
        )

        # Update session
        request.session['current_organization_id'] = org_id

        messages.success(request, f'Switched to {member.organization.name}')

    except OrganizationMember.DoesNotExist:
        messages.error(request, 'You are not a member of that organization.')

    # Redirect to referrer or dashboard
    return redirect(request.META.get('HTTP_REFERER', '/dashboard/'))


# ==================== TEAM OVERVIEW ====================

@login_required
def team_overview(request):
    """Team dashboard/overview page"""
    if not request.organization:
        messages.error(request, 'No organization selected.')
        return redirect('/dashboard/')

    org = request.organization

    # Get team statistics
    members_count = OrganizationMember.objects.filter(
        organization=org,
        is_active=True
    ).count()

    roles_count = OrganizationRole.objects.filter(organization=org).count()

    pending_approvals_count = Approval.objects.filter(
        organization=org,
        status=Approval.STATUS_PENDING
    ).count()

    pending_permission_requests_count = PermissionRequest.objects.filter(
        organization=org,
        status=PermissionRequest.STATUS_PENDING
    ).count()

    # Recent activity
    recent_activity = ActivityLog.objects.filter(
        organization=org
    ).select_related('user').order_by('-created_at')[:20]

    # Active members
    active_members = OrganizationMember.objects.filter(
        organization=org,
        is_active=True
    ).select_related('user', 'role').order_by('-accepted_at')[:10]

    context = {
        'title': 'Team Overview',
        'members_count': members_count,
        'roles_count': roles_count,
        'pending_approvals_count': pending_approvals_count,
        'pending_permission_requests_count': pending_permission_requests_count,
        'recent_activity': recent_activity,
        'active_members': active_members,
    }

    return render(request, 'app_web/team/overview.html', context)


# ==================== TEAM MEMBERS ====================

@login_required
@require_permission('can_view_transactions')  # Basic permission to view team
def team_members(request):
    """List all team members"""
    if not request.organization:
        messages.error(request, 'No organization selected.')
        return redirect('/dashboard/')

    org = request.organization

    # Get all members
    members = OrganizationMember.objects.filter(
        organization=org
    ).select_related('user', 'role', 'invited_by').order_by('-is_active', 'user__username')

    # Get available roles for inviting
    roles = OrganizationRole.objects.filter(organization=org).order_by('name')

    context = {
        'title': 'Team Members',
        'members': members,
        'roles': roles,
        'can_manage_members': request.organization_member.role.can_manage_members,
    }

    return render(request, 'app_web/team/members.html', context)


@login_required
@require_permission_ajax('can_manage_members')
def invite_member(request):
    """Invite a new member to the organization (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=400)

    email = request.POST.get('email', '').strip()
    role_id = request.POST.get('role_id')

    if not email or not role_id:
        return JsonResponse({'ok': False, 'error': 'Email and role are required'}, status=400)

    org = request.organization

    try:
        # Get the role
        role = OrganizationRole.objects.get(id=role_id, organization=org)

        # Check if user exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({
                'ok': False,
                'error': 'User with this email does not exist. They need to sign up first.'
            }, status=400)

        # Check if already a member
        if OrganizationMember.objects.filter(organization=org, user=user).exists():
            return JsonResponse({
                'ok': False,
                'error': 'This user is already a member of the organization.'
            }, status=400)

        # Check max users limit
        if not org.can_add_member():
            return JsonResponse({
                'ok': False,
                'error': f'Organization has reached maximum members limit ({org.max_users}).'
            }, status=400)

        # Create membership
        member = OrganizationMember.objects.create(
            organization=org,
            user=user,
            role=role,
            invited_by=request.user,
            accepted_at=timezone.now(),  # Auto-accept for now (can add invitation flow later)
            is_active=True
        )

        # Log activity
        log_activity(
            org,
            request.user,
            'invite',
            'member',
            member.id,
            f'Invited {user.email} as {role.name}',
            request=request
        )

        return JsonResponse({
            'ok': True,
            'message': f'{user.email} has been added to the organization.',
            'member': {
                'id': member.id,
                'username': user.username,
                'email': user.email,
                'role': role.name,
            }
        })

    except OrganizationRole.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Invalid role'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_permission_ajax('can_manage_members')
def remove_member(request, member_id):
    """Remove a member from the organization (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=400)

    org = request.organization

    try:
        member = OrganizationMember.objects.get(id=member_id, organization=org)

        # Can't remove the organization owner
        if member.role.is_owner:
            return JsonResponse({
                'ok': False,
                'error': 'Cannot remove the organization owner.'
            }, status=400)

        # Can't remove yourself
        if member.user == request.user:
            return JsonResponse({
                'ok': False,
                'error': 'You cannot remove yourself. Ask another admin to remove you.'
            }, status=400)

        username = member.user.username

        # Deactivate instead of delete (for audit trail)
        member.is_active = False
        member.save()

        # Log activity
        log_activity(
            org,
            request.user,
            'delete',
            'member',
            member.id,
            f'Removed member {username}',
            request=request
        )

        return JsonResponse({
            'ok': True,
            'message': f'{username} has been removed from the organization.'
        })

    except OrganizationMember.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Member not found'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_permission_ajax('can_manage_members')
def change_member_role(request, member_id):
    """Change a member's role (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=400)

    role_id = request.POST.get('role_id')

    if not role_id:
        return JsonResponse({'ok': False, 'error': 'Role is required'}, status=400)

    org = request.organization

    try:
        member = OrganizationMember.objects.get(id=member_id, organization=org)
        role = OrganizationRole.objects.get(id=role_id, organization=org)

        # Can't change owner role
        if member.role.is_owner:
            return JsonResponse({
                'ok': False,
                'error': 'Cannot change the organization owner\'s role.'
            }, status=400)

        old_role = member.role.name
        member.role = role
        member.save()

        # Log activity
        log_activity(
            org,
            request.user,
            'update',
            'member',
            member.id,
            f'Changed {member.user.username} role from {old_role} to {role.name}',
            request=request
        )

        return JsonResponse({
            'ok': True,
            'message': f'{member.user.username} is now {role.name}.'
        })

    except (OrganizationMember.DoesNotExist, OrganizationRole.DoesNotExist):
        return JsonResponse({'ok': False, 'error': 'Member or role not found'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ==================== ACTIVITY LOG ====================

@login_required
def activity_log(request):
    """View organization activity log"""
    if not request.organization:
        messages.error(request, 'No organization selected.')
        return redirect('/dashboard/')

    org = request.organization

    # Get filters
    action_filter = request.GET.get('action', '')
    entity_filter = request.GET.get('entity', '')
    user_filter = request.GET.get('user', '')

    # Build query
    activities = ActivityLog.objects.filter(organization=org)

    if action_filter:
        activities = activities.filter(action=action_filter)

    if entity_filter:
        activities = activities.filter(entity_type=entity_filter)

    if user_filter:
        activities = activities.filter(user_id=user_filter)

    activities = activities.select_related('user').order_by('-created_at')

    # Paginate
    paginator = Paginator(activities, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Get filter options
    action_choices = ActivityLog.ACTION_TYPES
    entity_choices = ActivityLog.ENTITY_TYPES
    team_members = OrganizationMember.objects.filter(
        organization=org,
        is_active=True
    ).select_related('user').values('user__id', 'user__username')

    context = {
        'title': 'Activity Log',
        'page_obj': page_obj,
        'action_choices': action_choices,
        'entity_choices': entity_choices,
        'team_members': team_members,
        'current_action': action_filter,
        'current_entity': entity_filter,
        'current_user': user_filter,
    }

    return render(request, 'app_web/team/activity_log.html', context)


# ==================== APPROVALS ====================

@login_required
def approvals_view(request):
    """View and manage approval requests"""
    if not request.organization:
        messages.error(request, 'No organization selected.')
        return redirect('/dashboard/')

    org = request.organization
    user_member = request.organization_member

    # Get filter
    status_filter = request.GET.get('status', 'pending')

    # Get approvals where user can approve (based on their role)
    my_approvals = Approval.objects.filter(
        organization=org,
        workflow__approver_roles=user_member.role
    )

    # Get approvals requested by user
    my_requests = Approval.objects.filter(
        organization=org,
        requested_by=request.user
    )

    # Apply status filter
    if status_filter and status_filter != 'all':
        my_approvals = my_approvals.filter(status=status_filter)
        my_requests = my_requests.filter(status=status_filter)

    my_approvals = my_approvals.select_related(
        'workflow', 'requested_by', 'rejected_by'
    ).prefetch_related('approved_by').order_by('-created_at')

    my_requests = my_requests.select_related(
        'workflow', 'requested_by', 'rejected_by'
    ).prefetch_related('approved_by').order_by('-created_at')

    # Paginate
    approvals_paginator = Paginator(my_approvals, 20)
    approvals_page = request.GET.get('approvals_page', 1)
    approvals_page_obj = approvals_paginator.get_page(approvals_page)

    requests_paginator = Paginator(my_requests, 20)
    requests_page = request.GET.get('requests_page', 1)
    requests_page_obj = requests_paginator.get_page(requests_page)

    # Get counts
    pending_approvals_count = Approval.objects.filter(
        organization=org,
        workflow__approver_roles=user_member.role,
        status=Approval.STATUS_PENDING
    ).count()

    context = {
        'title': 'Approvals',
        'approvals_page_obj': approvals_page_obj,
        'requests_page_obj': requests_page_obj,
        'pending_approvals_count': pending_approvals_count,
        'status_filter': status_filter,
        'status_choices': Approval.STATUS_CHOICES,
    }

    return render(request, 'app_web/team/approvals.html', context)


@login_required
@require_http_methods(["POST"])
def approve_request(request, approval_id):
    """Approve an approval request (AJAX)"""
    if not request.organization:
        return JsonResponse({'ok': False, 'error': 'No organization selected'}, status=400)

    org = request.organization
    user_member = request.organization_member

    try:
        approval = Approval.objects.get(id=approval_id, organization=org)

        # Check if user's role can approve this
        if user_member.role not in approval.workflow.approver_roles.all():
            return JsonResponse({
                'ok': False,
                'error': 'You do not have permission to approve this request.'
            }, status=403)

        # Check if already approved/rejected
        if approval.status != Approval.STATUS_PENDING:
            return JsonResponse({
                'ok': False,
                'error': f'This request has already been {approval.status}.'
            }, status=400)

        # Check if user already approved
        if request.user in approval.approved_by.all():
            return JsonResponse({
                'ok': False,
                'error': 'You have already approved this request.'
            }, status=400)

        # Approve
        approval.approve(request.user)

        # Log activity
        log_activity(
            org,
            request.user,
            'approve',
            approval.entity_type,
            approval.entity_id,
            f'Approved: {approval.entity_description}',
            request=request
        )

        return JsonResponse({
            'ok': True,
            'message': 'Approval granted successfully.',
            'status': approval.status,
            'approved_count': approval.approved_by.count(),
            'required_count': approval.workflow.approvals_required
        })

    except Approval.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Approval request not found'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def reject_request(request, approval_id):
    """Reject an approval request (AJAX)"""
    if not request.organization:
        return JsonResponse({'ok': False, 'error': 'No organization selected'}, status=400)

    org = request.organization
    user_member = request.organization_member

    try:
        import json
        data = json.loads(request.body)
        reason = data.get('reason', 'No reason provided')

        approval = Approval.objects.get(id=approval_id, organization=org)

        # Check if user's role can approve this
        if user_member.role not in approval.workflow.approver_roles.all():
            return JsonResponse({
                'ok': False,
                'error': 'You do not have permission to reject this request.'
            }, status=403)

        # Check if already approved/rejected
        if approval.status != Approval.STATUS_PENDING:
            return JsonResponse({
                'ok': False,
                'error': f'This request has already been {approval.status}.'
            }, status=400)

        # Reject
        approval.reject(request.user, reason)

        # Log activity
        log_activity(
            org,
            request.user,
            'reject',
            approval.entity_type,
            approval.entity_id,
            f'Rejected: {approval.entity_description}',
            request=request
        )

        return JsonResponse({
            'ok': True,
            'message': 'Request rejected.',
            'status': approval.status
        })

    except Approval.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Approval request not found'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ==================== APPROVAL WORKFLOWS ====================

@login_required
@require_permission('can_manage_organization')
def approval_workflows_view(request):
    """Manage approval workflows"""
    if not request.organization:
        messages.error(request, 'No organization selected.')
        return redirect('/dashboard/')

    org = request.organization

    workflows = ApprovalWorkflow.objects.filter(organization=org).prefetch_related(
        'approver_roles', 'labels'
    ).order_by('name')

    # Get all roles and labels for the form
    roles = OrganizationRole.objects.filter(organization=org).order_by('name')
    labels = org.labels.filter(organization=org).order_by('name')

    context = {
        'title': 'Approval Workflows',
        'workflows': workflows,
        'roles': roles,
        'labels': labels,
        'entity_types': ApprovalWorkflow.ENTITY_TYPES,
    }

    return render(request, 'app_web/team/approval_workflows.html', context)


@login_required
@require_permission_ajax('can_manage_organization')
def create_workflow(request):
    """Create a new approval workflow (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=400)

    org = request.organization

    try:
        import json
        from decimal import Decimal

        data = json.loads(request.body)

        # Create workflow
        workflow = ApprovalWorkflow.objects.create(
            organization=org,
            name=data['name'],
            entity_type=data['entity_type'],
            min_amount=Decimal(data['min_amount']) if data.get('min_amount') else None,
            max_amount=Decimal(data['max_amount']) if data.get('max_amount') else None,
            approvals_required=int(data.get('approvals_required', 1)),
            is_active=data.get('is_active', True)
        )

        # Add approver roles
        if 'approver_role_ids' in data:
            role_ids = data['approver_role_ids']
            if role_ids:
                roles = OrganizationRole.objects.filter(
                    id__in=role_ids,
                    organization=org
                )
                workflow.approver_roles.set(roles)

        # Add labels
        if 'label_ids' in data:
            label_ids = data['label_ids']
            if label_ids:
                from app_core.models import Label
                labels = Label.objects.filter(
                    id__in=label_ids,
                    organization=org
                )
                workflow.labels.set(labels)

        # Log activity
        log_activity(
            org,
            request.user,
            'create',
            'approval_workflow',
            workflow.id,
            f'Created approval workflow: {workflow.name}',
            request=request
        )

        return JsonResponse({
            'ok': True,
            'message': f'Workflow "{workflow.name}" created successfully.',
            'workflow_id': workflow.id
        })

    except KeyError as e:
        return JsonResponse({'ok': False, 'error': f'Missing field: {e}'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_permission_ajax('can_manage_organization')
def delete_workflow(request, workflow_id):
    """Delete an approval workflow (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=400)

    org = request.organization

    try:
        workflow = ApprovalWorkflow.objects.get(id=workflow_id, organization=org)
        workflow_name = workflow.name

        # Check if there are pending approvals
        pending_count = Approval.objects.filter(
            workflow=workflow,
            status=Approval.STATUS_PENDING
        ).count()

        if pending_count > 0:
            return JsonResponse({
                'ok': False,
                'error': f'Cannot delete workflow with {pending_count} pending approvals.'
            }, status=400)

        workflow.delete()

        # Log activity
        log_activity(
            org,
            request.user,
            'delete',
            'approval_workflow',
            workflow_id,
            f'Deleted approval workflow: {workflow_name}',
            request=request
        )

        return JsonResponse({
            'ok': True,
            'message': f'Workflow "{workflow_name}" deleted successfully.'
        })

    except ApprovalWorkflow.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Workflow not found'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


