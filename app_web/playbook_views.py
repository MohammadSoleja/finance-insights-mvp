"""
Playbook Views
AI Financial Goal Management and Insights
"""

import json
from decimal import Decimal
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone

from app_core.models import FinancialGoal, GoalEvaluation, PlaybookConversation
from app_core.middleware import organization_required
from app_core import ai_service
from app_core.playbook_engine import evaluate_goal
from app_core.playbook_simulations import run_simulation, parse_simulation_request


@login_required
@organization_required
def playbook_overview(request):
    """
    Main Playbook page showing all goals, AI insights, and recommendations.
    """
    organization = request.organization

    # Get all active goals for this organization
    goals = FinancialGoal.objects.filter(
        organization=organization,
        active=True
    ).select_related('created_by').order_by('-created_at')

    # Get AI insights for dashboard
    insights = ai_service.get_playbook_insights(organization, context='playbook')

    # Stats
    total_goals = goals.count()
    achieved_goals = goals.filter(current_status='achieved').count()
    at_risk_goals = goals.filter(current_status__in=['at_risk', 'off_track']).count()

    context = {
        'page_title': 'Playbook',
        'goals': goals,
        'insights': insights,
        'total_goals': total_goals,
        'achieved_goals': achieved_goals,
        'at_risk_goals': at_risk_goals,
        'goal_types': FinancialGoal.GOAL_TYPES,
    }

    return render(request, 'app_web/playbook/overview.html', context)


@login_required
@organization_required
def create_goal(request):
    """
    Natural language goal creation flow.
    POST: User submits text -> LLM parses -> Returns confirmation form
    """
    if request.method == 'POST':
        user_input = request.POST.get('goal_text', '').strip()

        if not user_input:
            messages.error(request, 'Please enter a goal description.')
            return redirect('app_web:playbook_create_goal')

        # Parse natural language input
        parsed_goal = ai_service.parse_natural_language_goal(
            user_input,
            request.organization
        )

        # Store parsed goal in session for confirmation
        request.session['pending_goal'] = {
            'natural_language_input': user_input,
            'parsed_data': parsed_goal,
        }

        return redirect('app_web:playbook_confirm_goal')

    return render(request, 'app_web/playbook/create_goal.html', {
        'page_title': 'Create Goal',
    })


@login_required
@organization_required
def confirm_goal(request):
    """
    User confirms/edits LLM-parsed goal before saving.
    """
    pending_goal = request.session.get('pending_goal')

    if not pending_goal:
        messages.warning(request, 'No pending goal found. Please create a new goal.')
        return redirect('app_web:playbook_create_goal')

    if request.method == 'POST':
        # User confirmed/edited the goal - save it
        try:
            goal = FinancialGoal.objects.create(
                organization=request.organization,
                created_by=request.user,
                natural_language_input=pending_goal['natural_language_input'],
                goal_type=request.POST.get('goal_type'),
                name=request.POST.get('name'),
                description=request.POST.get('description', ''),
                target_value=Decimal(request.POST.get('target_value', '0')),
                start_date=request.POST.get('start_date') or None,
                target_date=request.POST.get('target_date') or None,
                parameters=json.loads(request.POST.get('parameters', '{}')),
                active=True,
            )

            # Clear session
            del request.session['pending_goal']

            messages.success(request, f'Goal "{goal.name}" created successfully!')

            # Trigger initial evaluation
            try:
                evaluation_data = evaluate_goal(goal)
                goal.current_status = evaluation_data['status']
                goal.current_value = evaluation_data.get('current_value')
                goal.progress_percentage = evaluation_data.get('progress_percentage', Decimal('0'))
                goal.last_evaluated_at = timezone.now()
                goal.save()
            except Exception as e:
                # Don't fail if evaluation fails
                messages.warning(request, 'Goal created but initial evaluation failed. It will be evaluated on the next scheduled run.')

            return redirect('app_web:playbook_goal_detail', goal_id=goal.id)

        except Exception as e:
            messages.error(request, f'Error creating goal: {str(e)}')
            return redirect('app_web:playbook_confirm_goal')

    parsed_data = pending_goal['parsed_data']

    context = {
        'page_title': 'Confirm Goal',
        'natural_input': pending_goal['natural_language_input'],
        'parsed_goal': parsed_data,
        'goal_types': FinancialGoal.GOAL_TYPES,
    }

    return render(request, 'app_web/playbook/confirm_goal.html', context)


