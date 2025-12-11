# AI Financial Playbook - Technical Documentation

## Overview

### Current Application
Finance Insights MVP is a Django-based financial management system for small businesses that provides:
- Transaction management with labels, categories, and multi-organization support
- Budget tracking with recurring budgets and custom periods
- Hierarchical project/cost center tracking (3 levels deep)
- Financial reporting with time-series analysis and KPIs
- Customizable dashboard with widget system
- Team collaboration with organization-based permissions

### The AI Financial Playbook Feature
The **AI Financial Playbook** (referred to internally as "AI Goal Insights & Co-Pilot") transforms passive financial tracking into proactive financial intelligence. It's a conversational AI system that:

- Accepts financial goals in **natural language** (e.g., "Have 6 months of runway by March 2026")
- Continuously **evaluates progress** using existing transaction/budget/project data
- Generates **deep narrative explanations** with WHY analysis, actionable recommendations, trend analysis, risk factors, and forecasting
- Enables **AI-driven conversations** for what-if scenario planning
- Provides **real-time insights** integrated throughout the application

### Why This Is Different from Traditional Dashboards

**Traditional dashboards:**
- Show historical data (what happened)
- Require users to interpret metrics
- Reactive - users must check manually
- Generic insights based on simple rules

**AI Financial Playbook:**
- **Goal-oriented** - tracks what you want to achieve, not just what happened
- **Proactive** - continuously monitors and alerts when goals are at risk
- **Explanatory** - tells you WHY things are happening in plain English
- **Predictive** - forecasts outcomes and models scenarios
- **Conversational** - answer questions and explore what-if scenarios naturally
- **Contextual** - understands your business context and provides personalized recommendations

---

## Existing Building Blocks to Reuse

The Finance Insights MVP already has robust foundations that the AI Playbook will leverage:

### Transaction & Budget Data (`app_core/models.py`)
- **Transaction model** - Complete transaction history with labels, categories, amounts, dates, organization FK
- **Budget model** - Multi-label budgets with recurring support and custom periods
- **RecurringTransaction model** - Automated recurring income/expenses
- **Project model** - Hierarchical project tracking with budget allocation (via `projects.py`)
- **Label model** - Flexible categorization system

**Implementation Note:** The AI Playbook will query these models directly using the same patterns as existing reports. Do NOT duplicate transaction logic.

### Metrics & Analytics (`app_core/metrics.py`)
- **`queryset_to_df()`** - Converts Django QuerySets to Pandas DataFrames
- **`kpis()`** - Calculates inflow, outflow, net, transaction counts
- **`timeseries()`** - Aggregates data by period (daily/weekly/monthly/yearly) with gap filling

**Implementation Note:** Goal evaluation should use these existing functions for consistency. The AI explanation layer sits on top of these calculations.

### Basic Insights Engine (`app_core/insights.py`)
- **`generate_insights()`** - Currently generates rule-based insights:
  - Period summaries
  - Top spending categories
  - Best/worst revenue days
  - Notable variance detection (statistical spike analysis)

**Implementation Note:** This will be extended/replaced with AI-powered insights for the Playbook page. The basic insights can remain for lightweight views or as fallback.

### Dashboard System (`app_core/dashboard_models.py`, `app_web/dashboard_views.py`)
- **DashboardLayout model** - Stores user/organization widget configurations
- **Widget system** - Modular dashboard components with JSON config

**Implementation Note:** The Playbook will add new widgets showing goal status, AI insights, and recommendations.

### Organization & Permissions (`app_core/team_models.py`, `app_core/permissions.py`)
- **Organization model** - Multi-tenant support
- **OrganizationMember** - User-organization relationships with roles
- **Middleware** - `@organization_required` decorator for view protection

**Implementation Note:** All new Playbook models must include `organization` FK. Goals are organization-level (shared across team members).

### Reporting Patterns (`app_web/views.py`, `app_core/projects.py`)
- Existing query patterns for filtering by date range, organization, labels
- Project summary calculations with hierarchy support
- Budget vs actual variance calculations

**Implementation Note:** Reuse these query patterns in goal evaluation. For example, runway calculations should use the same logic as project/budget summaries.

---

## New Components for the AI Playbook

### Backend Components (in `app_core/`)

