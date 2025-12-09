# app_core/ai_service.py
"""
AI Financial Playbook - AI Service
Handles all LLM interactions with OpenAI, Google Gemini, or Hugging Face for goal parsing, explanations, and insights.
Supports multiple AI providers with automatic fallback.
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, date
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Check if OpenAI is available
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not installed.")

# Check if Google Gemini is available
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google Generative AI library not installed.")

# Check if Hugging Face is available
try:
    import requests
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False
    logger.warning("Requests library not installed for Hugging Face.")

# Check if Groq is available
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("Groq library not installed.")

def _check_ai_available() -> bool:
    """Check if AI features are available and configured"""
    if not settings.AI_PLAYBOOK_ENABLED:
        return False

    provider = settings.AI_PROVIDER.lower()

    if provider == "groq":
        if not GROQ_AVAILABLE:
            logger.warning("Groq library not available")
            return False
        if not settings.GROQ_API_KEY:
            logger.warning("Groq API key not configured")
            return False
        return True
    elif provider == "huggingface":
        if not HUGGINGFACE_AVAILABLE:
            logger.warning("Hugging Face library not available")
            return False
        if not settings.HUGGINGFACE_API_KEY:
            logger.warning("Hugging Face API key not configured")
            return False
        return True
    elif provider == "gemini":
        if not GEMINI_AVAILABLE:
            logger.warning("Gemini library not available")
            return False
        if not settings.GEMINI_API_KEY:
            logger.warning("Gemini API key not configured")
            return False
        return True
    elif provider == "openai":
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI library not available")
            return False
        if not settings.OPENAI_API_KEY:
            logger.warning("OpenAI API key not configured")
            return False
        return True
    else:
        logger.warning(f"Unknown AI provider: {provider}")
        return False


def _get_openai_client():
    """Get configured OpenAI client"""
    if settings.AI_PROVIDER.lower() != "openai":
        return None
    if not OPENAI_AVAILABLE or not settings.OPENAI_API_KEY:
        return None
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _get_gemini_model():
    """Get configured Gemini model"""
    if settings.AI_PROVIDER.lower() != "gemini":
        return None
    if not GEMINI_AVAILABLE or not settings.GEMINI_API_KEY:
        return None

    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel(settings.GEMINI_MODEL)


def _get_groq_client():
    """Get configured Groq client"""
    if settings.AI_PROVIDER.lower() != "groq":
        return None
    if not GROQ_AVAILABLE or not settings.GROQ_API_KEY:
        return None

    return Groq(api_key=settings.GROQ_API_KEY)


def _get_huggingface_client():
    """Check if Hugging Face is configured (we use requests directly)"""
    if settings.AI_PROVIDER.lower() != "huggingface":
        return None
    if not HUGGINGFACE_AVAILABLE or not settings.HUGGINGFACE_API_KEY:
        return None

    # Return True to indicate HF is available (we don't need a client object)
    return True


def _call_ai(prompt: str, max_tokens: int = None) -> str:
    """
    Universal AI call function that works with any configured provider.

    Args:
        prompt: The prompt to send to the AI
        max_tokens: Maximum tokens to generate (optional)

    Returns:
        AI generated text response
    """
    if not _check_ai_available():
        return None

    provider = settings.AI_PROVIDER.lower()
    max_tokens = max_tokens or settings.OPENAI_MAX_TOKENS

    try:
        if provider == "groq":
            client = _get_groq_client()
            if not client:
                return None

            # Call Groq API (same interface as OpenAI)
            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=settings.OPENAI_TEMPERATURE
            )

            logger.info(f"Groq API call successful")
            return response.choices[0].message.content

        elif provider == "huggingface":
            if not _get_huggingface_client():
                return None
            
            # Call Hugging Face serverless inference API directly using requests
            try:
                api_url = f"https://api-inference.huggingface.co/models/{settings.HUGGINGFACE_MODEL}"
                headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}

                payload = {
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": max_tokens,
                        "temperature": settings.OPENAI_TEMPERATURE,
                        "return_full_text": False,
                    }
                }

                response = requests.post(api_url, headers=headers, json=payload, timeout=30)
                response.raise_for_status()

                result = response.json()

                # Parse response - it returns a list with generated text
                if isinstance(result, list) and len(result) > 0:
                    text = result[0].get('generated_text', '')
                    logger.info(f"Hugging Face API call successful")
                    return text.strip()
                elif isinstance(result, dict):
                    text = result.get('generated_text', '')
                    logger.info(f"Hugging Face API call successful")
                    return text.strip()
                else:
                    logger.warning(f"Hugging Face returned unexpected format: {type(result)}")
                    return None
            except requests.exceptions.RequestException as e:
                logger.error(f"Hugging Face API call failed: {e}")
                return None
            except Exception as e:
                logger.error(f"Hugging Face API error: {e}")
                return None

        elif provider == "gemini":
            model = _get_gemini_model()
            if not model:
                return None

            # Configure generation settings with relaxed safety
            generation_config = {
                "max_output_tokens": max_tokens,
                "temperature": settings.OPENAI_TEMPERATURE,
            }

            # Configure safety settings to be less restrictive for financial content
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                }
            ]

            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )

            # Check if response was blocked
            if not response.candidates:
                logger.warning("Gemini response was blocked by safety filters")
                return None

            # Check if the response has valid parts
            if not response.parts:
                logger.warning(f"Gemini response has no parts. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'unknown'}")
                return None

            # Log token usage if available
            if hasattr(response, 'usage_metadata'):
                total_tokens = response.usage_metadata.total_token_count
                logger.info(f"Gemini API call used {total_tokens} tokens")

            return response.text

        elif provider == "openai":
            client = _get_openai_client()
            if not client:
                return None

            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=settings.OPENAI_TEMPERATURE
            )

            # Log token usage
            logger.info(f"OpenAI API call used {response.usage.total_tokens} tokens")

            return response.choices[0].message.content

    except Exception as e:
        logger.error(f"{provider.upper()} API error: {e}")
        return None

    return None


def _call_ai_with_messages(messages: list, max_tokens: int = None) -> str:
    """
    Call AI with message array (for conversations).

    Args:
        messages: List of message dicts with 'role' and 'content'
        max_tokens: Maximum tokens to generate

    Returns:
        AI response text
    """
    if not _check_ai_available():
        return None

    provider = settings.AI_PROVIDER.lower()

    if provider == "openai":
        try:
            client = _get_openai_client()
            if not client:
                return None

            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                max_tokens=max_tokens or settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE
            )

            logger.info(f"OpenAI conversation used {response.usage.total_tokens} tokens")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI conversation error: {e}")
            return None
    else:
        # For other providers, combine messages into a single prompt
        prompt = "\n\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        return _call_ai(prompt, max_tokens)


def _clean_json_response(response_text: str) -> str:
    """
    Clean up AI response to extract valid JSON.
    Handles markdown code blocks, extra text, and formatting issues.
    """
    if not response_text:
        return response_text

    # Remove markdown code blocks
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()

    # Remove any text before the first { or [
    json_start = response_text.find('{')
    if json_start == -1:
        json_start = response_text.find('[')
    if json_start > 0:
        response_text = response_text[json_start:]

    # Remove any text after the last } or ]
    json_end = response_text.rfind('}')
    if json_end == -1:
        json_end = response_text.rfind(']')
    if json_end > 0 and json_end < len(response_text) - 1:
        response_text = response_text[:json_end + 1]

    # Fix common JSON issues
    # Replace single quotes with double quotes (if not inside strings)
    # This is a simple fix - might not work for complex cases
    response_text = response_text.replace("'", '"')

    return response_text.strip()


def parse_natural_language_goal(user_input: str, organization) -> Dict:
    """
    Parse natural language input into structured goal.

    Args:
        user_input: User's goal description in natural language
        organization: Organization instance for context

    Returns:
        dict with: goal_type, name, description, target_value, target_date,
                   parameters, confidence, suggestions
    """
    if not _check_ai_available():
        return _fallback_parse_goal(user_input)

    try:
        prompt = f"""You are a financial goal parsing assistant. Parse the user's financial goal into a structured format.

