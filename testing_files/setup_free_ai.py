#!/usr/bin/env python3
"""
Setup Hugging Face integration for FREE AI-powered Playbook.
"""

print("""
╔══════════════════════════════════════════════════════════════╗
║   FREE AI SETUP - HUGGING FACE INTEGRATION                   ║
╚══════════════════════════════════════════════════════════════╝

You don't need to pay for AI! Let's set up Hugging Face (100% FREE).

STEP 1: GET YOUR FREE API TOKEN
────────────────────────────────────────────────────────────────
1. Sign up (if you haven't): https://huggingface.co/join
2. Get your token: https://huggingface.co/settings/tokens
   - Click "New token"
   - Name: "Finance Insights Playbook"
   - Type: Read
   - Click "Generate"
   - Copy the token (starts with "hf_")

STEP 2: PASTE YOUR TOKEN BELOW
────────────────────────────────────────────────────────────────
""")

token = input("Enter your Hugging Face token (hf_xxxxx): ").strip()

if not token.startswith("hf_"):
    print("\n❌ ERROR: Token should start with 'hf_'")
    print("Go to https://huggingface.co/settings/tokens and get your token")
    exit(1)

print("\n✓ Token looks valid!")
print("\nNow I'll update your settings...")

# Read settings
with open('/financeinsights/settings.py', 'r') as f:
    settings = f.read()

# Check if already has Hugging Face config
if 'HUGGINGFACE_API_KEY' in settings:
    print("✓ Hugging Face already configured, updating token...")
    # Update existing token
    import re
    settings = re.sub(
        r'HUGGINGFACE_API_KEY = .*',
        f'HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "{token}")',
        settings
    )
else:
    print("✓ Adding Hugging Face configuration...")
    # Add new config after Gemini config
    gemini_config_end = settings.find('GEMINI_MODEL = ')
    if gemini_config_end > 0:
        # Find end of that line
        line_end = settings.find('\n', gemini_config_end)
        insert_point = line_end + 1

        new_config = f'''
# Hugging Face API Configuration (FREE forever!)
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "{token}")
HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")  # Free tier
'''
        settings = settings[:insert_point] + new_config + settings[insert_point:]

# Update AI provider to huggingface
settings = settings.replace(
    'AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")',
    'AI_PROVIDER = os.getenv("AI_PROVIDER", "huggingface")'
)

# Write back
with open('/financeinsights/settings.py', 'w') as f:
    f.write(settings)

print("\n✅ SETTINGS UPDATED!")
print("\nNEXT STEPS:")
print("───────────────────────────────────────────────────────────────")
print("1. Install Hugging Face library:")
print("   pip install huggingface-hub")
print("")
print("2. I'll update the AI service code to support Hugging Face")
print("")
print("3. Restart your Django server:")
print("   python manage.py runserver")
print("")
print("4. Test it by creating/refreshing a goal!")
print("───────────────────────────────────────────────────────────────")
print("\n🎉 FREE AI-POWERED PLAYBOOK READY!")
print("   - No payment required")
print("   - 1,000+ requests/day")
print("   - Quality AI insights")
print("\n")

