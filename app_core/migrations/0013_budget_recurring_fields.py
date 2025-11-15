# Generated manually for recurring budgets

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_core', '0012_add_recurring_transactions'),
    ]

    operations = [
        migrations.AddField(
            model_name='budget',
            name='is_recurring',
            field=models.BooleanField(default=False, help_text='Whether this budget recurs automatically'),
        ),
        migrations.AddField(
            model_name='budget',
            name='recurrence_count',
            field=models.PositiveIntegerField(blank=True, help_text='Number of times to recur (e.g., 3 = create budget for next 3 periods)', null=True),
        ),
        migrations.AddField(
            model_name='budget',
            name='last_generated_period',
            field=models.DateField(blank=True, help_text='Last period start date that was generated', null=True),
        ),
    ]

