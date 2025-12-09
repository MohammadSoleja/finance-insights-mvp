# Switch to Google Gemini (FREE Alternative to OpenAI)

## Why Google Gemini?

✅ **100% FREE** - No credit card required  
✅ **Generous limits** - 60 requests/minute (vs OpenAI's 3 RPM on free tier)  
✅ **No phone verification** required  
✅ **Same quality** - Gemini 1.5 Flash is comparable to GPT-4o-mini  
✅ **Easy setup** - Get API key in 2 minutes  

---

## Step 1: Get Your Free Gemini API Key

1. Go to: https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click **"Create API key"**
4. Copy the key (starts with `AIza...`)

**That's it!** No credit card, no phone verification.

---

## Step 2: Install Google Gemini Library

```bash
cd /Users/mohammadsoleja/Documents/GitHub/finance-insights-mvp
pip install google-generativeai
```

---

## Step 3: Update Settings

Edit `financeinsights/settings.py`:

```python
# Add these lines around line 176 (replace OpenAI settings):

# AI Provider Selection
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")  # Options: "openai", "gemini", "none"

# OpenAI Configuration (if using OpenAI)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Google Gemini Configuration (if using Gemini)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_KEY_HERE")  # Paste your key here
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Common AI settings
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "1500"))
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
AI_PLAYBOOK_ENABLED = os.getenv("AI_PLAYBOOK_ENABLED", "True").lower() == "true"
PLAYBOOK_ENABLE_FORECASTING = os.getenv("PLAYBOOK_ENABLE_FORECASTING", "True").lower() == "true"
PLAYBOOK_ENABLE_CONVERSATIONS = os.getenv("PLAYBOOK_ENABLE_CONVERSATIONS", "True").lower() == "true"
```

---

## Step 4: Update AI Service to Support Gemini

I'll create a modified `ai_service.py` that supports both OpenAI and Gemini.

**Do you want me to:**
1. **Modify the existing code** to support both providers (recommended)
2. **Create a Gemini-only version** (simpler, but removes OpenAI support)

---

## Gemini Free Tier Limits

| Feature | Gemini Free | OpenAI Free |
|---------|-------------|-------------|
| Requests/minute | 60 | 3 |
| Requests/day | 1,500 | ~90 |
| Cost | $0 forever | $0 (for 3 months) |
| Credit card | Not required | Not required |
| Phone verification | Not required | Required |

**Gemini is MUCH better for free tier!**

---

## Comparison

### Gemini 1.5 Flash
- ✅ FREE with high limits
- ✅ Fast responses
- ✅ Good quality
- ✅ No verification needed
- ✅ 1M token context window

### OpenAI GPT-4o-mini
- ⚠️ FREE tier very limited (3 RPM)
- ✅ Slightly better quality
- ❌ Phone verification required
- ❌ Free credits expire

---

## Next Steps

**Choose one:**

### A. Switch to Gemini (RECOMMENDED for free usage)
1. Get Gemini API key: https://aistudio.google.com/app/apikey
2. Tell me and I'll update the code to use Gemini
3. **Result:** Free AI with generous limits!

### B. Try to fix OpenAI free tier
1. Verify phone number at https://platform.openai.com/account/
2. Check if free credits are available
3. **Result:** May or may not work (depends on account status)

### C. Use fallback mode (no AI)
1. Set `AI_PLAYBOOK_ENABLED = False`
2. **Result:** Basic functionality, no AI costs

---

## My Recommendation

**Use Google Gemini!** It's:
- Completely free
- Better free tier than OpenAI
- No verification hassles
- Takes 5 minutes to switch

Want me to update the code to use Gemini? Just say "yes" and give me your Gemini API key!

---

**Status:** Ready to switch to free Google Gemini  
**Time:** 5 minutes to switch  
**Cost:** $0 forever  
**Quality:** Excellent (comparable to GPT-4o-mini)