Goal Types:
- runway: Cash runway (months of operating expenses in reserve)
- savings: Savings target (specific amount to save)
- spending_limit: Spending limit (max spend in category/period)
- budget_compliance: Budget compliance (stay within budget)
- revenue_target: Revenue target (achieve specific revenue)
- profit_margin: Profit margin (achieve % profit margin)

Return ONLY valid JSON with this exact structure:
{{
  "goal_type": "runway|savings|spending_limit|budget_compliance|revenue_target|profit_margin",
  "name": "Short goal name (max 50 chars)",
  "description": "Detailed description of what this goal means",
  "target_value": numeric value (amount, months, or percentage),
  "target_date": "YYYY-MM-DD" or null,
  "parameters": {{}},
  "confidence": 0.0-1.0,
  "suggestions": ["suggestion1", "suggestion2"]
}}

User's goal: {user_input}

Return ONLY the JSON, no other text."""

        response_text = _call_ai(prompt, max_tokens=800)
        
        if not response_text:
            logger.warning("AI goal parsing failed, using fallback")
            return _fallback_parse_goal(user_input)
        
        # Clean and parse JSON response
        response_text = _clean_json_response(response_text)
        result = json.loads(response_text)
        return result

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}. Response: {response_text[:200]}")
        return _fallback_parse_goal(user_input)
    except Exception as e:
        logger.error(f"Error parsing goal with AI: {str(e)}")
        return _fallback_parse_goal(user_input)


def _fallback_parse_goal(user_input: str) -> Dict:
    """Fallback goal parsing using simple keyword matching"""
    user_input_lower = user_input.lower()

    # Simple keyword detection
    goal_type = "savings"  # Default
    if "runway" in user_input_lower or "months" in user_input_lower:
        goal_type = "runway"
    elif "save" in user_input_lower or "savings" in user_input_lower:
        goal_type = "savings"
    elif "spend" in user_input_lower or "limit" in user_input_lower:
        goal_type = "spending_limit"
    elif "budget" in user_input_lower:
        goal_type = "budget_compliance"
    elif "revenue" in user_input_lower or "income" in user_input_lower:
        goal_type = "revenue_target"
    elif "margin" in user_input_lower or "profit" in user_input_lower:
        goal_type = "profit_margin"

    # Extract numbers
    import re
    numbers = re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?', user_input)
    target_value = float(numbers[0].replace(',', '')) if numbers else 10000

    # Extract dates (very basic)
    date_patterns = re.findall(r'\d{4}-\d{2}-\d{2}', user_input)
    target_date = date_patterns[0] if date_patterns else None

    return {
        "goal_type": goal_type,
        "name": user_input[:50],  # First 50 chars
        "description": f"Goal: {user_input}",
        "target_value": target_value,
        "target_date": target_date,
        "parameters": {},
        "confidence": 0.5,
        "suggestions": [
            "AI parsing unavailable. Please review and edit the parsed goal.",
            "Consider adding specific dates and amounts for better tracking."
        ]
    }


def generate_goal_explanation(goal, evaluation_data: Dict, historical_evaluations: List) -> str:
    """
    Generate narrative explanation of goal status with WHY analysis.

    Args:
        goal: FinancialGoal instance
        evaluation_data: Latest evaluation dict from playbook_engine
        historical_evaluations: List of recent GoalEvaluation instances

    Returns:
        Detailed narrative explanation string
    """
    if not _check_ai_available():
        return _fallback_explanation(goal, evaluation_data)

    try:
        # Build context from historical data
        history_context = ""
        if historical_evaluations:
            recent = historical_evaluations[:5]  # Last 5 evaluations
            history_context = "\n\nHistorical Progress:\n"
            for eval in recent:
                history_context += f"- {eval.evaluated_at.strftime('%Y-%m-%d')}: {eval.status}, {eval.progress_percentage}% complete\n"

        prompt = f"""You are a helpful financial advisor. Analyze this financial goal and provide insights.