#### 1. **Financial Goal Model** (`app_core/playbook_models.py` - NEW FILE)

```python
class FinancialGoal(models.Model):
    """
    User-defined financial goals created via natural language input.
    Organization-level, evaluated continuously by AI.
    """
    GOAL_TYPES = [
        ('runway', 'Cash Runway'),
        ('savings', 'Savings Target'),
        ('spending_limit', 'Spending Limit'),
        ('budget_compliance', 'Budget Compliance'),
        ('revenue_target', 'Revenue Target'),
        ('profit_margin', 'Profit Margin'),
    ]
    
    STATUS_CHOICES = [
        ('on_track', 'On Track'),
        ('at_risk', 'At Risk'),
        ('off_track', 'Off Track'),
        ('achieved', 'Achieved'),
        ('not_started', 'Not Started'),
    ]
    
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name='financial_goals')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_goals')
    
    # Natural language input
    natural_language_input = models.TextField(help_text="User's original goal description")
    
    # Parsed/structured goal (generated by LLM, confirmed by user)
    goal_type = models.CharField(max_length=32, choices=GOAL_TYPES)
    name = models.CharField(max_length=255, help_text="Short goal name")
    description = models.TextField(blank=True, help_text="AI-generated description")
    
    # Goal parameters (JSON for flexibility across different goal types)
    target_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    target_date = models.DateField(null=True, blank=True)
    parameters = models.JSONField(default=dict, help_text="Type-specific parameters")
    
    # Current status
    current_status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='not_started')
    current_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    progress_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # AI-generated insights (cached, regenerated on evaluation)
    last_explanation = models.TextField(blank=True, help_text="Latest AI explanation")
    last_recommendations = models.JSONField(default=list, help_text="List of AI recommendations")
    last_evaluated_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'active']),
            models.Index(fields=['goal_type', 'current_status']),
        ]
```

#### 2. **Goal Evaluation History Model** (`app_core/playbook_models.py`)

```python
class GoalEvaluation(models.Model):
    """
    Snapshot of goal evaluation at a point in time.
    Used for trend analysis and historical tracking.
    """
    goal = models.ForeignKey(FinancialGoal, on_delete=models.CASCADE, related_name='evaluations')
    
    # Snapshot data
    evaluated_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=16, choices=FinancialGoal.STATUS_CHOICES)
    current_value = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    progress_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Metrics snapshot (JSON for flexibility)
    metrics = models.JSONField(default=dict, help_text="KPIs and calculations at this point")
    
    # AI analysis
    explanation = models.TextField(blank=True)
    recommendations = models.JSONField(default=list)
    risk_factors = models.JSONField(default=list, help_text="Identified risks")
    trend_analysis = models.TextField(blank=True, help_text="AI trend commentary")
    forecast = models.JSONField(default=dict, help_text="Predicted outcomes")
    
    class Meta:
        ordering = ['-evaluated_at']
        indexes = [
            models.Index(fields=['goal', 'evaluated_at']),
        ]
```

#### 3. **AI Conversation Model** (`app_core/playbook_models.py`)

```python
class PlaybookConversation(models.Model):
    """
    Stores AI conversations for what-if simulations and Q&A.
    Maintains context across multiple messages.
    """
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name='playbook_conversations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='playbook_conversations')
    goal = models.ForeignKey(FinancialGoal, on_delete=models.CASCADE, null=True, blank=True, related_name='conversations')
    
    # Conversation metadata
    title = models.CharField(max_length=255, help_text="Auto-generated from first message")
    conversation_type = models.CharField(max_length=32, default='what_if', choices=[
        ('what_if', 'What-If Simulation'),
        ('goal_discussion', 'Goal Discussion'),
        ('general_insights', 'General Insights'),
    ])
    
    # Messages stored as JSON array
    messages = models.JSONField(default=list, help_text="[{role, content, timestamp}]")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
```

#### 4. **Goal Evaluation Engine** (`app_core/playbook_engine.py` - NEW FILE)

Service that evaluates goals using existing transaction/budget data.

