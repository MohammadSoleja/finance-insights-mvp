# Team Collaboration - Testing Guide & User Linking 🧪

**Date**: November 20, 2025

---

## 🎯 Current Status

### What's Already Set Up:
✅ **Every user automatically has an organization**
- When you log in, you're automatically assigned to your personal organization
- Created during migration: "username's Organization"
- You're automatically the Owner of your personal organization

### How Users Are Currently Linked:
1. **Existing Users**: Automatically migrated to personal organizations
2. **New Users**: Will need a post-signup hook to create their organization
3. **Invitations**: Admins can invite existing users to join their organization

---

## 🔧 Quick Fix Needed

### Issue: New users signing up won't get an organization automatically

**Solution**: We need to create an organization when a new user signs up.

Let me implement this now...

---

## 📋 How The System Works

### 1. Organization Structure:

```
Personal Use (Free Plan):
└── User A
    └── "User A's Organization" (Owner)
        ├── All their transactions
        ├── All their budgets
        └── All their projects

Small Business (Professional Plan):
└── Company ABC
    ├── User B (Owner)
    ├── User C (Admin)
    └── User D (Accountant)
        └── Shared data across all members

Enterprise (Enterprise Plan):
└── Big Corp Inc
    ├── 20+ team members
    ├── Multiple roles
    ├── Approval workflows
    └── Activity tracking
```

### 2. How Users Join Organizations:

**Method 1: Invitation (Current)**
1. Owner/Admin goes to Team → Members
2. Clicks "Invite Member"
3. Enters user's email (user must already have account)
4. Selects role (Admin, Accountant, Viewer, etc.)
5. User is immediately added to the organization

**Method 2: Organization Codes (Future)**
- Organization has a join code
- Users can enter code to join
- Good for public/open organizations

**Method 3: Email Invitations (Future)**
- Send email to non-users
- They sign up and auto-join
- Currently requires manual account creation first

---

## 🧪 Testing Guide

### Step 1: Verify Your Current Setup

1. **Start the server:**
   ```bash
   python manage.py runserver
   ```

2. **Login** with your account (msoleja)

3. **Check the dropdown:**
   - Click your avatar (top right)
   - You should see:
     - Your username
     - "My Profile"
     - "Organization" section
     - Your organization name ("msoleja's Organization")
     - "Team Dashboard" link
     - "Activity Log" link

### Step 2: Access Team Pages

1. **Team Overview** (`/team/`)
   - Click "Team Dashboard" in dropdown OR
   - Navigate to: http://localhost:8000/team/
   - You should see:
     - 4 stat cards (Members: 1, Roles: 3, etc.)
     - Your member info
     - Recent activity (empty if no actions yet)

2. **Team Members** (`/team/members/`)
   - Click "Members" in sidebar
   - You should see:
     - Yourself listed as "Owner"
     - "Invite Member" button
     - Your email and join date

3. **Activity Log** (`/team/activity/`)
   - Click "Activity Log" in sidebar
   - Should show migration activities
   - Filter options for action/entity/user

### Step 3: Test Inviting Members

**Prerequisites**: You need another user account

**Create Test User:**
```bash
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
User = get_user_model()

# Create test user
test_user = User.objects.create_user(
    username='testuser',
    email='test@example.com',
    password='testpass123'
)

print(f"Created user: {test_user.username}")
exit()
```

**Invite the User:**
1. Go to Team → Members
2. Click "Invite Member"
3. Enter email: `test@example.com`
4. Select role: "Admin"
5. Click "Send Invitation"
6. User should appear in members list!

### Step 4: Test Organization Switching

**Create Second Organization for Your User:**
```bash
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
from app_core.models import Organization, OrganizationRole, OrganizationMember
from django.utils.text import slugify

User = get_user_model()
user = User.objects.get(username='msoleja')  # Your username

# Create second organization
org2 = Organization.objects.create(
    name="My Business LLC",
    slug="my-business-llc",
    owner=user,
    max_users=5,
    plan='professional'
)

# Create Owner role
owner_role = OrganizationRole.objects.create(
    organization=org2,
    name='Owner',
    is_owner=True,
    is_system=True,
    can_manage_organization=True,
    can_manage_members=True,
    can_manage_roles=True,
    can_view_transactions=True,
    can_create_transactions=True,
    can_edit_transactions=True,
    can_delete_transactions=True,
    can_export_transactions=True,
    can_view_budgets=True,
    can_create_budgets=True,
    can_edit_budgets=True,
    can_delete_budgets=True,
    can_view_projects=True,
    can_create_projects=True,
    can_edit_projects=True,
    can_delete_projects=True,
    can_view_invoices=True,
    can_create_invoices=True,
    can_edit_invoices=True,
    can_delete_invoices=True,
    can_send_invoices=True,
    can_view_reports=True,
    can_export_reports=True,
)

# Add yourself as member
from django.utils import timezone
OrganizationMember.objects.create(
    organization=org2,
    user=user,
    role=owner_role,
    invited_by=user,
    accepted_at=timezone.now(),
    is_active=True
)

print(f"Created organization: {org2.name}")
exit()
```

