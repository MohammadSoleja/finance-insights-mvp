# 🔧 GEMINI MODEL 404 FIX - ACTION REQUIRED

## Current Situation

You're getting: `404 models/gemini-pro is not found`

This means we need to find the correct model name for your Gemini API key.

---

## ✅ SOLUTION: Run This Command

Copy and paste this into your terminal:

```bash
python3 << 'EOF'
import google.generativeai as genai
genai.configure(api_key='')

models = ['gemini-1.5-flash-latest', 'gemini-1.5-flash', 'gemini-1.0-pro-latest', 'gemini-1.0-pro', 'gemini-pro']

for m in models:
    try:
        print(f'Testing: {m}...')
        model = genai.GenerativeModel(m)
        r = model.generate_content('Hi')
        print(f'✓ SUCCESS! Use: {m}\n')
        print(f'Update settings.py to: GEMINI_MODEL = "{m}"')
        break
    except:
        print(f'✗ Failed\n')
EOF
```

---

## Then Do This

1. **Note which model worked** (the one that says "✓ SUCCESS!")
2. **Update `financeinsights/settings.py` line 177:**
   ```python
   GEMINI_MODEL = "the-model-that-worked"
   ```
3. **Restart Django server**
4. **Test by creating a goal**

---

## If Nothing Works

Your Gemini API key might not have access yet. Try this:

### Alternative 1: Get a Fresh API Key
1. Go to: https://aistudio.google.com/app/apikey
2. Delete old key
3. Create new API key
4. Update in settings.py
5. Try again

### Alternative 2: Use Fallback Mode (No AI)
Edit `settings.py`:
```python
AI_PLAYBOOK_ENABLED = False  # Disable AI temporarily
```

The Playbook will still work with basic template responses.

---

## Quick Test

After updating the model name, test with:
```bash
python3 -c "
import google.generativeai as genai
genai.configure(api_key='AIzaSyBMQ_fhhDiP7h4ZMgn-SawUKju2TX6wXi4')
model = genai.GenerativeModel('PUT-MODEL-NAME-HERE')
print(model.generate_content('Hi').text)
"
```

If you see a response → It works!  
If you see 404 → Try different model name

---

## I've Already Set

Currently in `settings.py`:
```python
GEMINI_MODEL = "gemini-1.5-flash-latest"
```

**Try restarting your server first!** This might already work.

If you still get 404, run the test command above to find the right model.

---

**Status:** Waiting for you to test and confirm which model works