Goal Details:
- Name: {goal.name}
- Type: {goal.get_goal_type_display()}
- Target: {goal.target_value} by {goal.target_date or 'no date set'}
- Current Status: {evaluation_data['status']}
- Progress: {evaluation_data['progress_percentage']}%
- Current Value: {evaluation_data['current_value']}

Recent Data:
{json.dumps(evaluation_data['metrics'], indent=2)}
{history_context}

Please explain in 2-3 paragraphs:
1. Why the goal is currently {evaluation_data['status']}
2. What factors are influencing the progress
3. What this means for achieving the target

Keep your response factual, professional, and encouraging."""

        explanation = _call_ai(prompt, max_tokens=settings.OPENAI_MAX_TOKENS)

        if not explanation:
            return _fallback_explanation(goal, evaluation_data)

        return explanation.strip()

    except Exception as e:
        logger.error(f"Error generating explanation: {str(e)}")
        return _fallback_explanation(goal, evaluation_data)


def _fallback_explanation(goal, evaluation_data: Dict) -> str:
    """Fallback template-based explanation"""
    status = evaluation_data['status']
    progress = evaluation_data['progress_percentage']
    current = evaluation_data['current_value']
    target = evaluation_data['target_value']

    if status == 'achieved':
        return f"Congratulations! You've achieved your goal of {target}. Your current value is {current}, which meets or exceeds your target."
    elif status == 'on_track':
        return f"Your goal is on track. You're currently at {current} ({progress}% of your {target} target). Keep up the good work and you should reach your goal on schedule."
    elif status == 'at_risk':
        return f"Your goal is at risk. You're at {current} ({progress}% of your {target} target). You may need to adjust your approach to reach your goal by the target date."
    elif status == 'off_track':
        return f"Your goal is off track. You're currently at {current}, which is {progress}% of your {target} target. Significant changes may be needed to achieve this goal."
    else:
        return f"Goal tracking has started. Current value: {current}. Target: {target}."


def generate_recommendations(goal, evaluation_data: Dict) -> List[Dict]:
    """
    Generate actionable recommendations.

    Returns:
        List of dicts: [{action, impact, priority, reasoning}]
    """
    if not _check_ai_available():
        return _fallback_recommendations(goal, evaluation_data)

    try:
        prompt = f"""Generate helpful suggestions for this financial goal in JSON format.

Goal: {goal.name}
Type: {goal.get_goal_type_display()}
Status: {evaluation_data['status']}
Progress: {evaluation_data['progress_percentage']}%
Current: {evaluation_data['current_value']}
Target: {evaluation_data['target_value']}