@login_required
@organization_required
def goal_detail(request, goal_id):
    """
    Detailed goal view with progress chart, AI analysis, and what-if simulator.
    """
    goal = get_object_or_404(
        FinancialGoal,
        id=goal_id,
        organization=request.organization
    )

    # Get evaluation history for chart - filter by start_date if set
    evaluations_query = GoalEvaluation.objects.filter(goal=goal)
    
    # Only show evaluations from start_date onwards if start_date is set
    if goal.start_date:
        evaluations_query = evaluations_query.filter(
            evaluated_at__date__gte=goal.start_date
        )
    
    evaluations = evaluations_query.order_by('-evaluated_at')[:30]  # Last 30 evaluations

    # Reverse for chronological order in chart
    evaluations_list = list(reversed(evaluations))

    # Get latest evaluation for detailed view
    latest_evaluation = evaluations.first() if evaluations else None

    # Prepare chart data
    chart_data = {
        'labels': [e.evaluated_at.strftime('%Y-%m-%d') for e in evaluations_list],
        'progress': [float(e.progress_percentage) for e in evaluations_list],
        'values': [float(e.current_value) if e.current_value else 0 for e in evaluations_list],
    }

    context = {
        'page_title': goal.name,
        'goal': goal,
        'latest_evaluation': latest_evaluation,
        'evaluations': evaluations,
        'chart_data': json.dumps(chart_data),
    }

    return render(request, 'app_web/playbook/goal_detail.html', context)


