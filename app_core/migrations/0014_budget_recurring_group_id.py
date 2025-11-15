# Generated manually for recurring group ID

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_core', '0013_budget_recurring_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='budget',
            name='recurring_group_id',
            field=models.CharField(blank=True, help_text='UUID linking related recurring budgets together', max_length=64, null=True),
        ),
    ]