Provide 3-4 practical suggestions in this exact JSON format:
{{
  "recommendations": [
    {{
      "action": "Specific step to take",
      "impact": "Expected positive result",
      "priority": "high",
      "reasoning": "Brief explanation"
    }}
  ]
}}

Return only valid JSON."""

        response_text = _call_ai(prompt, max_tokens=settings.OPENAI_MAX_TOKENS)

        if not response_text:
            return _fallback_recommendations(goal, evaluation_data)

        # Clean and parse JSON response
        response_text = _clean_json_response(response_text)
        result = json.loads(response_text)
        recommendations = result.get('recommendations', [])

        return recommendations

    except json.JSONDecodeError as e:
        logger.error(f"Error parsing recommendations JSON: {e}")
        return _fallback_recommendations(goal, evaluation_data)
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        return _fallback_recommendations(goal, evaluation_data)


def _fallback_recommendations(goal, evaluation_data: Dict) -> List[Dict]:
    """Fallback template-based recommendations"""
    recommendations = []
    status = evaluation_data['status']
    goal_type = goal.goal_type

    if status in ['at_risk', 'off_track']:
        if goal_type == 'runway':
            recommendations.append({
                "action": "Reduce monthly expenses by 10-15%",
                "impact": "Extends runway and improves financial stability",
                "priority": "high",
                "reasoning": "Current burn rate is too high to reach target runway"
            })
        elif goal_type == 'savings':
            recommendations.append({
                "action": "Increase monthly savings allocation",
                "impact": "Accelerates progress toward savings goal",
                "priority": "high",
                "reasoning": "Current savings rate won't reach target on time"
            })
        elif goal_type == 'spending_limit':
            recommendations.append({
                "action": "Review and cut non-essential expenses",
                "impact": "Brings spending back within limit",
                "priority": "high",
                "reasoning": "Currently over or approaching spending limit"
            })

    if not recommendations:
        recommendations.append({
            "action": "Continue current approach",
            "impact": "Maintains progress toward goal",
            "priority": "low",
            "reasoning": "Goal is on track with current strategy"
        })

    return recommendations


def generate_trend_analysis(goal, historical_evaluations: List) -> str:
    """
    Analyze trends over time.

    Returns:
        Narrative trend analysis string
    """
    if not historical_evaluations or len(historical_evaluations) < 2:
        return "Not enough historical data for trend analysis yet. Check back after a few evaluations."

    if not _check_ai_available():
        return _fallback_trend_analysis(historical_evaluations)

    try:
        # Build trend data
        trend_data = []
        for eval in historical_evaluations[:10]:  # Last 10 evaluations
            trend_data.append({
                "date": eval.evaluated_at.strftime('%Y-%m-%d'),
                "status": eval.status,
                "progress": float(eval.progress_percentage),
                "value": float(eval.current_value) if eval.current_value else 0
            })

        prompt = f"""You are a financial analyst identifying trends and patterns.
Analyze the historical data and identify:
- Overall trend direction (improving/declining/stable)
- Rate of change (accelerating/decelerating)
- Any notable patterns or anomalies
- Seasonality if present

Be concise (1-2 paragraphs) and focus on actionable insights.

Goal: {goal.name}
Historical Data (most recent first):
{json.dumps(trend_data, indent=2)}

Analyze the trend and provide insights."""

        analysis = _call_ai(prompt, max_tokens=800)

        if not analysis:
            return _fallback_trend_analysis(historical_evaluations)

        return analysis.strip()

    except Exception as e:
        logger.error(f"Error generating trend analysis: {str(e)}")
        return _fallback_trend_analysis(historical_evaluations)


def _fallback_trend_analysis(historical_evaluations: List) -> str:
    """Fallback trend analysis using simple statistics"""
    if len(historical_evaluations) < 2:
        return "Not enough data for trend analysis."

    recent = historical_evaluations[:5]
    progress_values = [float(e.progress_percentage) for e in recent]

    if len(progress_values) >= 2:
        trend = progress_values[0] - progress_values[-1]
        if trend > 5:
            return f"Positive trend: Progress has increased by {trend:.1f}% over recent evaluations. Keep up the momentum!"
        elif trend < -5:
            return f"Concerning trend: Progress has decreased by {abs(trend):.1f}% recently. Consider reviewing your strategy."
        else:
            return "Progress is relatively stable with minor fluctuations. Maintain current approach."

    return "Trend data available but insufficient for analysis."


def identify_risk_factors(goal, evaluation_data: Dict) -> List[Dict]:
    """
    Identify risks to goal achievement.

    Returns:
        List of dicts: [{risk, severity, mitigation}]
    """
    if not _check_ai_available():
        return _fallback_risk_factors(goal, evaluation_data)

    try:
        prompt = f"""You are a risk analyst identifying potential threats to goal achievement.
Identify 2-4 key risk factors.

Return ONLY valid JSON in this exact format:
{{
  "risks": [
    {{
      "risk": "Description of the challenge",
      "severity": "high|medium|low",
      "mitigation": "Suggested approach to address it"
    }}
  ]
}}