**Key Functions:**
```python
def evaluate_goal(goal: FinancialGoal, as_of_date: date = None) -> dict:
    """
    Calculate current progress for a goal.
    Returns dict with: current_value, target_value, progress_percentage, status, metrics
    """
    # Reuses metrics.py functions (kpis, timeseries)
    # Queries Transaction/Budget models with organization filtering
    # Type-specific evaluation logic for each goal type

def calculate_runway(organization: Organization, as_of_date: date = None) -> dict:
    """Calculate months of runway based on current burn rate"""
    # Uses existing transaction query patterns
    
def calculate_savings_progress(goal: FinancialGoal) -> dict:
    """Track progress toward savings target"""
    
def calculate_spending_limit_compliance(goal: FinancialGoal) -> dict:
    """Check if spending is within limits"""
    
def calculate_budget_compliance(goal: FinancialGoal) -> dict:
    """Compare actual vs budget using existing Budget model logic"""
```

**Implementation Notes:**
- Must reuse `app_core/metrics.py` functions
- Must use same query patterns as `app_core/projects.py` and `app_web/views.py`
- All queries must filter by `organization`
- Return standardized dict structure for all goal types

#### 5. **AI Service** (`app_core/ai_service.py` - NEW FILE)

Handles all LLM interactions with OpenAI API.

**Key Functions:**
```python
def parse_natural_language_goal(user_input: str, organization: Organization) -> dict:
    """
    Parse natural language input into structured goal.
    Returns: {goal_type, name, description, target_value, target_date, parameters, confidence}
    User confirms before saving.
    """

def generate_goal_explanation(goal: FinancialGoal, evaluation_data: dict, historical_evaluations: list) -> str:
    """
    Generate narrative explanation of goal status.
    Includes WHY analysis using current + historical data.
    """

def generate_recommendations(goal: FinancialGoal, evaluation_data: dict) -> list[dict]:
    """
    Generate actionable recommendations.
    Returns: [{action, impact, priority, reasoning}]
    """

def generate_trend_analysis(goal: FinancialGoal, historical_evaluations: list) -> str:
    """
    Analyze trends over time.
    Identifies patterns, acceleration/deceleration, seasonality.
    """

def identify_risk_factors(goal: FinancialGoal, evaluation_data: dict) -> list[dict]:
    """
    Identify risks to goal achievement.
    Returns: [{risk, severity, mitigation}]
    """

def generate_forecast(goal: FinancialGoal, evaluation_data: dict, historical_evaluations: list) -> dict:
    """
    Forecast future outcomes.
    Returns: {predicted_date, predicted_value, confidence, scenarios}
    """

def chat_conversation(conversation: PlaybookConversation, user_message: str) -> str:
    """
    Handle conversational what-if simulations.
    Maintains context, can run simulations, answer questions.
    """

def get_playbook_insights(organization: Organization, context: str = 'dashboard') -> list[dict]:
    """
    Generate AI insights for display on Playbook page or dashboard.
    Replaces/enhances existing insights.py for AI-powered insights.
    Returns: [{title, content, severity, goal_id, action}]
    """
```

**Configuration:**
- Uses environment variables: `OPENAI_API_KEY`, `OPENAI_MODEL` (default: gpt-4o-mini), `AI_PLAYBOOK_ENABLED`
- Graceful fallback if API key not set (template-based responses)
- Error handling for API failures
- Token usage logging for cost monitoring
- Rate limiting to prevent abuse

#### 6. **What-If Simulation Service** (`app_core/playbook_simulations.py` - NEW FILE)

```python
def run_simulation(goal: FinancialGoal, hypothetical_changes: dict, as_of_date: date = None) -> dict:
    """
    Run what-if simulation by modifying metrics and re-evaluating.
    
    hypothetical_changes examples:
    - {"monthly_revenue_increase": 5000}
    - {"expense_reduction_percentage": 10, "category": "Marketing"}
    - {"one_time_income": 50000, "date": "2026-01-15"}
    
    Returns: {
        original_outcome: {...},
        simulated_outcome: {...},
        difference: {...},
        achieves_goal: bool,
        narrative: str (AI-generated)
    }
    """
    # Uses metrics.py functions with modified data
    # Re-runs evaluation logic with hypothetical transactions

def parse_simulation_request(user_message: str, goal: FinancialGoal) -> dict:
    """
    Parse natural language simulation request using LLM.
    Example: "What if I cut marketing spend by 20%?" 
    Returns: {hypothetical_changes dict}
    """
```

### Scheduling Components

