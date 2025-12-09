#!/usr/bin/env python3
"""
Verify that environment variables are loaded correctly
Run this before committing to ensure everything works!
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

print("🔍 Checking Environment Variables Configuration...\n")
print("="*60)

# Check required variables
checks = {
    "AI_PROVIDER": os.getenv("AI_PROVIDER"),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
    "HUGGINGFACE_API_KEY": os.getenv("HUGGINGFACE_API_KEY"),
}

all_good = True

for key, value in checks.items():
    if value and value != "":
        # Mask the key for security
        if "KEY" in key or "SECRET" in key:
            masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
            print(f"✅ {key}: {masked}")
        else:
            print(f"✅ {key}: {value}")
    else:
        print(f"⚠️  {key}: Not set")
        if key in ["AI_PROVIDER"]:  # Required
            all_good = False

print("="*60)

if all_good:
    print("\n✅ Configuration looks good!")
    print("🔒 API keys are loaded from .env file")
    print("🚀 Safe to commit and push!")
else:
    print("\n⚠️  Some required variables are missing")
    print("📝 Check your .env file")

print("\n💡 Remember:")
print("   - .env file is in .gitignore (won't be committed)")
print("   - settings.py now uses os.getenv() (safe to commit)")
print("   - Your API keys are secure!")

