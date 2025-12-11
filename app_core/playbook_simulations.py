# app_core/playbook_simulations.py
"""
AI Financial Playbook - What-If Simulation Service
Runs hypothetical scenarios by modifying financial data and re-evaluating goals.
"""

import json
import logging
from typing import Dict, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
from copy import deepcopy

from django.conf import settings

from .playbook_engine import evaluate_goal
from . import ai_service

logger = logging.getLogger(__name__)


def run_simulation(goal, hypothetical_changes: Dict, as_of_date: Optional[date] = None) -> Dict:
    """
    Run what-if simulation by modifying metrics and re-evaluating.

    Args:
        goal: FinancialGoal instance
        hypothetical_changes: Dict with changes to apply
        as_of_date: Date to simulate as of (defaults to today)

    hypothetical_changes examples:
    - {"monthly_revenue_increase": 5000}
    - {"monthly_expense_reduction": 2000}
    - {"expense_reduction_percentage": 10, "category": "Marketing"}
    - {"one_time_income": 50000, "date": "2026-01-15"}
    - {"cut_category_spend": {"category": "Office", "percentage": 25}}

    Returns:
        dict with:
            original_outcome: {...},
            simulated_outcome: {...},
            difference: {...},
            achieves_goal: bool,
            narrative: str (AI-generated explanation)
    """
    from django.utils import timezone
    if as_of_date is None:
        as_of_date = timezone.now().date()

    # Get original evaluation
    original_evaluation = evaluate_goal(goal, as_of_date)

    # Apply hypothetical changes and re-evaluate
    # For now, we'll simulate by adjusting the metrics
    # In a full implementation, this would create hypothetical transactions

    simulated_evaluation = _apply_hypothetical_changes(
        goal, original_evaluation, hypothetical_changes, as_of_date
    )

    # Calculate differences
    difference = _calculate_difference(original_evaluation, simulated_evaluation)

    # Determine if goal is achievable with changes
    achieves_goal = simulated_evaluation['status'] in ['on_track', 'achieved']

    # Generate narrative explanation
    narrative = _generate_simulation_narrative(
        goal, original_evaluation, simulated_evaluation, hypothetical_changes, achieves_goal
    )

    return {
        'original_outcome': original_evaluation,
        'simulated_outcome': simulated_evaluation,
        'difference': difference,
        'achieves_goal': achieves_goal,
        'narrative': narrative,
        'hypothetical_changes': hypothetical_changes,
    }


def _apply_hypothetical_changes(goal, original_eval: Dict, changes: Dict, as_of_date: date) -> Dict:
    """
    Apply hypothetical changes to evaluation data.
    This is a simplified simulation - real implementation would modify actual data.
    """
    # Create a copy of the evaluation
    simulated = deepcopy(original_eval)
    metrics = simulated.get('metrics', {})

    # Apply different types of changes
    if 'monthly_revenue_increase' in changes:
        increase = Decimal(str(changes['monthly_revenue_increase']))
        if 'inflow' in metrics:
            metrics['inflow'] = float(Decimal(str(metrics['inflow'])) + increase)
        if 'net' in metrics:
            metrics['net'] = float(Decimal(str(metrics['net'])) + increase)

    if 'monthly_expense_reduction' in changes:
        reduction = Decimal(str(changes['monthly_expense_reduction']))
        if 'outflow' in metrics:
            metrics['outflow'] = float(max(Decimal('0'), Decimal(str(metrics['outflow'])) - reduction))
        if 'net' in metrics:
            metrics['net'] = float(Decimal(str(metrics['net'])) + reduction)

    if 'expense_reduction_percentage' in changes:
        pct = Decimal(str(changes['expense_reduction_percentage'])) / Decimal('100')
        if 'outflow' in metrics:
            current_outflow = Decimal(str(metrics['outflow']))
            reduction = current_outflow * pct
            metrics['outflow'] = float(current_outflow - reduction)
        if 'net' in metrics:
            metrics['net'] = float(Decimal(str(metrics['net'])) + reduction)

    if 'one_time_income' in changes:
        income = Decimal(str(changes['one_time_income']))
        if 'inflow' in metrics:
            metrics['inflow'] = float(Decimal(str(metrics['inflow'])) + income)
        if 'net' in metrics:
            metrics['net'] = float(Decimal(str(metrics['net'])) + income)

    # Recalculate goal-specific values based on modified metrics
    simulated['metrics'] = metrics

    if goal.goal_type == 'runway':
        # Recalculate runway with modified burn rate
        if 'monthly_burn' in metrics and 'current_balance' in metrics:
            modified_burn = Decimal(str(metrics.get('monthly_burn', 0)))
            if 'monthly_expense_reduction' in changes:
                modified_burn = max(Decimal('0'), modified_burn - Decimal(str(changes['monthly_expense_reduction'])))

            current_balance = Decimal(str(metrics.get('current_balance', 0)))
            if 'one_time_income' in changes:
                current_balance += Decimal(str(changes['one_time_income']))

            if modified_burn > 0:
                new_runway = current_balance / modified_burn
            else:
                new_runway = Decimal('999')

            simulated['current_value'] = min(new_runway, Decimal('999'))
            metrics['runway_months'] = float(new_runway)
            metrics['monthly_burn'] = float(modified_burn)
            metrics['current_balance'] = float(current_balance)

    elif goal.goal_type == 'savings':
        # Recalculate savings
        net = Decimal(str(metrics.get('net', 0)))
        simulated['current_value'] = net

    elif goal.goal_type == 'revenue_target':
        # Use modified inflow
        simulated['current_value'] = Decimal(str(metrics.get('inflow', 0)))

    elif goal.goal_type == 'spending_limit':
        # Use modified outflow
        simulated['current_value'] = Decimal(str(metrics.get('outflow', 0)))

    # Recalculate progress percentage
    target = simulated.get('target_value', Decimal('1'))
    if target > 0:
        progress = (simulated['current_value'] / target) * Decimal('100')
        simulated['progress_percentage'] = min(progress, Decimal('100'))

    # Recalculate status
    progress_pct = simulated['progress_percentage']
    if progress_pct >= 100:
        simulated['status'] = 'achieved'
    elif progress_pct >= 75:
        simulated['status'] = 'on_track'
    elif progress_pct >= 50:
        simulated['status'] = 'at_risk'
    else:
        simulated['status'] = 'off_track'

    return simulated