#### 7. **Periodic Evaluation Management Command** (`app_core/management/commands/evaluate_playbook_goals.py` - NEW FILE)

```python
# manage.py evaluate_playbook_goals [--organization-id=X] [--goal-id=Y]

class Command(BaseCommand):
    help = 'Evaluate all active financial goals and generate AI insights'
    
    def handle(self, *args, **options):
        # Get all active goals (optionally filtered)
        # For each goal:
        #   - Run evaluation engine
        #   - Create GoalEvaluation snapshot
        #   - Generate AI explanation/recommendations/forecast
        #   - Update goal current_status and cached fields
        #   - Log results
```

**Scheduling:**
- Run daily via cron: `0 2 * * * cd /path && python manage.py evaluate_playbook_goals`
- Or use Django-Q/Celery for more sophisticated scheduling
- Can also be triggered on-demand from UI

### Frontend Components (in `app_web/`)

#### 8. **Playbook Views** (`app_web/playbook_views.py` - NEW FILE)

```python
@login_required
@organization_required
def playbook_overview(request):
    """
    Main Playbook page showing all goals, AI insights, and recommendations.
    Replaces/enhances the basic insights page.
    """

@login_required
@organization_required
def create_goal(request):
    """
    Natural language goal creation flow.
    POST: User submits text -> LLM parses -> Returns confirmation form
    """

@login_required
@organization_required
def confirm_goal(request, temp_goal_id):
    """
    User confirms/edits LLM-parsed goal before saving.
    """

@login_required
@organization_required
def goal_detail(request, goal_id):
    """
    Detailed goal view with:
    - Progress chart (historical evaluations)
    - Latest AI explanation
    - Recommendations
    - Risk factors
    - Trend analysis
    - Forecast
    - What-if simulator interface
    """

@login_required
@organization_required
def goal_conversation(request, goal_id):
    """
    Conversational what-if interface.
    POST: User message -> AI response with simulation results
    """

@login_required
@organization_required
def refresh_goal_evaluation(request, goal_id):
    """
    Manually trigger real-time goal evaluation.
    Runs evaluation engine and AI analysis on-demand.
    """

@login_required
@organization_required
def playbook_api_insights(request):
    """
    API endpoint for fetching AI insights for dashboard widget.
    Returns JSON with top 3-5 insights.
    """
```

#### 9. **Playbook Templates** (`app_web/templates/app_web/playbook/`)

**New templates needed:**
- `playbook_overview.html` - Main Playbook page with goals list, insights panel
- `create_goal.html` - Natural language input form
- `confirm_goal.html` - Review/edit parsed goal
- `goal_detail.html` - Detailed goal view with charts, AI analysis, chat interface
- `partials/_goal_card.html` - Reusable goal status card
- `partials/_playbook_insights.html` - AI insights panel
- `partials/_what_if_chat.html` - Conversational what-if interface

**UI/UX Notes:**
- Reuse existing CSS patterns from `app_web/static/`
- Use Chart.js for progress charts (already used in dashboard)
- Modern, conversational UI for AI interactions
- Real-time updates using AJAX/fetch
- Loading states while AI generates responses

#### 10. **Dashboard Widget** (`app_web/dashboard_views.py` - EXTEND EXISTING)

Add new widget functions:
```python
@login_required
@organization_required
def widget_playbook_goals(request):
    """
    Widget showing 2-3 most critical goals with status.
    Used on main dashboard.
    """

@login_required
@organization_required
def widget_playbook_insights(request):
    """
    Widget showing AI-generated insights.
    Can replace or complement existing insights widget.
    """
```

Update `DashboardLayout` default config to include Playbook widgets.

#### 11. **Navigation Integration** (`app_web/templates/partials/_nav.html` - EXTEND)

Add "Playbook" link to main navigation between Dashboard and Reports.

---

## Implementation Roadmap (Step-by-Step)

### Phase 1: Foundation (Backend Core)
**Goal:** Get basic goal tracking working without AI first

**1.1 Create Goal Models**
- Files: `app_core/playbook_models.py`
- Create `FinancialGoal`, `GoalEvaluation`, `PlaybookConversation` models
- Run migrations
- Register models in `app_core/admin.py` for testing