@login_required
@organization_required
@require_http_methods(["POST"])
def refresh_goal_evaluation(request, goal_id):
    """
    Manually trigger real-time goal evaluation.
    """
    goal = get_object_or_404(
        FinancialGoal,
        id=goal_id,
        organization=request.organization
    )

    try:
        # Run evaluation
        evaluation_data = evaluate_goal(goal)

        # Get historical evaluations for AI context
        historical_evaluations = list(
            GoalEvaluation.objects.filter(goal=goal)
            .order_by('-evaluated_at')[:10]
        )

        # Generate AI insights
        explanation = ai_service.generate_goal_explanation(
            goal, evaluation_data, historical_evaluations
        )

        recommendations = ai_service.generate_recommendations(
            goal, evaluation_data
        )

        trend_analysis = ''
        if len(historical_evaluations) >= 2:
            trend_analysis = ai_service.generate_trend_analysis(
                goal, historical_evaluations
            )

        risk_factors = ai_service.identify_risk_factors(
            goal, evaluation_data
        )

        forecast = {}
        if len(historical_evaluations) >= 3:
            forecast = ai_service.generate_forecast(
                goal, evaluation_data, historical_evaluations
            )

        # Check if we already have an evaluation for today to prevent duplicates
        today = timezone.now().date()
        existing_today = GoalEvaluation.objects.filter(
            goal=goal,
            evaluated_at__date=today
        ).first()

        # Update or create evaluation snapshot
        if existing_today:
            # Update existing evaluation for today
            existing_today.status = evaluation_data['status']
            existing_today.current_value = evaluation_data.get('current_value')
            existing_today.progress_percentage = evaluation_data.get('progress_percentage', Decimal('0'))
            existing_today.metrics = evaluation_data.get('metrics', {})
            existing_today.explanation = explanation
            existing_today.recommendations = recommendations
            existing_today.risk_factors = risk_factors
            existing_today.trend_analysis = trend_analysis
            existing_today.forecast = forecast
            existing_today.evaluated_at = timezone.now()  # Update timestamp
            existing_today.save()
            evaluation = existing_today
        else:
            # Create new evaluation snapshot
            evaluation = GoalEvaluation.objects.create(
                goal=goal,
                status=evaluation_data['status'],
                current_value=evaluation_data.get('current_value'),
                progress_percentage=evaluation_data.get('progress_percentage', Decimal('0')),
                metrics=evaluation_data.get('metrics', {}),
                explanation=explanation,
                recommendations=recommendations,
                risk_factors=risk_factors,
                trend_analysis=trend_analysis,
                forecast=forecast,
            )

        # Update goal
        goal.current_status = evaluation_data['status']
        goal.current_value = evaluation_data.get('current_value')
        goal.progress_percentage = evaluation_data.get('progress_percentage', Decimal('0'))
        goal.last_evaluated_at = timezone.now()
        goal.last_explanation = explanation
        goal.last_recommendations = recommendations
        goal.save()

        return JsonResponse({
            'success': True,
            'message': 'Goal evaluation updated successfully',
            'status': evaluation_data['status'],
            'progress': float(evaluation_data['progress_percentage']),
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@organization_required
def edit_goal(request, goal_id):
    """
    Edit an existing goal - all fields including start_date, target_date, name, etc.
    """
    goal = get_object_or_404(
        FinancialGoal,
        id=goal_id,
        organization=request.organization
    )

    if request.method == 'POST':
        try:
            # Update goal fields
            goal.name = request.POST.get('name', goal.name)
            goal.description = request.POST.get('description', goal.description)
            goal.goal_type = request.POST.get('goal_type', goal.goal_type)

            # Update dates
            start_date = request.POST.get('start_date')
            if start_date:
                goal.start_date = start_date

            target_date = request.POST.get('target_date')
            if target_date:
                goal.target_date = target_date

            # Update target value
            target_value = request.POST.get('target_value')
            if target_value:
                goal.target_value = Decimal(target_value)

            # Update parameters if provided
            parameters = request.POST.get('parameters')
            if parameters:
                try:
                    goal.parameters = json.loads(parameters)
                except:
                    pass  # Keep existing if invalid JSON

            goal.save()

            # Re-evaluate the goal with new parameters
            try:
                evaluation_data = evaluate_goal(goal)
                goal.current_status = evaluation_data['status']
                goal.current_value = evaluation_data.get('current_value')
                goal.progress_percentage = evaluation_data.get('progress_percentage', Decimal('0'))
                goal.last_evaluated_at = timezone.now()
                goal.save()
            except Exception as e:
                messages.warning(request, f'Goal updated but evaluation failed: {str(e)}')

            messages.success(request, f'Goal "{goal.name}" updated successfully!')
            return redirect('app_web:playbook_goal_detail', goal_id=goal.id)

        except Exception as e:
            messages.error(request, f'Error updating goal: {str(e)}')

    context = {
        'page_title': f'Edit {goal.name}',
        'goal': goal,
        'goal_types': FinancialGoal.GOAL_TYPES,
        'parameters_json': json.dumps(goal.parameters) if goal.parameters else '{}',
    }

    return render(request, 'app_web/playbook/edit_goal.html', context)


@login_required
@organization_required
def goal_conversation(request, goal_id):
    """
    Conversational what-if interface.
    """
    goal = get_object_or_404(
        FinancialGoal,
        id=goal_id,
        organization=request.organization
    )

    if request.method == 'POST':
        user_message = request.POST.get('message', '').strip()

        if not user_message:
            return JsonResponse({'error': 'Message is required'}, status=400)

        # Get or create conversation
        conversation = PlaybookConversation.objects.filter(
            organization=request.organization,
            user=request.user,
            goal=goal
        ).order_by('-updated_at').first()

        if not conversation:
            conversation = PlaybookConversation.objects.create(
                organization=request.organization,
                user=request.user,
                goal=goal,
                title=f"What-if: {goal.name[:50]}",
                conversation_type='what_if'
            )

        # Check if this is a what-if simulation request
        if any(keyword in user_message.lower() for keyword in ['what if', 'simulate', 'scenario']):
            # Parse simulation request
            hypothetical_changes = parse_simulation_request(user_message, goal)

            if hypothetical_changes:
                # Run simulation
                try:
                    result = run_simulation(goal, hypothetical_changes)
                    assistant_message = result['narrative']

                    # Add simulation results to message with proper formatting
                    original_pct = round(float(result['original_outcome']['progress_percentage']), 1)
                    simulated_pct = round(float(result['simulated_outcome']['progress_percentage']), 1)

                    assistant_message += f"\n\n**Simulation Results:**\n"
                    assistant_message += f"- Original: {result['original_outcome']['status'].replace('_', ' ').title()} ({original_pct}%)\n"
                    assistant_message += f"- Simulated: {result['simulated_outcome']['status'].replace('_', ' ').title()} ({simulated_pct}%)\n"
                    assistant_message += f"- Goal Achievable: {'✅ Yes' if result['achieves_goal'] else '❌ Not yet'}"

                except Exception as e:
                    assistant_message = f"I encountered an error running the simulation: {str(e)}"
            else:
                assistant_message = "I couldn't parse the simulation parameters. Could you rephrase your question?"
        else:
            # General conversation
            assistant_message = ai_service.chat_conversation(conversation, user_message)

        # Save the messages to conversation history
        conversation.add_message('user', user_message)
        conversation.add_message('assistant', assistant_message)
        conversation.save()

        return JsonResponse({
            'success': True,
            'user_message': user_message,
            'assistant_message': assistant_message,
            'timestamp': timezone.now().isoformat()
        })

    # GET request - check if it's an AJAX request for conversation history
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        # Return conversation history as JSON
        conversation = PlaybookConversation.objects.filter(
            organization=request.organization,
            user=request.user,
            goal=goal
        ).order_by('-updated_at').first()

        messages = []
        if conversation and conversation.messages:
            messages = conversation.messages

        return JsonResponse({
            'success': True,
            'messages': messages
        })

    # Regular GET request - show conversation history
    conversations = PlaybookConversation.objects.filter(
        organization=request.organization,
        user=request.user,
        goal=goal
    ).order_by('-updated_at')[:5]

    context = {
        'goal': goal,
        'conversations': conversations,
    }

    return render(request, 'app_web/playbook/conversation.html', context)


@login_required
@organization_required
def clear_goal_conversation(request, goal_id):
    """
    Clear/reset the conversation for a goal.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    goal = get_object_or_404(
        FinancialGoal,
        id=goal_id,
        organization=request.organization
    )

    # Delete all conversations for this goal
    deleted_count = PlaybookConversation.objects.filter(
        organization=request.organization,
        user=request.user,
        goal=goal
    ).delete()

    return JsonResponse({
        'success': True,
        'message': 'Conversation cleared successfully'
    })


@login_required
@organization_required
@require_http_methods(["POST"])
def delete_goal(request, goal_id):
    """
    Soft delete a goal (set active=False).
    """
    goal = get_object_or_404(
        FinancialGoal,
        id=goal_id,
        organization=request.organization
    )

    goal.active = False
    goal.save()

    messages.success(request, f'Goal "{goal.name}" has been archived.')
    return redirect('app_web:playbook_overview')


@login_required
@organization_required
@require_http_methods(["GET"])
def playbook_api_insights(request):
    """
    API endpoint for fetching AI insights for dashboard widget.
    """
    organization = request.organization
    insights = ai_service.get_playbook_insights(organization, context='dashboard')

    return JsonResponse({
        'success': True,
        'insights': insights[:3]  # Top 3 for dashboard widget
    })


@login_required
@organization_required
def goal_templates(request):
    """
    Browse goal templates library
    """
    from app_core.goal_templates import GOAL_TEMPLATES

    context = {
        'page_title': 'Goal Templates',
        'templates': GOAL_TEMPLATES,
    }

    return render(request, 'app_web/playbook/templates.html', context)


@login_required
@organization_required
def create_from_template(request, template_id):
    """
    Create a goal from a template
    """
    from app_core.goal_templates import get_template, calculate_dynamic_target
    from datetime import timedelta

    template = get_template(template_id)

    if not template:
        messages.error(request, 'Template not found.')
        return redirect('app_web:goal_templates')

    # Calculate dynamic target if needed
    target_value = template.get('target_value')
    if target_value is None:
        target_value = calculate_dynamic_target(request.organization, template)

    # Calculate target date
    duration_months = template.get('duration_months', 6)
    target_date = timezone.now().date() + timedelta(days=duration_months * 30)

    # Create goal
    goal = FinancialGoal.objects.create(
        organization=request.organization,
        name=template['name'],
        description=template['description'],
        goal_type=template['goal_type'],
        target_value=target_value,
        target_date=target_date,
        start_date=timezone.now().date(),
        natural_language_input=f"Created from template: {template['name']}",
        created_by=request.user,
    )

    # Evaluate immediately
    try:
        evaluation_data = evaluate_goal(goal)
        goal.current_status = evaluation_data['status']
        goal.current_value = evaluation_data.get('current_value')
        goal.progress_percentage = evaluation_data.get('progress_percentage', Decimal('0'))
        goal.last_evaluated_at = timezone.now()
        goal.save()
    except Exception as e:
        messages.warning(request, f'Goal created but evaluation failed: {str(e)}')

    messages.success(request, f'Goal "{goal.name}" created from template!')
    return redirect('app_web:playbook_goal_detail', goal_id=goal.id)


@login_required
@organization_required
def health_score_dashboard(request):
    """
    Health Score dashboard with trends and breakdown
    """
    from app_core.health_score import calculate_health_score, get_score_trend

    organization = request.organization

    # Get current health score
    current_score = calculate_health_score(organization)

    # Get trend data (last 30 days)
    trend_data = get_score_trend(organization, days=30)

    context = {
        'page_title': 'Financial Health Score',
        'health_score': current_score,
        'trend_data': trend_data,
    }

    return render(request, 'app_web/health/dashboard.html', context)


@login_required
@organization_required
def runway_intelligence(request):
    """
    Enhanced runway intelligence dashboard
    """
    from app_core.playbook_engine import calculate_runway_enhanced

    organization = request.organization

    # Get enhanced runway data
    runway_data = calculate_runway_enhanced(organization)

    context = {
        'page_title': 'Runway Intelligence',
        'runway_data': runway_data,
    }

    return render(request, 'app_web/runway/dashboard.html', context)


@login_required
@organization_required
def api_health_score(request):
    """
    API endpoint for health score widget
    """
    from app_core.health_score import calculate_health_score

    health_data = calculate_health_score(request.organization)

    return JsonResponse({
        'success': True,
        'data': health_data
    })


@login_required
@organization_required
def api_runway_enhanced(request):
    """
    API endpoint for enhanced runway data
    """
    from app_core.playbook_engine import calculate_runway_enhanced

    runway_data = calculate_runway_enhanced(request.organization)

    return JsonResponse({
        'success': True,
        'data': runway_data
    })


@login_required
@organization_required
def api_weekly_briefing(request):
    """
    API endpoint to get weekly briefing data
    """
    from app_core.weekly_briefing import generate_weekly_briefing

    briefing_data = generate_weekly_briefing(request.organization)

    return JsonResponse({
        'success': True,
        'briefing': briefing_data
    })