Goal: {goal.name}
Type: {goal.get_goal_type_display()}
Status: {evaluation_data['status']}
Target Date: {goal.target_date or 'Not set'}
Current Progress: {evaluation_data['progress_percentage']}%

Identify potential challenges or concerns that might affect achieving this goal. Return only valid JSON."""

        response_text = _call_ai(prompt, max_tokens=settings.OPENAI_MAX_TOKENS)

        if not response_text:
            return _fallback_risk_factors(goal, evaluation_data)

        # Clean and parse JSON response
        response_text = _clean_json_response(response_text)
        result = json.loads(response_text)
        risks = result.get('risks', [])

        return risks

    except json.JSONDecodeError as e:
        logger.error(f"Error parsing risks JSON: {e}")
        return _fallback_risk_factors(goal, evaluation_data)
    except Exception as e:
        logger.error(f"Error identifying risks: {str(e)}")
        return _fallback_risk_factors(goal, evaluation_data)


def _fallback_risk_factors(goal, evaluation_data: Dict) -> List[Dict]:
    """Fallback risk identification"""
    risks = []
    status = evaluation_data['status']

    if status in ['at_risk', 'off_track']:
        risks.append({
            "risk": "Goal may not be achieved by target date",
            "severity": "high" if status == 'off_track' else "medium",
            "mitigation": "Review and adjust strategy, consider extending timeline or revising target"
        })

    if goal.target_date:
        days_left = (goal.target_date - timezone.now().date()).days
        if days_left < 30:
            risks.append({
                "risk": "Limited time remaining to achieve goal",
                "severity": "high",
                "mitigation": "Focus on high-impact actions, accelerate progress"
            })

    if not risks:
        risks.append({
            "risk": "No significant risks identified",
            "severity": "low",
            "mitigation": "Continue monitoring and maintain current approach"
        })

    return risks


def generate_forecast(goal, evaluation_data: Dict, historical_evaluations: List) -> Dict:
    """
    Forecast future outcomes.

    Returns:
        dict: {predicted_date, predicted_value, confidence, scenarios}
    """
    if not settings.PLAYBOOK_ENABLE_FORECASTING:
        return {"error": "Forecasting disabled"}

    if len(historical_evaluations) < 3:
        return {
            "predicted_date": None,
            "predicted_value": None,
            "confidence": 0,
            "message": "Not enough historical data for forecasting (need at least 3 evaluations)"
        }

    if not _check_ai_available():
        return _fallback_forecast(goal, evaluation_data, historical_evaluations)

    try:
        client = _get_openai_client()

        # Build historical data
        history = []
        for eval in historical_evaluations[:10]:
            history.append({
                "date": eval.evaluated_at.strftime('%Y-%m-%d'),
                "value": float(eval.current_value) if eval.current_value else 0,
                "progress": float(eval.progress_percentage)
            })

        system_prompt = """You are a financial forecaster predicting future outcomes.
Based on historical data, predict when the goal will be achieved and provide scenarios.

Return JSON:
{
  "predicted_date": "YYYY-MM-DD" or null,
  "predicted_value": numeric value at target date,
  "confidence": 0.0-1.0,
  "trend": "improving|declining|stable",
  "scenarios": {
    "optimistic": "Best case scenario description",
    "realistic": "Most likely scenario description",
    "pessimistic": "Worst case scenario description"
  }
}

Base predictions on the trend in the data."""

        user_message = f"""Goal: {goal.name}
Target: {evaluation_data['target_value']}
Target Date: {goal.target_date or 'Not set'}
Current: {evaluation_data['current_value']}

Historical Progress:
{json.dumps(history, indent=2)}