**1.2 Build Evaluation Engine**
- Files: `app_core/playbook_engine.py`
- Implement `evaluate_goal()` with support for 2-3 goal types (runway, savings, spending limit)
- Reuse `metrics.py` functions extensively
- Write unit tests for calculations

**1.3 Create Management Command**
- Files: `app_core/management/commands/evaluate_playbook_goals.py`
- Basic evaluation loop without AI
- Test with sample goals

### Phase 2: AI Integration (Intelligence Layer)
**Goal:** Add OpenAI-powered intelligence

**2.1 Set Up AI Service**
- Files: `app_core/ai_service.py`, `financeinsights/settings.py`
- Add environment variables: `OPENAI_API_KEY`, `OPENAI_MODEL`, `AI_PLAYBOOK_ENABLED`
- Implement `parse_natural_language_goal()` with confirmation flow
- Add basic error handling and fallbacks

**2.2 Implement AI Explanation Generation**
- Files: `app_core/ai_service.py`
- Implement `generate_goal_explanation()` with WHY analysis
- Implement `generate_recommendations()` for actionable advice
- Implement `generate_trend_analysis()` using historical evaluations
- Implement `identify_risk_factors()` for proactive warnings
- Implement `generate_forecast()` for predictions

**2.3 Update Evaluation Command**
- Files: `app_core/management/commands/evaluate_playbook_goals.py`
- Integrate AI service calls
- Store results in `GoalEvaluation` model
- Update cached fields on `FinancialGoal`

### Phase 3: Basic UI (MVP User Interface)
**Goal:** Make it usable through web interface

**3.1 Create Playbook Views**
- Files: `app_web/playbook_views.py`, `app_web/urls.py`
- Implement `playbook_overview()` - list goals and insights
- Implement `create_goal()` - natural language input
- Implement `confirm_goal()` - review parsed goal
- Add URL patterns

**3.2 Build Basic Templates**
- Files: `app_web/templates/app_web/playbook/*.html`
- `playbook_overview.html` - main page
- `create_goal.html` - input form
- `confirm_goal.html` - confirmation form
- Reuse existing CSS/JS patterns

**3.3 Add Navigation**
- Files: `app_web/templates/partials/_nav.html`
- Add "Playbook" menu item
- Update active state logic

### Phase 4: Goal Detail & History
**Goal:** Rich goal detail pages with charts

**4.1 Goal Detail View**
- Files: `app_web/playbook_views.py`
- Implement `goal_detail()` with full AI analysis
- Fetch historical evaluations for trend charts

**4.2 Goal Detail Template**
- Files: `app_web/templates/app_web/playbook/goal_detail.html`
- Progress chart using Chart.js
- AI explanation display
- Recommendations list
- Risk factors panel
- Trend analysis section
- Forecast visualization

**4.3 Real-Time Evaluation**
- Files: `app_web/playbook_views.py`
- Implement `refresh_goal_evaluation()` for manual refresh
- AJAX endpoint for on-demand evaluation
- Loading states in frontend

### Phase 5: What-If Simulator
**Goal:** Conversational scenario planning

**5.1 Simulation Engine**
- Files: `app_core/playbook_simulations.py`
- Implement `run_simulation()` with hypothetical changes
- Implement `parse_simulation_request()` using LLM

**5.2 Conversation Interface**
- Files: `app_web/playbook_views.py`
- Implement `goal_conversation()` for chat-style what-if
- Store conversation history in `PlaybookConversation`

**5.3 Chat UI**
- Files: `app_web/templates/app_web/playbook/goal_detail.html`
- Add chat interface component
- Real-time message streaming (or polling)
- Display simulation results visually

### Phase 6: Dashboard Integration
**Goal:** Surface Playbook insights throughout app

**6.1 Dashboard Widgets**
- Files: `app_web/dashboard_views.py`
- Implement `widget_playbook_goals()` - top goals widget
- Implement `widget_playbook_insights()` - AI insights widget
- Update default dashboard layout

**6.2 Enhanced Insights**
- Files: `app_core/ai_service.py`
- Implement `get_playbook_insights()` for general AI insights
- Can enhance/replace existing `insights.py` logic

**6.3 Widget Templates**
- Files: `app_web/templates/app_web/widgets/`
- Create widget templates for Playbook components
- Ensure responsive design

### Phase 7: Polish & Optimization
**Goal:** Production-ready features

