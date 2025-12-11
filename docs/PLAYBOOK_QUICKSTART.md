# 🚀 AI Financial Playbook - Quick Start Guide

## Get Started in 5 Minutes

### 1. Visit the Playbook
Navigate to: **http://127.0.0.1:8000/playbook/**

You'll see the Playbook overview with stats and insights.

---

### 2. Create Your First Goal

Click **"+ Create Goal"** and type your goal in plain English:

**Examples:**
```
"I want 6 months of runway by March 2026"
"Save £10,000 for equipment by December 2025"
"Keep marketing spend under 15% of revenue"
"Reach £50,000 in monthly revenue"
```

Click **Continue** →

---

### 3. Review AI-Parsed Goal

The AI will parse your goal and show:
- ✨ **Confidence Score** - How well it understood
- **Goal Type** - Auto-detected (runway, savings, etc.)
- **Target Value** - Extracted from your input
- **Target Date** - Parsed date if mentioned
- 💡 **Suggestions** - Tips to improve clarity

Edit any fields if needed, then click **"Create Goal ✓"**

---

### 4. View Your Goal

You'll be redirected to the goal detail page showing:

📊 **Progress Chart** - Historical progress visualization

✨ **AI Explanation** - WHY the goal is in its current state:
> "Your runway goal is on track. You're currently at 4.5 months, which is 75% of your 6-month target. Your burn rate has been stable at £8,500/month, and with current revenue trends, you're projected to reach your goal by February 2026..."

💡 **Recommendations** - Actionable advice:
- Reduce non-essential expenses by 10%
- Increase monthly savings allocation
- Review subscription costs

⚠️ **Risk Factors** - Potential threats:
- Seasonal revenue dip expected in Q1
- Marketing spend trending upward

📈 **Trend Analysis** - Pattern detection:
> "Progress has improved 12% over the past 30 days, showing positive acceleration..."

---

### 5. Try the What-If Simulator

Scroll to the chat interface and ask:

**Example Questions:**
```
"What if I cut expenses by 15%?"
"What if we increase revenue by £5,000?"
"What if I get a one-time payment of £50,000?"
```

The AI will:
1. Parse your simulation request
2. Run the hypothetical scenario
3. Show original vs simulated outcome
4. Explain if it helps achieve your goal

---

### 6. Refresh for Latest Insights

Click **"🔄 Refresh"** to:
- Re-evaluate with latest transaction data
- Generate fresh AI insights
- Update charts and recommendations
- Get current risk assessment

---

## 💡 Pro Tips

### Get Better AI Insights
To get the best AI analysis, add your **OpenAI API key**:

1. Create `.env` file in project root
2. Add:
   ```bash
   OPENAI_API_KEY=sk-proj-your-key-here
   ```
3. Restart server

**Without API key:** Everything still works with template-based responses!

### Run Automated Evaluations
Schedule daily evaluations:

```bash
# Run manually
python manage.py evaluate_playbook_goals

# Or add to crontab for daily 2 AM runs
0 2 * * * cd /path/to/project && python manage.py evaluate_playbook_goals
```

### Import Transaction Data
Goals work best with real data! Import your transactions via:
- **Upload** page (CSV/XLSX)
- **Transactions** page (manual entry)
- Or use existing data

---

## 🎯 Goal Types Explained

### 1. **Cash Runway** 🏃
"Have X months of operating expenses in reserve"
- **Target:** Number of months (e.g., 6)
- **Tracks:** Current balance / monthly burn rate
- **Example:** "Build 6 months runway by March"

### 2. **Savings Target** 💰
"Save £X by [date]"
- **Target:** Amount to save
- **Tracks:** Net inflows over time
- **Example:** "Save £15,000 by year end"

### 3. **Spending Limit** 📉
"Keep [category] under £X per period"
- **Target:** Maximum spending allowed
- **Tracks:** Outflows in category/period
- **Example:** "Keep marketing under £2,000/month"

### 4. **Budget Compliance** 📋
"Stay within budget for [budget name]"
- **Target:** Budget amount
- **Tracks:** Actual vs budgeted spend
- **Example:** "Stay within Q4 Marketing budget"

### 5. **Revenue Target** 📈
"Reach £X in [period] revenue"
- **Target:** Revenue amount
- **Tracks:** Inflows over period
- **Example:** "Reach £50,000 monthly revenue"

### 6. **Profit Margin** 💹
"Achieve X% profit margin"
- **Target:** Margin percentage
- **Tracks:** (Revenue - Costs) / Revenue
- **Example:** "Achieve 25% profit margin"

---

## 🔍 Understanding Status Badges

- 🟢 **Achieved** - Goal reached! 🎉
- 🔵 **On Track** - Making good progress (75%+)
- 🟡 **At Risk** - Needs attention (50-75%)
- 🔴 **Off Track** - Significant changes needed (<50%)
- ⚪ **Not Started** - Goal just created

---

## ❓ Common Questions

### "How often are goals evaluated?"
- **Automatically:** Can be scheduled (daily/weekly)
- **Manually:** Click "Refresh" anytime
- **On creation:** Initial evaluation runs immediately

### "Do I need an API key?"
**No!** The system works without it:
- Goal creation: Rule-based parsing
- Explanations: Template-based
- Recommendations: Basic rules
- AI just makes it smarter!

### "Can I edit a goal?"
Currently goals can be:
- **Archived** (delete button)
- **Created new**
- Future: Edit functionality

### "How accurate are forecasts?"
Forecasts use:
- Historical trend data
- Statistical analysis
- AI pattern recognition
- More data = better accuracy

### "Can I export goal data?"
Via Django admin:
- `/admin/app_core/financialgoal/`
- `/admin/app_core/goalevaluation/`
- Export to CSV

---

## 🐛 Troubleshooting

### Goal not evaluating?
1. Check you have transaction data
2. Verify organization is set
3. Run manual command:
   ```bash
   python manage.py evaluate_playbook_goals --force
   ```

### AI not working?
1. Check `OPENAI_API_KEY` in `.env`
2. Verify `AI_PLAYBOOK_ENABLED=True`
3. Check logs for API errors
4. Fallback mode still works!

### Charts not showing?
1. Check browser console for errors
2. Verify Chart.js is loading
3. Clear browser cache
4. Check evaluation history exists

---

## 🎓 Learn More

- **Full Documentation:** `docs/AI_GOAL_COPILOT_README.md`
- **Implementation Details:** `docs/AI_PLAYBOOK_COMPLETE.md`
- **Progress Tracking:** `docs/AI_PLAYBOOK_PROGRESS.md`

---

## 🚀 You're Ready!

Start creating goals and let the AI guide you toward financial success!

**Questions?** Check the admin panel or documentation.

**Happy Planning! 🎯**