Generate forecast."""

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            response_format={"type": "json_object"}
        )

        forecast = json.loads(response.choices[0].message.content)
        logger.info(f"Forecast generation used {response.usage.total_tokens} tokens")

        return forecast

    except Exception as e:
        logger.error(f"Error generating forecast: {str(e)}")
        return _fallback_forecast(goal, evaluation_data, historical_evaluations)


def _fallback_forecast(goal, evaluation_data: Dict, historical_evaluations: List) -> Dict:
    """Simple linear projection forecast"""
    if len(historical_evaluations) < 2:
        return {
            "predicted_date": None,
            "predicted_value": None,
            "confidence": 0,
            "message": "Insufficient data for forecasting"
        }

    # Simple linear trend
    recent = historical_evaluations[:5]
    progress_values = [float(e.progress_percentage) for e in recent]

    if len(progress_values) >= 2:
        rate = (progress_values[0] - progress_values[-1]) / len(progress_values)

        current_progress = float(evaluation_data['progress_percentage'])
        remaining = 100 - current_progress

        if rate > 0:
            periods_to_goal = remaining / rate
            trend = "improving"
        else:
            periods_to_goal = None
            trend = "declining" if rate < 0 else "stable"

        return {
            "predicted_date": None,  # Would need date calculations
            "predicted_value": None,
            "confidence": 0.5,
            "trend": trend,
            "message": f"Based on recent trend, progress is {trend}"
        }

    return {
        "predicted_date": None,
        "predicted_value": None,
        "confidence": 0,
        "trend": "unknown",
        "message": "Unable to determine trend"
    }


def chat_conversation(conversation, user_message: str) -> str:
    """
    Handle conversational what-if simulations and Q&A.

    Args:
        conversation: PlaybookConversation instance
        user_message: User's message

    Returns:
        AI assistant's response
    """
    if not settings.PLAYBOOK_ENABLE_CONVERSATIONS:
        return "Conversational features are currently disabled."

    if not _check_ai_available():
        return "AI conversation features require OpenAI API configuration. Please contact your administrator."

    try:
        from django.utils import timezone
        from dateutil.relativedelta import relativedelta

        current_date = timezone.now().date()

        # Build conversation context
        goal_context = ""
        if conversation.goal:
            goal = conversation.goal

            # Calculate months remaining
            months_remaining = "unknown"
            if goal.target_date:
                delta = relativedelta(goal.target_date, current_date)
                months_remaining = delta.years * 12 + delta.months

            # Get recent transaction data
            from app_core.models import Transaction, Project, Budget, RecurringTransaction, ProjectTransaction
            from django.db.models import Sum, Q, Count, F
            from datetime import timedelta

            # Recent transactions (last 90 days) - ALL of them, not limited
            recent_transactions = Transaction.objects.filter(
                organization=goal.organization,
                date__gte=current_date - timedelta(days=90)
            ).order_by('-date')

            # Calculate totals properly - use direction field, not amount sign
            total_inflow = 0
            total_outflow = 0
            transaction_count = 0
            for t in recent_transactions:
                transaction_count += 1
                amount = abs(float(t.amount))  # Amount is always positive
                if t.direction == 'inflow':
                    total_inflow += amount
                else:  # 'outflow'
                    total_outflow += amount

            print(f"\n{'='*80}")
            print(f"🔍 AI CONTEXT DEBUG - Goal: {goal.name}")
            print(f"{'='*80}")
            print(f"📊 Transaction Count (Last 90 days): {transaction_count}")
            print(f"💰 Total Inflow: ${total_inflow:,.2f}")
            print(f"💸 Total Outflow: ${total_outflow:,.2f}")

            # Get expense breakdown by category (last 30 days)
            expense_by_category = Transaction.objects.filter(
                organization=goal.organization,
                date__gte=current_date - timedelta(days=30),
                direction='outflow'  # Filter by direction, not amount
            ).values('category').annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('-total')[:15]  # Order by highest spending first

            print(f"📝 Expense Categories (Last 30 days): {expense_by_category.count()} found")

            category_breakdown = ""
            monthly_expenses = 0
            if expense_by_category.exists():
                category_breakdown = "\n\nMonthly Expense Breakdown by Category (Last 30 days):\n"
                for cat in expense_by_category:
                    cat_name = cat['category'] or 'Uncategorized'
                    cat_amount = float(cat['total'] or 0)  # Amount is positive, no need for abs()
                    cat_count = cat['count']
                    monthly_expenses += cat_amount
                    category_breakdown += f"- {cat_name}: ${cat_amount:,.2f} ({cat_count} transactions)\n"
                    print(f"   • {cat_name}: ${cat_amount:,.2f} ({cat_count} txns)")
                category_breakdown += f"Total Monthly Expenses: ${monthly_expenses:,.2f}\n"
            else:
                category_breakdown = "\n\nMonthly Expense Breakdown: No expenses recorded in the last 30 days.\n"
                print(f"   ⚠️  NO EXPENSE CATEGORIES FOUND")

            # Get active projects with their spending
            projects = Project.objects.filter(
                organization=goal.organization,
                status='active'
            )[:10]

            projects_info = ""
            if projects.exists():
                projects_info = "\n\nActive Projects:\n"
                for proj in projects:
                    # Calculate actual spend from project allocations
                    # Sum up (transaction.amount * allocation_percentage / 100)
                    project_spend = 0
                    allocations = ProjectTransaction.objects.filter(
                        project=proj,
                        transaction__organization=goal.organization
                    ).select_related('transaction')

                    for alloc in allocations:
                        # Amount is already positive (direction field determines inflow/outflow)
                        allocated_amount = float(alloc.transaction.amount) * (float(alloc.allocation_percentage) / 100)
                        project_spend += allocated_amount

                    budget_info = ""
                    if proj.budget:
                        remaining = float(proj.budget) - project_spend
                        percent_used = (project_spend / float(proj.budget) * 100) if float(proj.budget) > 0 else 0
                        budget_info = f" | Budget: ${float(proj.budget):,.2f}, Spent: ${project_spend:,.2f} ({percent_used:.1f}%), Remaining: ${remaining:,.2f}"
                    projects_info += f"- {proj.name} ({proj.status}){budget_info}\n"

            # Get budgets with actual spend calculations
            budgets = Budget.objects.filter(
                organization=goal.organization,
                active=True
            ).order_by('-amount')[:10]

            budgets_info = ""
            if budgets.exists():
                budgets_info = "\n\nBudget Allocations:\n"
                for budget in budgets:
                    # Calculate actual spend for this budget
                    budget_transactions = Transaction.objects.filter(
                        organization=goal.organization,
                        direction='outflow'  # Only expenses - use direction field
                    )

                    # Filter by budget period
                    if budget.period == 'monthly':
                        budget_transactions = budget_transactions.filter(
                            date__gte=current_date.replace(day=1)
                        )
                    elif budget.period == 'weekly':
                        # Get current week
                        from datetime import timedelta
                        start_of_week = current_date - timedelta(days=current_date.weekday())
                        budget_transactions = budget_transactions.filter(
                            date__gte=start_of_week
                        )
                    elif budget.period == 'yearly':
                        budget_transactions = budget_transactions.filter(
                            date__year=current_date.year
                        )
                    elif budget.start_date and budget.end_date:
                        budget_transactions = budget_transactions.filter(
                            date__gte=budget.start_date,
                            date__lte=budget.end_date
                        )

                    # Filter by labels if budget has labels
                    if budget.labels.exists():
                        budget_transactions = budget_transactions.filter(
                            label__in=budget.labels.all()
                        )
                    elif budget.category:
                        budget_transactions = budget_transactions.filter(
                            category=budget.category
                        )

                    actual_spend = float(budget_transactions.aggregate(
                        total=Sum('amount')
                    )['total'] or 0)  # Amount is already positive for outflows

                    utilization = (actual_spend / float(budget.amount) * 100) if float(budget.amount) > 0 else 0
                    remaining = float(budget.amount) - actual_spend
                    period_label = f"{budget.get_period_display()}"
                    budgets_info += f"- {budget.name} ({period_label}): ${float(budget.amount):,.2f} allocated, ${actual_spend:,.2f} spent ({utilization:.1f}%), ${remaining:,.2f} remaining\n"

            # Get recurring transactions - filter by user OR organization transactions
            # Get user IDs from organization members
            org_user_ids = goal.organization.members.values_list('user_id', flat=True)
            recurring = RecurringTransaction.objects.filter(
                user_id__in=org_user_ids,
                active=True
            )[:20]

            recurring_info = ""
            monthly_recurring_income = 0
            monthly_recurring_expenses = 0

            if recurring.exists():
                recurring_info = "\n\nRecurring Transactions:\n"
                for rec in recurring:
                    # Convert frequency to monthly equivalent
                    frequency_map = {
                        'daily': 30,
                        'weekly': 4.33,
                        'monthly': 1,
                        'yearly': 0.083
                    }
                    multiplier = frequency_map.get(rec.frequency, 1)
                    monthly_amount = abs(float(rec.amount)) * multiplier

                    if rec.direction == 'inflow':
                        monthly_recurring_income += monthly_amount
                        recurring_info += f"- {rec.description}: +${monthly_amount:,.2f}/month ({rec.get_frequency_display()})\n"
                    else:
                        monthly_recurring_expenses += monthly_amount
                        recurring_info += f"- {rec.description}: -${monthly_amount:,.2f}/month ({rec.get_frequency_display()})\n"

                recurring_info += f"\nTotal Recurring Income: ${monthly_recurring_income:,.2f}/month\n"
                recurring_info += f"Total Recurring Expenses: ${monthly_recurring_expenses:,.2f}/month\n"
                recurring_info += f"Net Recurring: ${(monthly_recurring_income - monthly_recurring_expenses):,.2f}/month\n"

            # Calculate average monthly metrics
            months_of_data = 3  # 90 days = ~3 months
            avg_monthly_inflow = total_inflow / months_of_data if months_of_data > 0 else 0
            avg_monthly_outflow = total_outflow / months_of_data if months_of_data > 0 else 0
            avg_monthly_net = avg_monthly_inflow - avg_monthly_outflow

            # Print final summary that AI will see
            print(f"\n📈 CALCULATED AVERAGES (90 days / 3 months):")
            print(f"   Avg Monthly Inflow: ${avg_monthly_inflow:,.2f}")
            print(f"   Avg Monthly Outflow: ${avg_monthly_outflow:,.2f}")
            print(f"   Avg Monthly Net: ${avg_monthly_net:,.2f}")
            print(f"   Monthly Expenses (last 30d): ${monthly_expenses:,.2f}")
            print(f"{'='*80}\n")

            goal_context = f"""