def _calculate_difference(original: Dict, simulated: Dict) -> Dict:
    """Calculate the difference between original and simulated outcomes"""
    return {
        'value_change': float(simulated['current_value'] - original['current_value']),
        'progress_change': float(simulated['progress_percentage'] - original['progress_percentage']),
        'status_change': f"{original['status']} → {simulated['status']}",
        'improved': simulated['progress_percentage'] > original['progress_percentage'],
    }


def _generate_simulation_narrative(goal, original, simulated, changes, achieves_goal) -> str:
    """Generate narrative explanation of simulation results"""
    if not ai_service._check_ai_available():
        return _fallback_simulation_narrative(goal, original, simulated, changes, achieves_goal)

    try:
        from django.utils import timezone
        current_date = timezone.now().date()

        # Calculate months until target
        months_remaining = "unknown"
        if goal.target_date:
            from dateutil.relativedelta import relativedelta
            delta = relativedelta(goal.target_date, current_date)
            months_remaining = delta.years * 12 + delta.months

        prompt = f"""You are a financial advisor explaining simulation results.
Explain what the hypothetical changes would mean for the goal in clear, conversational language.

**IMPORTANT CONTEXT:**
- Today's Date: {current_date.strftime('%B %d, %Y')}
- Target Date: {goal.target_date.strftime('%B %d, %Y') if goal.target_date else 'Not set'}
- Months Remaining: {months_remaining} months
- Target Amount: {goal.target_value}
- Current Amount: {original['current_value']}

Goal: {goal.name}
Type: {goal.get_goal_type_display()}

Hypothetical Changes:
{json.dumps(changes, indent=2)}

Original Outcome:
- Status: {original['status']}
- Progress: {original['progress_percentage']}%
- Value: {original['current_value']}

Simulated Outcome:
- Status: {simulated['status']}
- Progress: {simulated['progress_percentage']}%
- Value: {simulated['current_value']}

Result: {'Goal achievable' if achieves_goal else 'Goal still challenging'}

Guidelines:
- Use the CURRENT DATE ({current_date.strftime('%B %Y')}) for calculations
- Calculate months remaining correctly: {months_remaining} months
- Start with the bottom line (would it help achieve the goal?)
- Explain HOW the changes improve (or don't improve) the situation
- Be specific with numbers
- Provide context about feasibility
- Keep it concise (2-3 paragraphs)
- Don't use markdown headings (###), use plain paragraphs

Explain what these changes would mean for achieving the goal."""

        narrative = ai_service._call_ai(prompt, max_tokens=800)

        if not narrative:
            logger.warning("AI returned no narrative for simulation, using fallback")
            return _fallback_simulation_narrative(goal, original, simulated, changes, achieves_goal)

        logger.info(f"Simulation narrative generated via AI")
        return narrative.strip()

    except Exception as e:
        logger.error(f"Error generating simulation narrative: {str(e)}")
        return _fallback_simulation_narrative(goal, original, simulated, changes, achieves_goal)