**7.1 Error Handling**
- Graceful degradation when API fails
- Clear user messaging
- Fallback templates when AI unavailable

**7.2 Performance**
- Cache AI responses where appropriate
- Optimize queries (select_related, prefetch_related)
- Background task processing for slow operations

**7.3 Testing**
- Unit tests for evaluation engine
- Integration tests for AI service (with mocked API)
- End-to-end tests for goal creation flow

**7.4 Documentation**
- User guide for Playbook feature
- API documentation for future extensions
- Environment variable reference

---

## Suggested Ticket Breakdown

### Epic 1: Backend Foundation
- **TICKET-001**: Create Playbook models (FinancialGoal, GoalEvaluation, PlaybookConversation)
- **TICKET-002**: Implement goal evaluation engine (playbook_engine.py) with runway, savings, spending limit support
- **TICKET-003**: Create evaluate_playbook_goals management command
- **TICKET-004**: Write unit tests for evaluation calculations

### Epic 2: AI Intelligence
- **TICKET-005**: Set up AI service infrastructure (ai_service.py, settings, env vars)
- **TICKET-006**: Implement natural language goal parsing with confirmation flow
- **TICKET-007**: Implement AI explanation generation (WHY + context)
- **TICKET-008**: Implement AI recommendations generation
- **TICKET-009**: Implement trend analysis and forecasting
- **TICKET-010**: Implement risk factor identification
- **TICKET-011**: Add error handling, fallbacks, and rate limiting

### Epic 3: Basic UI
- **TICKET-012**: Create Playbook views (overview, create, confirm)
- **TICKET-013**: Build Playbook templates (overview, create, confirm)
- **TICKET-014**: Add Playbook navigation menu item
- **TICKET-015**: Style Playbook pages using existing CSS patterns

### Epic 4: Goal Detail & History
- **TICKET-016**: Implement goal detail view with historical data
- **TICKET-017**: Build goal detail template with Chart.js progress charts
- **TICKET-018**: Add real-time evaluation refresh functionality
- **TICKET-019**: Display AI analysis components (explanation, recommendations, risks, forecast)

### Epic 5: What-If Simulator
- **TICKET-020**: Implement simulation engine (playbook_simulations.py)
- **TICKET-021**: Create conversation interface for what-if scenarios
- **TICKET-022**: Build chat UI for conversational simulations
- **TICKET-023**: Add simulation result visualization

### Epic 6: Dashboard Integration
- **TICKET-024**: Create Playbook dashboard widgets (goals, insights)
- **TICKET-025**: Integrate AI insights throughout app
- **TICKET-026**: Update default dashboard layout with Playbook widgets

### Epic 7: Testing & Polish
- **TICKET-027**: Write comprehensive tests (unit, integration, E2E)
- **TICKET-028**: Performance optimization (caching, query optimization)
- **TICKET-029**: Error handling and graceful degradation
- **TICKET-030**: User documentation and onboarding

### Epic 8: Advanced Goal Types
- **TICKET-031**: Add revenue target goal type
- **TICKET-032**: Add profit margin goal type
- **TICKET-033**: Add budget compliance goal type
- **TICKET-034**: Add custom formula goal type (advanced)

---

## Configuration & Environment

### New Settings (`financeinsights/settings.py`)

Add to settings file:

```python
# AI Playbook Configuration
AI_PLAYBOOK_ENABLED = os.getenv("AI_PLAYBOOK_ENABLED", "True").lower() == "true"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # Cost-effective, fast
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "1500"))
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

# Playbook evaluation settings
PLAYBOOK_EVALUATION_RETENTION_DAYS = int(os.getenv("PLAYBOOK_EVALUATION_RETENTION_DAYS", "365"))
PLAYBOOK_MAX_CONVERSATIONS_PER_USER = int(os.getenv("PLAYBOOK_MAX_CONVERSATIONS_PER_USER", "50"))

# Feature flags
PLAYBOOK_ENABLE_FORECASTING = os.getenv("PLAYBOOK_ENABLE_FORECASTING", "True").lower() == "true"
PLAYBOOK_ENABLE_CONVERSATIONS = os.getenv("PLAYBOOK_ENABLE_CONVERSATIONS", "True").lower() == "true"
```

### Environment Variables (.env file)

