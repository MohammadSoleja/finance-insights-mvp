# management/commands/send_weekly_briefings.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from app_core.models import Organization
from app_core.weekly_briefing import generate_weekly_briefing


class Command(BaseCommand):
    help = 'Send weekly financial briefings to all active organizations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--org-id',
            type=int,
            help='Send to specific organization only',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Generate briefings but don\'t send emails',
        )

    def handle(self, *args, **options):
        self.stdout.write('Generating weekly financial briefings...')

        # Get organizations
        if options['org_id']:
            orgs = Organization.objects.filter(id=options['org_id'], active=True)
        else:
            orgs = Organization.objects.filter(active=True)

        sent_count = 0
        error_count = 0

        for org in orgs:
            try:
                self.stdout.write(f'Processing {org.name}...')

                # Generate briefing
                briefing_data = generate_weekly_briefing(org)

                # Get all users in organization
                users = org.get_all_members()

                if not users:
                    self.stdout.write(self.style.WARNING(f'  No users found for {org.name}'))
                    continue

                for user in users:
                    if options['dry_run']:
                        self.stdout.write(f'  [DRY RUN] Would send to {user.email}')
                    else:
                        # Send email
                        success = self._send_briefing_email(user, org, briefing_data)
                        if success:
                            sent_count += 1
                            self.stdout.write(self.style.SUCCESS(f'  ✓ Sent to {user.email}'))
                        else:
                            error_count += 1
                            self.stdout.write(self.style.ERROR(f'  ✗ Failed to send to {user.email}'))

            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'  Error processing {org.name}: {str(e)}'))

        # Summary
        self.stdout.write('\n' + '='*50)
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(f'DRY RUN: Would have sent {sent_count} briefings'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ Sent {sent_count} briefings'))
            if error_count > 0:
                self.stdout.write(self.style.WARNING(f'✗ {error_count} errors'))

    def _send_briefing_email(self, user, organization, briefing_data):
        """Send briefing email to user"""
        try:
            # Prepare context for template
            context = {
                'user': user,
                'organization': organization,
                'briefing': briefing_data,
                'dashboard_url': 'https://financeinsights.com/dashboard',  # Update with actual URL
            }

            # Render HTML email
            html_content = render_to_string('emails/weekly_briefing.html', context)

            # Render plain text version
            text_content = self._generate_text_briefing(briefing_data)

            # Send email
            send_mail(
                subject=f"Your Financial Briefing - Week of {briefing_data['week_of']}",
                message=text_content,
                html_message=html_content,
                from_email='insights@financeinsights.com',
                recipient_list=[user.email],
                fail_silently=False,
            )

            return True

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error sending email: {str(e)}'))
            return False

    def _generate_text_briefing(self, briefing_data):
        """Generate plain text version of briefing"""
        text = f"""
Your Financial Briefing - Week of {briefing_data['week_of']}

KEY METRICS
===========
Runway: {briefing_data['key_metrics']['runway']['current']} months ({briefing_data['key_metrics']['runway']['change_label']} from last week)
Revenue: £{briefing_data['key_metrics']['revenue']['current']:,.0f} ({briefing_data['key_metrics']['revenue']['change_label']} from last week)
Expenses: £{briefing_data['key_metrics']['expenses']['current']:,.0f} ({briefing_data['key_metrics']['expenses']['change_label']} from last week)
Health Score: {briefing_data['health_score']['current']}/100 ({briefing_data['health_score']['level']})

"""

        if briefing_data['concerns']:
            text += "ATTENTION NEEDED\n"
            text += "================\n"
            for concern in briefing_data['concerns']:
                text += f"• {concern}\n"
            text += "\n"

        if briefing_data['good_news']:
            text += "GOOD NEWS\n"
            text += "=========\n"
            for news in briefing_data['good_news']:
                text += f"• {news}\n"
            text += "\n"

        if briefing_data['action_items']:
            text += "TOP ACTIONS THIS WEEK\n"
            text += "=====================\n"
            for i, action in enumerate(briefing_data['action_items'], 1):
                text += f"{i}. {action}\n"
            text += "\n"

        if briefing_data['upcoming_dates']:
            text += "UPCOMING CRITICAL DATES\n"
            text += "=======================\n"
            for date_item in briefing_data['upcoming_dates']:
                text += f"• {date_item['description']} - {date_item['days_away']} days away\n"
            text += "\n"

        text += "\nView full dashboard: https://financeinsights.com/dashboard\n"
        text += "\nNext briefing: Next Monday\n"

        return text

