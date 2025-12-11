#!/usr/bin/env python3
"""
Script to organize markdown documentation files into proper directories.
"""
import os
import shutil
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / 'docs'

# Create subdirectories
subdirs = {
    'playbook': DOCS_DIR / 'playbook',
    'ai-integration': DOCS_DIR / 'ai-integration',
    'troubleshooting': DOCS_DIR / 'troubleshooting',
    'security': DOCS_DIR / 'security',
}

# Create directories
for dir_path in subdirs.values():
    dir_path.mkdir(parents=True, exist_ok=True)
    print(f"✓ Created: {dir_path.relative_to(BASE_DIR)}")

# File mappings (source filename -> destination category)
file_mappings = {
    # Playbook files
    'DASHBOARD_WIDGETS_IMPLEMENTATION.md': 'playbook',
    'FINAL_PLAYBOOK_FIXES.md': 'playbook',
    'GOAL_TRACKING_IMPROVEMENTS.md': 'playbook',
    'PLAYBOOK_CARD_REDESIGN.md': 'playbook',
    'PLAYBOOK_FALLBACK_MODE.md': 'playbook',
    'PLAYBOOK_IMPLEMENTATION_STATUS.md': 'playbook',
    'PLAYBOOK_UI_IMPROVEMENTS.md': 'playbook',
    'PLAYBOOK_WIDGETS_FRONTEND_FIX.md': 'playbook',
    'PLAYBOOK_WIDGETS_SCROLLABLE_UPDATE.md': 'playbook',
    'PLAYBOOK_WIDGETS_TROUBLESHOOTING.md': 'playbook',
    'IMPLEMENTATION_VERIFICATION_COMPLETE.md': 'playbook',

    # AI Integration files
    'AI_COMPLETE_DATA_ACCESS.md': 'ai-integration',
    'AI_INSIGHTS_MADE_CONCISE.md': 'ai-integration',
    'AI_RESPONSE_QUALITY_FIXED.md': 'ai-integration',
    'AI_SERVICE_ERRORS_FIXED.md': 'ai-integration',
    'ALL_AI_FUNCTIONS_UPDATED.md': 'ai-integration',
    'CHAT_AI_DATE_FIXES.md': 'ai-integration',
    'CHAT_DATA_ACCESS_FIXED.md': 'ai-integration',
    'CHAT_FIXES_COMPLETE.md': 'ai-integration',
    'CLEAR_CHAT_FEATURE.md': 'ai-integration',
    'CONFIDENCE_DISPLAY_FIXED.md': 'ai-integration',
    'FREE_AI_OPTIONS.md': 'ai-integration',
    'GEMINI_FINAL_STATUS.md': 'ai-integration',
    'GEMINI_INTEGRATION_COMPLETE.md': 'ai-integration',
    'GEMINI_MODEL_FIXED.md': 'ai-integration',
    'GEMINI_MODEL_TROUBLESHOOTING.md': 'ai-integration',
    'GEMINI_PROMPT_SAFETY_FIX.md': 'ai-integration',
    'GEMINI_SAFETY_JSON_FIXED.md': 'ai-integration',
    'GROQ_SETUP_GUIDE.md': 'ai-integration',
    'HONEST_AI_OPTIONS.md': 'ai-integration',
    'HUGGINGFACE_API_FIX.md': 'ai-integration',
    'HUGGINGFACE_ENDPOINT_FIX.md': 'ai-integration',
    'HUGGINGFACE_FINAL_FIX.md': 'ai-integration',
    'HUGGINGFACE_INTEGRATION_COMPLETE.md': 'ai-integration',
    'HUGGINGFACE_REAL_FIX.md': 'ai-integration',
    'OPENAI_FINAL_CHOICE.md': 'ai-integration',
    'OPENAI_FIXED_FINAL.md': 'ai-integration',
    'OPENAI_QUOTA_ISSUE.md': 'ai-integration',
    'OPENAI_READY_TO_TEST.md': 'ai-integration',
    'OPENAI_STATUS.md': 'ai-integration',
    'REAL_SOLUTION_USE_OPENAI.md': 'ai-integration',
    'SIMULATION_NARRATIVE_AI_FIXED.md': 'ai-integration',
    'SIMULATION_PARSING_FIXED.md': 'ai-integration',
    'SWITCH_TO_GEMINI.md': 'ai-integration',
    'WORKING_MODEL_UPDATE.md': 'ai-integration',

    # Troubleshooting files
    'ALL_MODEL_ERRORS_FIXED.md': 'troubleshooting',
    'CACHE_ISSUE_FIXED.md': 'troubleshooting',
    'CLEAR_CACHE_NOW.md': 'troubleshooting',
    'COMPLETE_FIX_VERIFICATION.md': 'troubleshooting',
    'DEBUG_PRINT_STATEMENTS_ADDED.md': 'troubleshooting',
    'ERRORS_FIXED.md': 'troubleshooting',
    'FIX_GEMINI_404_NOW.md': 'troubleshooting',
    'FIX_IS_BROWSER_CACHE.md': 'troubleshooting',
    'JSON_IMPORT_FIXED.md': 'troubleshooting',
    'MODEL_FIELD_ERROR_FIXED.md': 'troubleshooting',
    'QUICK_FIX_SUMMARY.md': 'troubleshooting',
    'RESTART_SERVER_FIX.md': 'troubleshooting',
    'ROOT_CAUSE_FIXED_DIRECTION_FIELD.md': 'troubleshooting',
    'START_DATE_MIGRATION_FIXED.md': 'troubleshooting',
    'SYNTAX_ERROR_FIXED.md': 'troubleshooting',
    'SYNTAX_ERROR_FIXED_FINAL.md': 'troubleshooting',
    'URGENT_RESTART_SERVER.md': 'troubleshooting',

    # Security files
    'API_KEYS_SECURITY_FIX.md': 'security',
    'KEYS_NOT_EXPOSED_KEEP_THEM.md': 'security',
}

# Move files
moved_count = 0
skipped_count = 0

for filename, category in file_mappings.items():
    source = BASE_DIR / filename
    destination = subdirs[category] / filename

    if source.exists():
        try:
            shutil.move(str(source), str(destination))
            print(f"✓ Moved: {filename} -> docs/{category}/")
            moved_count += 1
        except Exception as e:
            print(f"✗ Error moving {filename}: {e}")
    else:
        print(f"⊘ Skipped: {filename} (not found)")
        skipped_count += 1

print(f"\n{'='*60}")
print(f"Summary:")
print(f"  Directories created: {len(subdirs)}")
print(f"  Files moved: {moved_count}")
print(f"  Files skipped: {skipped_count}")
print(f"{'='*60}")
print("\n✓ Documentation organization complete!")