Current Goal Context:
- Goal: {goal.name}
- Type: {goal.get_goal_type_display()}
- Target Amount: ${float(goal.target_value):,.2f}
- Target Date: {goal.target_date.strftime('%B %d, %Y') if goal.target_date else 'Not set'}
- Current Status: {goal.current_status}
- Current Progress: {goal.progress_percentage}%
- Current Value: ${float(goal.current_value):,.2f} (out of ${float(goal.target_value):,.2f})

**IMPORTANT DATE CONTEXT:**
- Today's Date: {current_date.strftime('%B %d, %Y')}
- Months Until Target: {months_remaining} months
- Amount Remaining: ${float(goal.target_value - goal.current_value):,.2f}
- Monthly Savings Needed: ${(float(goal.target_value - goal.current_value) / months_remaining if months_remaining > 0 else 0):,.2f}

Financial Activity (Last 90 days):
- Total Inflow: ${total_inflow:,.2f}
- Total Outflow: ${total_outflow:,.2f}
- Net: ${(total_inflow - total_outflow):,.2f}
- Transaction Count: {len(recent_transactions)}
- Average Monthly Inflow: ${avg_monthly_inflow:,.2f}
- Average Monthly Outflow: ${avg_monthly_outflow:,.2f}
- Average Monthly Net: ${avg_monthly_net:,.2f}
{category_breakdown}{recurring_info}{projects_info}{budgets_info}
"""

        system_prompt = f"""You are a financial planning assistant helping with what-if scenarios and goal planning.