**Test Switching:**
1. Refresh the page
2. Click avatar dropdown
3. Click your organization name
4. You should see dropdown with BOTH organizations:
   - "msoleja's Organization" (Owner)
   - "My Business LLC" (Owner)
5. Click one to switch
6. Page refreshes
7. All data now filtered to that organization

### Step 5: Test Permission System

**As Owner:**
- ✅ Can invite members
- ✅ Can remove members
- ✅ Can change roles
- ✅ Can see all data

**Logout and Login as Test User:**
1. Logout
2. Login as: `testuser` / `testpass123`
3. You won't have an organization yet (we'll fix this)
4. But if invited to msoleja's org, you'd see it in dropdown

---

## 🔨 Fixes Needed

### Fix 1: Auto-Create Organization on Signup

**File**: `/app_web/views.py` - Update `signup_view`

### Fix 2: Better Error Handling

If user has no organization, redirect to "create organization" page

### Fix 3: Organization Creation Page

Allow users to create their own organizations (for business plans)

---

## 💡 Pricing Plan Integration

### Suggested Structure:

**Free Plan (Personal)**:
- 1 organization
- 1 user (yourself)
- Unlimited transactions/budgets/projects
- No team features
- **Price**: Free

**Professional Plan (Small Business)**:
- 1 organization
- Up to 5 team members
- All team features
- Role-based permissions
- Activity logging
- **Price**: $29/month

**Enterprise Plan (Big Business)**:
- Unlimited organizations
- Unlimited team members
- Custom roles
- Approval workflows
- Priority support
- API access
- **Price**: $99/month or Custom

### Implementation in Models:

```python
# Organization model already has:
plan = models.CharField(max_length=20, default='free')
max_users = models.IntegerField(default=1)

# Plans:
- 'free' → max_users=1
- 'professional' → max_users=5
- 'enterprise' → max_users=999
```

### Enforcement:

```python
# Already implemented in OrganizationMember invitation:
if not org.can_add_member():
    return error("Reached max users limit")
```

---

## 🎯 Next Steps to Make It Fully Functional

### 1. Fix New User Signup (Priority 1)
Add organization creation to signup process

### 2. Test Multi-User Scenario
- Create 2+ accounts
- Invite them to same org
- Test permissions
- Test data sharing

### 3. Add Pricing Enforcement
- Check plan limits
- Upgrade prompts
- Billing integration (Stripe?)

### 4. Polish UI
- Show plan name in dropdown
- "Upgrade" button for free users
- Usage stats (2/5 members used)

---

## 🐛 Current Limitations

### Known Issues:
1. **New signups don't get organization** (needs fix)
2. **Can't create new organization from UI** (needs page)
3. **No billing integration** (future)
4. **No email invitations** (requires existing account)
5. **Organization switcher might not show if middleware fails** (needs debugging)

### Why Dropdown Might Not Show:
1. Middleware not applying to partials (should work though)
2. Template context not passed correctly
3. User has no organizations (new signup issue)

---

## 🔍 Debug Steps

### Check if you have an organization:

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

**Expected Output**:
```
Organizations: 1
- msoleja's Organization (Owner)
```

If this shows 0, then that's the problem!

---

## ✅ Quick Verification Checklist

- [ ] Server starts without errors
- [ ] Can login successfully
- [ ] Avatar dropdown appears
- [ ] Can see organization section in dropdown
- [ ] Can access /team/ page
- [ ] Can see team stats
- [ ] Can access /team/members/ page
- [ ] Can see yourself listed as Owner
- [ ] Can access /team/activity/ page
- [ ] Can see recent activities

**If any fail, let me know which step and we'll debug!**

---

**Let me now implement the signup fix...**

