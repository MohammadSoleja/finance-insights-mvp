#!/usr/bin/env python
"""
Script to update all remaining templates with currency tags.
Replaces hardcoded £ symbols with {% currency_symbol %} template tag.
"""

import os
import re

# Base directory
BASE_DIR = '/Users/mohammadsoleja/Documents/GitHub/finance-insights-mvp/app_web/templates/app_web'

# Files to update
TEMPLATES_TO_UPDATE = [
    'budgets.html',
    'projects.html',
    'project_detail.html',
    'invoices.html',
    'invoice_detail.html',
    'reports.html',
    'report_pnl.html',
    'clients.html',
]

def update_template(filepath):
    """Update a template file with currency tags"""
    print(f"\nUpdating: {filepath}")

    if not os.path.exists(filepath):
        print(f"  ❌ File not found")
        return False

    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content
    changes = 0

    # 1. Add currency_tags to {% load %} statement if not present
    if '{% load currency_tags %}' not in content:
        if '{% load static %}' in content:
            content = content.replace(
                '{% load static %}',
                '{% load static currency_tags %}'
            )
            changes += 1
            print(f"  ✓ Added currency_tags to load statement")
        elif '{% load humanize %}' in content:
            content = content.replace(
                '{% load humanize %}',
                '{% load humanize currency_tags %}'
            )
            changes += 1
            print(f"  ✓ Added currency_tags to load statement")

    # 2. Replace hardcoded £ symbols with {% currency_symbol %}
    # Pattern: £{{ ... }}
    pattern1 = r'£\{\{([^}]+)\}\}'
    matches = re.findall(pattern1, content)
    if matches:
        content = re.sub(pattern1, r'{% currency_symbol %}{{\ 1}}', content)
        changes += len(matches)
        print(f"  ✓ Replaced {len(matches)} £{{{{ ... }}}} patterns")

    # Pattern: <td>£123</td> or similar
    pattern2 = r'([>"])\s*£\s*([0-9{])'
    matches2 = re.findall(pattern2, content)
    if matches2:
        content = re.sub(pattern2, r'\1{% currency_symbol %}\2', content)
        changes += len(matches2)
        print(f"  ✓ Replaced {len(matches2)} hardcoded £ symbols")

    if changes > 0:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  ✅ Saved {changes} changes")
        return True
    else:
        print(f"  ⚠️  No changes needed")
        return False

def main():
    print("=" * 60)
    print("Currency Template Updater")
    print("=" * 60)

    total_updated = 0

    for template_name in TEMPLATES_TO_UPDATE:
        filepath = os.path.join(BASE_DIR, template_name)
        if update_template(filepath):
            total_updated += 1

    print("\n" + "=" * 60)
    print(f"Updated {total_updated}/{len(TEMPLATES_TO_UPDATE)} templates")
    print("=" * 60)

if __name__ == '__main__':
    main()