You can answer questions about financial goals, run hypothetical scenarios, and provide guidance.

{goal_context}

**CRITICAL INSTRUCTIONS:**
1. Always use TODAY'S DATE ({current_date.strftime('%B %d, %Y')}) for calculations
2. The target date is {conversation.goal.target_date.strftime('%B %d, %Y') if conversation.goal and conversation.goal.target_date else 'unknown'}
3. Calculate months remaining as {months_remaining} months (NOT years!)
4. YOU HAVE COMPLETE FINANCIAL DATA ABOVE - Use it! Including:
   - Actual monthly expenses by category
   - Recurring income and expenses  
   - Active projects and their budgets
   - Budget allocations and utilization
   - Average monthly cash flow
   - Transaction history
5. DO NOT use ANY markdown formatting - no ###, ##, #, **, *, or other markdown
6. Use plain text paragraphs only - just regular sentences separated by blank lines
7. When discussing expenses, reference the ACTUAL category breakdown shown above
8. When discussing income, reference the ACTUAL recurring income shown above
9. Be specific with numbers from the actual data provided
10. NEVER say "if you share your expenses" or "I don't have that data" - YOU HAVE ALL THE DATA!

Guidelines:
- Be conversational and helpful
- Provide specific, actionable advice based on the COMPLETE financial data shown above
- Reference actual numbers: monthly expenses (${monthly_expenses:,.2f}), recurring income (${monthly_recurring_income:,.2f}), etc.
- When calculating what's needed, use the actual average monthly net: ${avg_monthly_net:,.2f}
- When suggesting cuts, reference specific expense categories with their actual amounts
- When discussing timeline, use months remaining: {months_remaining} months
- Calculate time periods correctly using the dates provided
- Consider recurring transactions when making projections
- Reference active projects and budgets when relevant
- Be realistic but encouraging
- Write in plain paragraphs without any special formatting"""

        # Build message history
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (last 10 messages)
        for msg in conversation.messages[-10:]:
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })

        # Add new user message
        messages.append({"role": "user", "content": user_message})

        response = _call_ai_with_messages(messages, max_tokens=settings.OPENAI_MAX_TOKENS)

        if not response:
            return "I'm having trouble connecting to the AI service. Please try again."

        logger.info(f"Conversation completed successfully")
        return response.strip()

    except Exception as e:
        logger.error(f"Error in chat conversation: {str(e)}")
        return "I encountered an error processing your message. Please try rephrasing your question."



def get_playbook_insights(organization, context: str = 'dashboard') -> List[Dict]:
    """
    Generate AI insights for display on Playbook page or dashboard.
    Enhances/replaces existing insights.py functionality.

    Args:
        organization: Organization instance
        context: 'dashboard' or 'playbook' - determines scope and detail

    Returns:
        List of dicts: [{title, content, severity, goal_id, action}]
    """
    from .models import FinancialGoal

    insights = []

    # Get active goals
    goals = FinancialGoal.objects.filter(
        organization=organization,
        active=True
    ).order_by('-last_evaluated_at')[:5]

    for goal in goals:
        severity = 'info'
        if goal.current_status == 'achieved':
            severity = 'good'
        elif goal.current_status == 'at_risk':
            severity = 'warn'
        elif goal.current_status == 'off_track':
            severity = 'bad'

        insights.append({
            'title': f"{goal.name}",
            'content': goal.last_explanation or f"{goal.current_status.replace('_', ' ').title()} - {goal.progress_percentage}% complete",
            'severity': severity,
            'goal_id': goal.id,
            'action': f'View goal details'
        })

    if not insights:
        insights.append({
            'title': 'No Active Goals',
            'content': 'Create your first financial goal to get AI-powered insights and guidance.',
            'severity': 'info',
            'goal_id': None,
            'action': 'Create a goal'
        })

    return insights

