"""
Dashboard Widget Models
Stores user's custom dashboard layout and widget configurations
"""
from django.db import models
from django.contrib.auth.models import User
from app_core.team_models import Organization


class DashboardLayout(models.Model):
    """
    Stores a user's custom dashboard layout
    One layout per user per organization
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboard_layouts')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='dashboard_layouts')

    layout_config = models.JSONField(default=dict, help_text="""
        JSON structure:
        {
            'widgets': [
                {
                    'id': 'kpi-total-income',
                    'x': 0, 'y': 0, 'w': 3, 'h': 1,
                    'settings': {
                        'dateRange': 'last30days',
                        'showSparkline': True
                    }
                }
            ],
            'density': 'comfortable',
            'autoRefresh': 30
        }
    """)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'organization']
        ordering = ['-updated_at']

    def __str__(self):
        return f"Dashboard Layout for {self.user.username} in {self.organization.name}"

    @classmethod
    def get_default_layout(cls):
        """Returns the default dashboard layout configuration"""
        return {
            'widgets': [
                # Row 1: KPIs (6 widgets at 2 columns each = 12 columns)
                {'id': 'kpi-total-income', 'x': 0, 'y': 0, 'w': 2, 'h': 1},
                {'id': 'kpi-total-expenses', 'x': 2, 'y': 0, 'w': 2, 'h': 1},
                {'id': 'kpi-net-cash-flow', 'x': 4, 'y': 0, 'w': 2, 'h': 1},
                {'id': 'kpi-budget-progress', 'x': 6, 'y': 0, 'w': 2, 'h': 1},
                {'id': 'kpi-burn-rate', 'x': 8, 'y': 0, 'w': 2, 'h': 1},
                {'id': 'kpi-active-projects', 'x': 10, 'y': 0, 'w': 2, 'h': 1},

                # Row 2: Main Charts (6+6 = 12 columns)
                {'id': 'chart-revenue-expense', 'x': 0, 'y': 1, 'w': 6, 'h': 3},
                {'id': 'chart-trend-line', 'x': 6, 'y': 1, 'w': 6, 'h': 3},

                # Row 3: Secondary Charts and Lists (4+4+4 = 12 columns)
                {'id': 'chart-expense-pie', 'x': 0, 'y': 4, 'w': 4, 'h': 3},
                {'id': 'chart-budget-performance', 'x': 4, 'y': 4, 'w': 4, 'h': 3},
                {'id': 'list-recent-transactions', 'x': 8, 'y': 4, 'w': 4, 'h': 3}
            ],
            'density': 'comfortable',
            'autoRefresh': 30
        }

    def get_or_create_default(user, organization):
        """Get existing layout or create default one"""
        layout, created = DashboardLayout.objects.get_or_create(
            user=user,
            organization=organization,
            defaults={'layout_config': DashboardLayout.get_default_layout()}
        )
        return layout