```bash
# Required for AI features
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini  # or gpt-4, gpt-3.5-turbo

# Optional
AI_PLAYBOOK_ENABLED=True
OPENAI_MAX_TOKENS=1500
OPENAI_TEMPERATURE=0.7
PLAYBOOK_EVALUATION_RETENTION_DAYS=365
PLAYBOOK_ENABLE_FORECASTING=True
PLAYBOOK_ENABLE_CONVERSATIONS=True
```

### Safe Handling of Missing Configuration

**AI Service must gracefully degrade:**

```python
# In ai_service.py
import os
from django.conf import settings

def _check_ai_available():
    """Check if AI features are available"""
    if not settings.AI_PLAYBOOK_ENABLED:
        return False
    if not settings.OPENAI_API_KEY:
        logger.warning("OpenAI API key not configured, using fallback templates")
        return False
    return True

def generate_goal_explanation(goal, evaluation_data, historical):
    if not _check_ai_available():
        # Fallback to template-based explanation
        return _template_explanation(goal, evaluation_data)
    
    # AI generation logic...
```

**Template-based fallbacks:**
- Simple text templates with variable substitution
- Basic rule-based recommendations
- Still functional, just less intelligent

### Cost Management

**Strategies to minimize OpenAI API costs:**
1. Use `gpt-4o-mini` (cheapest, still very capable)
2. Cache AI responses for repeated queries
3. Limit max_tokens per request
4. Rate limiting on expensive operations (forecasting)
5. Batch evaluations (nightly) instead of real-time for all goals
6. User-triggered evaluations cost quota (e.g., 10 refreshes per day)
7. Log token usage for monitoring

---

## Notes on Innovation / Positioning

### Why This Feature Is Special

**The AI Financial Playbook transforms Finance Insights MVP from a reporting tool into an intelligent financial advisor.**

**Unique Positioning:**

1. **Goal-First, Not Data-First**
   - Most finance tools show you data and expect you to figure out what to do
   - Playbook starts with what you want to achieve and tells you how to get there

2. **Conversational Intelligence**
   - Natural language throughout (create goals, ask questions, explore scenarios)
   - No learning curve - just talk to it like a financial advisor

3. **Proactive, Not Reactive**
   - Traditional: You check the dashboard when you remember
   - Playbook: It monitors continuously and alerts you to risks/opportunities

4. **Explanatory, Not Just Analytical**
   - Doesn't just show charts - explains WHY things are happening
   - Provides context, trends, and forward-looking insights

5. **Scenario Planning Made Easy**
   - What-if analysis without spreadsheets
   - Ask questions like "What if I cut expenses by 15%?" and get instant, intelligent answers

6. **Real-Time AI Analysis**
   - Not pre-canned insights - fresh analysis every time based on your actual data
   - Personalized to your business context and goals

### Target Positioning Statements

**For Pitch Decks:**
> "Finance Insights Playbook is an AI financial co-pilot that helps small businesses achieve their financial goals through natural language conversations, proactive monitoring, and intelligent scenario planning."

**For User Marketing:**
> "Stop guessing with your finances. Tell Playbook what you want to achieve, and it'll monitor your progress, explain what's happening, and show you exactly how to get there."

**For Investor/Visa Applications:**
> "We're democratizing financial intelligence. What used to require a CFO and expensive consultants is now available to any small business through conversational AI that understands your goals and guides you toward achieving them."

### Competitive Differentiation

**vs. Traditional Accounting Software (QuickBooks, Xero):**
- They show past data → We predict future outcomes
- They require interpretation → We explain in plain English
- They're reactive → We're proactive

**vs. Other AI Finance Tools:**
- They use AI for categorization/automation → We use AI for strategic guidance
- They're feature-focused → We're goal-focused
- They answer "what happened?" → We answer "what should I do?"

### Innovation Highlights

1. **Natural Language Throughout** - No forms, just conversation
2. **Real-Time AI Analysis** - Not pre-generated reports
3. **Integrated What-If Simulations** - Scenario planning in natural language
4. **Proactive Risk Detection** - AI identifies threats before they become problems
5. **Context-Aware Recommendations** - Advice tailored to your specific business situation

This positions Finance Insights MVP as a cutting-edge, AI-first financial intelligence platform - perfect for visa/innovation showcases while being genuinely useful for small businesses.

