#!/usr/bin/env python3
"""
Find the correct Gemini model name for your API key.
Run this script and it will tell you which model to use.
"""

import google.generativeai as genai

# Your API key
API_KEY = "AIzaSyBMQ_fhhDiP7h4ZMgn-SawUKju2TX6wXi4"

genai.configure(api_key=API_KEY)

print("=" * 70)
print("FINDING CORRECT GEMINI MODEL")
print("=" * 70)

# List of possible model names to try
models_to_try = [
    'gemini-1.5-flash-latest',
    'gemini-1.5-flash',
    'gemini-1.5-pro-latest',
    'gemini-1.5-pro',
    'gemini-1.0-pro-latest',
    'gemini-1.0-pro',
    'gemini-pro',
]

print("\nTesting models...\n")

working_model = None

for model_name in models_to_try:
    try:
        print(f"Testing: {model_name:<30}", end=" ")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content('Say hi in 3 words')
        print(f"✓ WORKS!")
        print(f"  Response: {response.text[:50]}")
        working_model = model_name
        break
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            print("✗ Not found")
        else:
            print(f"✗ Error: {error_msg[:40]}")

print("\n" + "=" * 70)

if working_model:
    print("SUCCESS!")
    print("=" * 70)
    print(f"\n✓ Use this model: {working_model}\n")
    print("Update your settings.py:")
    print(f'  GEMINI_MODEL = "{working_model}"')
    print("\nThen restart your Django server!")
else:
    print("NO MODELS WORKED")
    print("=" * 70)
    print("\nTrying to list all available models...")
    try:
        available = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available.append(m.name)

        if available:
            print(f"\nFound {len(available)} available models:")
            for name in available:
                print(f"  - {name}")
            print(f"\nTry using: {available[0]}")
        else:
            print("\nNo models found. Check your API key!")
    except Exception as e:
        print(f"\nError listing models: {e}")
        print("\nPossible issues:")
        print("  1. API key is invalid")
        print("  2. API key doesn't have Gemini access")
        print("  3. Network/firewall issue")

print("\n" + "=" * 70)