def _fallback_simulation_narrative(goal, original, simulated, changes, achieves_goal) -> str:
    """Fallback narrative without AI"""
    diff = _calculate_difference(original, simulated)

    if achieves_goal:
        result = "This change would help you achieve your goal!"
    else:
        result = "This change would improve your situation, but you'd still need additional adjustments."

    value_change_desc = f"increase by {abs(diff['value_change']):.2f}" if diff['value_change'] > 0 else f"decrease by {abs(diff['value_change']):.2f}"

    narrative = f"""{result}

With the proposed changes, your progress would {value_change_desc}, moving from {original['progress_percentage']:.1f}% to {simulated['progress_percentage']:.1f}% complete. Your status would change from {original['status']} to {simulated['status']}.

The changes would directly impact your goal by modifying your financial metrics. Consider whether these changes are realistic and sustainable for your business."""

    return narrative


def parse_simulation_request(user_message: str, goal) -> Dict:
    """
    Parse natural language simulation request using LLM.

    Args:
        user_message: User's simulation request in natural language
        goal: FinancialGoal instance for context

    Returns:
        Dict of hypothetical_changes to pass to run_simulation()

    Example inputs:
    - "What if I cut marketing spend by 20%?"
    - "What if we increase revenue by £5000 per month?"
    - "What if I get a one-time payment of £50,000?"
    """
    if not ai_service._check_ai_available():
        logger.info("AI not available, using fallback simulation parsing")
        return _fallback_parse_simulation(user_message)

    try:
        # Use the universal _call_ai function instead of direct OpenAI client
        prompt = f"""Parse this what-if question into structured simulation parameters.

Goal Type: {goal.get_goal_type_display()}
Question: "{user_message}"

Return ONLY valid JSON with the relevant fields:
{{
  "monthly_revenue_increase": 5000,  // If increasing revenue
  "monthly_expense_reduction": 1000,  // If reducing expenses by amount
  "expense_reduction_percentage": 20,  // If reducing expenses by %
  "one_time_income": 50000,  // If one-time payment
  "cut_category_spend": {{"category": "marketing", "percentage": 30}}  // If cutting specific category
}}

Only include fields that are mentioned in the question. Return valid JSON."""

        response_text = ai_service._call_ai(prompt, max_tokens=500)

        if not response_text:
            logger.warning("AI returned no response for simulation parsing, using fallback")
            return _fallback_parse_simulation(user_message)

        # Clean and parse JSON
        response_text = ai_service._clean_json_response(response_text)
        result = json.loads(response_text)

        logger.info(f"Simulation parsing successful via AI")

        # Return the changes directly if valid
        if result and isinstance(result, dict):
            return result

        return _fallback_parse_simulation(user_message)

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error in simulation: {e}")
        return _fallback_parse_simulation(user_message)
    except Exception as e:
        logger.error(f"Error parsing simulation request: {str(e)}")
        return _fallback_parse_simulation(user_message)


def _fallback_parse_simulation(user_message: str) -> Dict:
    """Fallback simulation parsing using keywords"""
    import re

    changes = {}
    msg_lower = user_message.lower()

    # Extract numbers
    numbers = re.findall(r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(%|percent|pounds?|£)?', user_message)

    if numbers:
        value = float(numbers[0][0].replace(',', ''))
        unit = numbers[0][1] if len(numbers[0]) > 1 else ''

        if '%' in unit or 'percent' in unit:
            if 'cut' in msg_lower or 'reduce' in msg_lower or 'decrease' in msg_lower:
                changes['expense_reduction_percentage'] = value
            else:
                changes['monthly_revenue_increase'] = value
        else:
            if 'revenue' in msg_lower or 'income' in msg_lower or 'increase' in msg_lower:
                if 'one' in msg_lower or 'once' in msg_lower:
                    changes['one_time_income'] = value
                else:
                    changes['monthly_revenue_increase'] = value
            elif 'cut' in msg_lower or 'reduce' in msg_lower or 'decrease' in msg_lower:
                changes['monthly_expense_reduction'] = value

    return changes

