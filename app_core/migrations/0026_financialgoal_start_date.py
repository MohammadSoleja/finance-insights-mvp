# Generated manually for start_date field addition

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_core', '0025_transaction_original_currency'),
    ]

    operations = [
        migrations.AddField(
            model_name='financialgoal',
            name='start_date',
            field=models.DateField(blank=True, help_text='Date when goal tracking should start (defaults to creation date)', null=True),
        ),
    ]

