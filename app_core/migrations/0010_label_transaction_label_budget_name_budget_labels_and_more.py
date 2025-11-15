# Generated manually for label system

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('app_core', '0009_alter_budget_unique_together_budget_end_date_and_more'),
    ]

    operations = [
        # Create Label model
        migrations.CreateModel(
            name='Label',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text="Label name (e.g., 'Office Supplies', 'Client A')", max_length=64)),
                ('color', models.CharField(default='#2563eb', help_text='Hex color code for UI display', max_length=7)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='labels', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        # Add unique constraint for Label
        migrations.AlterUniqueTogether(
            name='label',
            unique_together={('user', 'name')},
        ),
        # Add indexes for Label
        migrations.AddIndex(
            model_name='label',
            index=models.Index(fields=['user', 'name'], name='app_core_la_user_id_d8c442_idx'),
        ),
        # Add label FK to Transaction
        migrations.AddField(
            model_name='transaction',
            name='label',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transactions', to='app_core.label'),
        ),
        # Add index for transaction label
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['user', 'label'], name='app_core_tr_user_lb_idx'),
        ),
        # Add name field to Budget (with default for existing rows)
        migrations.AddField(
            model_name='budget',
            name='name',
            field=models.CharField(default='Unnamed Budget', help_text="Budget name (e.g., 'Q4 Marketing', 'Office Renovation')", max_length=128),
            preserve_default=True,
        ),
        # Create many-to-many for Budget labels
        migrations.AddField(
            model_name='budget',
            name='labels',
            field=models.ManyToManyField(blank=True, help_text='Labels to track in this budget', related_name='budgets', to='app_core.label'),
        ),
        # Alter Budget ordering
        migrations.AlterModelOptions(
            name='budget',
            options={'ordering': ['name']},
        ),
    ]

