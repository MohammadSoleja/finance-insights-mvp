#!/bin/bash
# Script to organize markdown documentation files

cd /Users/mohammadsoleja/Documents/GitHub/finance-insights-mvp

# Create directories
mkdir -p docs/playbook
mkdir -p docs/ai-integration
mkdir -p docs/troubleshooting
mkdir -p docs/security

echo "Created directories"

# Move Playbook files
for file in DASHBOARD_WIDGETS_IMPLEMENTATION.md FINAL_PLAYBOOK_FIXES.md GOAL_TRACKING_IMPROVEMENTS.md PLAYBOOK_CARD_REDESIGN.md PLAYBOOK_FALLBACK_MODE.md PLAYBOOK_IMPLEMENTATION_STATUS.md PLAYBOOK_UI_IMPROVEMENTS.md PLAYBOOK_WIDGETS_FRONTEND_FIX.md PLAYBOOK_WIDGETS_SCROLLABLE_UPDATE.md PLAYBOOK_WIDGETS_TROUBLESHOOTING.md IMPLEMENTATION_VERIFICATION_COMPLETE.md; do
  if [ -f "$file" ]; then
    mv "$file" docs/playbook/
    echo "Moved $file"
  fi
done

echo "Playbook files moved"

# Move AI Integration files
for file in AI_COMPLETE_DATA_ACCESS.md AI_INSIGHTS_MADE_CONCISE.md AI_RESPONSE_QUALITY_FIXED.md AI_SERVICE_ERRORS_FIXED.md ALL_AI_FUNCTIONS_UPDATED.md CHAT_AI_DATE_FIXES.md CHAT_DATA_ACCESS_FIXED.md CHAT_FIXES_COMPLETE.md CLEAR_CHAT_FEATURE.md CONFIDENCE_DISPLAY_FIXED.md FREE_AI_OPTIONS.md GEMINI_FINAL_STATUS.md GEMINI_INTEGRATION_COMPLETE.md GEMINI_MODEL_FIXED.md GEMINI_MODEL_TROUBLESHOOTING.md GEMINI_PROMPT_SAFETY_FIX.md GEMINI_SAFETY_JSON_FIXED.md GROQ_SETUP_GUIDE.md HONEST_AI_OPTIONS.md HUGGINGFACE_API_FIX.md HUGGINGFACE_ENDPOINT_FIX.md HUGGINGFACE_FINAL_FIX.md HUGGINGFACE_INTEGRATION_COMPLETE.md HUGGINGFACE_REAL_FIX.md OPENAI_FINAL_CHOICE.md OPENAI_FIXED_FINAL.md OPENAI_QUOTA_ISSUE.md OPENAI_READY_TO_TEST.md OPENAI_STATUS.md REAL_SOLUTION_USE_OPENAI.md SIMULATION_NARRATIVE_AI_FIXED.md SIMULATION_PARSING_FIXED.md SWITCH_TO_GEMINI.md WORKING_MODEL_UPDATE.md; do
  if [ -f "$file" ]; then
    mv "$file" docs/ai-integration/
    echo "Moved $file"
  fi
done

echo "AI files moved"

# Move Troubleshooting files
for file in ALL_MODEL_ERRORS_FIXED.md CACHE_ISSUE_FIXED.md CLEAR_CACHE_NOW.md COMPLETE_FIX_VERIFICATION.md DEBUG_PRINT_STATEMENTS_ADDED.md ERRORS_FIXED.md FIX_GEMINI_404_NOW.md FIX_IS_BROWSER_CACHE.md JSON_IMPORT_FIXED.md MODEL_FIELD_ERROR_FIXED.md QUICK_FIX_SUMMARY.md RESTART_SERVER_FIX.md ROOT_CAUSE_FIXED_DIRECTION_FIELD.md START_DATE_MIGRATION_FIXED.md SYNTAX_ERROR_FIXED.md SYNTAX_ERROR_FIXED_FINAL.md URGENT_RESTART_SERVER.md; do
  if [ -f "$file" ]; then
    mv "$file" docs/troubleshooting/
    echo "Moved $file"
  fi
done

echo "Troubleshooting files moved"

# Move Security files
for file in API_KEYS_SECURITY_FIX.md KEYS_NOT_EXPOSED_KEEP_THEM.md; do
  if [ -f "$file" ]; then
    mv "$file" docs/security/
    echo "Moved $file"
  fi
done

echo "Security files moved"
echo "Done!"