---

## Success Metrics

Track these metrics to measure feature success:

**Engagement:**
- % of organizations with active goals
- Goals created per organization
- Daily/weekly active users on Playbook page
- Average session time on Playbook

**AI Usage:**
- Natural language goals parsed successfully (vs. failed/needed editing)
- What-if simulations run per user/month
- API calls per day (cost monitoring)
- AI response satisfaction (future: thumbs up/down)

**Business Impact:**
- Goals achieved
- Average time to goal achievement
- User retention (do Playbook users stick around longer?)
- Conversion from free to paid (if applicable)

**Technical:**
- API response times
- Error rates
- Fallback usage (how often AI unavailable?)
- Token costs per evaluation

---

## Future Enhancements (Post-MVP)

**Not in initial scope, but consider for future:**

1. **Automated Goal Suggestions** - AI proposes goals based on transaction patterns
2. **Goal Templates** - Pre-built goals for common scenarios (runway, cash reserves, etc.)
3. **Team Collaboration on Goals** - Comments, shared ownership, approval workflows
4. **Notifications** - Email/Slack alerts when goals at risk or achieved
5. **Multi-Currency Support** - For international businesses
6. **Benchmarking** - Compare your goals vs. similar businesses (anonymized)
7. **Integration with External Data** - Bank feeds, invoice platforms, etc.
8. **Mobile App** - Push notifications for goal status changes
9. **Voice Interface** - "Hey Playbook, what's my runway?"
10. **Advanced ML Models** - Custom-trained models on your data for better forecasting

---

## Getting Started (For Developers)

**Prerequisites:**
- Python 3.10+
- Django 5.2.7 (already installed)
- OpenAI API key (sign up at platform.openai.com)
- Familiarity with existing codebase (`app_core/models.py`, `app_core/metrics.py`)

**Setup Steps:**

1. **Install Dependencies**
   ```bash
   pip install openai  # Add to requirements.txt
   ```

2. **Configure Environment**
   ```bash
   # Add to .env file
   OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
   AI_PLAYBOOK_ENABLED=True
   ```

3. **Create Models**
   ```bash
   # Create app_core/playbook_models.py
   # Add to app_core/models.py: from .playbook_models import *
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Start with Backend**
   - Implement evaluation engine first (no AI dependency)
   - Add AI layer once core logic works
   - Test with sample goals via Django admin

5. **Build UI Incrementally**
   - Start with simple goal list page
   - Add create flow
   - Add detail page with charts
   - Add conversational features last

**Development Workflow:**
1. Backend first, UI second
2. Rule-based fallbacks before AI enhancement
3. Test with real transaction data from existing users
4. Monitor token usage closely during development

---

## Questions & Decisions Log

**Decisions Made:**
- Natural language input with confirmation (not blind trust)
- OpenAI as primary LLM provider
- Organization-level goals (shared across team)
- Real-time evaluation available (not just scheduled)
- Conversational what-if simulator
- Enhanced insights on "Playbook" page (cool name!)
- Deep AI analysis: WHY + recommendations + trends + risks + forecasting

**Open Questions:**
- Should we support custom goal formulas? (e.g., "Revenue > Expenses * 1.2")
- Do we need approval workflows for goal creation in large organizations?
- Should AI explanations be editable by users?
- How do we handle goals that span multiple organizations? (cross-org consolidation)
- Should we expose Playbook API for external integrations?

---

## Contact & Support

**For Implementation Questions:**
- Review existing code patterns in `app_core/metrics.py`, `app_core/insights.py`, `app_core/projects.py`
- Follow Django best practices for models, views, templates
- Reuse existing UI components and CSS from `app_web/static/`

**For AI/LLM Questions:**
- OpenAI documentation: https://platform.openai.com/docs
- Model selection: Use gpt-4o-mini for development, can upgrade to gpt-4 for production
- Prompt engineering: Be specific, provide context, use examples

**For Business/Product Questions:**
- This feature positions Finance Insights as an AI-first financial intelligence platform
- Focus on user value: proactive guidance, not just data visualization
- Competitive advantage: conversational interface + goal-based approach

---

**Last Updated:** December 3, 2025  
**Status:** Design Complete - Ready for Implementation  
**Next Step:** TICKET-001 - Create Playbook Models

