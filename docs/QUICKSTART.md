# 🚀 QUICK START - Test Team Collaboration NOW

**Ready to test? Follow these 3 simple steps:**

---

## Step 1: Start Server & Check Debug Page (2 minutes)

```bash
# Start server
python manage.py runserver
```

Then open: **http://localhost:8000/debug/org/**

**What you should see:**
- ✅ Your organization: "msoleja's Organization"
- ✅ Your role: Owner
- ✅ All green checkmarks

**If you see problems:** Check the "Debug Steps" section below

---

## Step 2: Test the User Dropdown (30 seconds)

1. Click your **avatar** (top-right, shows "MS")
2. Look for the **"Organization"** section
3. You should see:
   - Your organization name
   - "Team Dashboard" link
   - "Activity Log" link

**Click "Team Dashboard"** → You should see team stats!

---

## Step 3: Create & Invite a Test User (3 minutes)

### A. Create test user:
```bash
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
User = get_user_model()

test = User.objects.create_user(
    username='alice',
    email='alice@example.com',
    password='testpass123'
)
print(f"✅ Created: {test.username}")
exit()
```

### B. Invite to your organization:
1. Go to: http://localhost:8000/team/members/
2. Click **"Invite Member"**
3. Enter email: `alice@example.com`
4. Select role: **Admin**
5. Click **"Send Invitation"**

**Result:** Alice should appear in your members list! ✅

---

## 🎉 That's It!

**If all 3 steps worked:**
- ✅ Team collaboration is WORKING
- ✅ Organization system is LIVE  
- ✅ You can invite users
- ✅ Everything is ready!

---

## 🐛 Quick Debug

### Problem: No organization in dropdown

**Fix:**
```bash
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
from app_core.models import OrganizationMember

User = get_user_model()
user = User.objects.get(username='msoleja')

# Check memberships
memberships = OrganizationMember.objects.filter(user=user, is_active=True)
print(f"Organizations: {memberships.count()}")

for m in memberships:
    print(f"- {m.organization.name} ({m.role.name})")
```

**Should show:**
```
Organizations: 1
- msoleja's Organization (Owner)
```

**If it shows 0:** You need to create organization manually. Run:

```python
from app_core.models import Organization, OrganizationRole, OrganizationMember
from django.utils.text import slugify
from django.utils import timezone

org = Organization.objects.create(
    name=f"{user.username}'s Organization",
    slug=slugify(user.username),
    owner=user,
    max_users=1,
    plan='free'
)

owner_role = OrganizationRole.objects.create(
    organization=org,
    name='Owner',
    is_owner=True,
    is_system=True,
    can_manage_organization=True,
    can_manage_members=True,
    can_view_transactions=True,
    can_create_transactions=True,
    can_edit_transactions=True,
    can_delete_transactions=True,
    can_view_budgets=True,
    can_create_budgets=True,
    can_view_projects=True,
    can_view_invoices=True,
    can_view_reports=True,
)

OrganizationMember.objects.create(
    organization=org,
    user=user,
    role=owner_role,
    invited_by=user,
    accepted_at=timezone.now(),
    is_active=True
)

print(f"✅ Created organization!")
exit()
```

---

## 📚 More Testing

**Full testing guide:** `/docs/TESTING_INSTRUCTIONS.md`

**Pricing info:** `/docs/PRICING_TIERS.md`

**Implementation docs:** `/docs/implementations/TEAM_COLLABORATION_COMPLETE.md`

---

**Questions? Start with Step 1 and let me know what you see!** 🚀

