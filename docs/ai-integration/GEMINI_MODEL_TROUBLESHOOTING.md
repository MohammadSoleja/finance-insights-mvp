# Gemini Model Name Troubleshooting

## The Problem

Getting 404 errors for Gemini models means the model name format is incorrect for your API version.

## Current Fix Applied

Changed model to: `gemini-1.5-flash-latest`

**File:** `financeinsights/settings.py`
```python
GEMINI_MODEL = "gemini-1.5-flash-latest"
```

---

## If Still Getting 404 Errors

Try these model names **one at a time**:

### Option 1: gemini-1.5-flash-latest (CURRENT)
```python
GEMINI_MODEL = "gemini-1.5-flash-latest"
```

### Option 2: gemini-1.5-flash
```python
GEMINI_MODEL = "gemini-1.5-flash"
```

### Option 3: gemini-1.5-pro-latest
```python
GEMINI_MODEL = "gemini-1.5-pro-latest"
```

### Option 4: gemini-1.0-pro-latest
```python
GEMINI_MODEL = "gemini-1.0-pro-latest"
```

### Option 5: gemini-1.0-pro
```python
GEMINI_MODEL = "gemini-1.0-pro"
```

---

## How to Test

After changing the model name:

1. **Restart Django server**
2. **Create a goal** or **refresh a goal**
3. **Check terminal output:**

**If it works:**
```
✓ Gemini API call used 234 tokens
```

**If it doesn't:**
```
✗ GEMINI API error: 404 models/XXX is not found
```

Try the next option!

---

## Manual API Test

Run this in terminal to find which model works:

```bash
python3 << 'EOF'
import google.generativeai as genai

genai.configure(api_key=)

models = [
    'gemini-1.5-flash-latest',
    'gemini-1.5-flash',
    'gemini-1.5-pro-latest',
    'gemini-1.0-pro-latest',
    'gemini-1.0-pro',
]

for model_name in models:
    try:
        print(f'Testing: {model_name}...')
        model = genai.GenerativeModel(model_name)
        response = model.generate_content('Hi')
        print(f'  ✓ SUCCESS! Use this: {model_name}\n')
        break
    except Exception as e:
        print(f'  ✗ Failed: {str(e)[:60]}\n')
EOF
```

Whatever model succeeds, use that in `settings.py`!

---

## Alternative: List Available Models

```bash
python3 << 'EOF'
import google.generativeai as genai

genai.configure(api_key='AIzaSyBMQ_fhhDiP7h4ZMgn-SawUKju2TX6wXi4')

print("Available models:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f'  ✓ {m.name}')
EOF
```

This shows all models your API key can access.

---

## Quick Fix Checklist

1. [ ] Try `gemini-1.5-flash-latest` (currently set)
2. [ ] Restart Django server
3. [ ] Test by creating/refreshing a goal
4. [ ] If 404 error, try next model name
5. [ ] Repeat until it works

---

## Most Likely to Work

Based on Gemini API documentation:

1. **`gemini-1.5-flash-latest`** ← Currently set
2. **`gemini-1.0-pro-latest`** ← Fallback
3. **`gemini-1.0-pro`** ← Old stable

---

**After you find the working model name, update this file with the solution!**

