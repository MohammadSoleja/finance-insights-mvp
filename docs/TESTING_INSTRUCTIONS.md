# 🧪 STEP-BY-STEP TESTING INSTRUCTIONS

**Date**: November 20, 2025

---

## ✅ What I Just Fixed

1. ✅ **New signups now automatically create organizations**
2. ✅ **Created a debug page** to check your organization status
3. ✅ **All existing users already have organizations** (from migration)

---

## 🚀 START HERE - Quick Test

### Step 1: Check Your Organization Status

1. **Start the server:**
   ```bash
   python manage.py runserver
   ```

2. **Go to the debug page:**
   - Open: http://localhost:8000/debug/org/
   - Login if needed (username: `msoleja`)

3. **What you should see:**
   - ✅ Your username and email
   - ✅ Current organization: "msoleja's Organization"
   - ✅ Your membership listed with "Owner" role
   - ✅ All green checkmarks

4. **If you see RED ❌ errors:**
   - Run this in terminal:
   ```bash
   python manage.py shell
   ```
   
   Then paste this code:
   ```python
   from django.contrib.auth import get_user_model
   from app_core.models import OrganizationMember
   
   User = get_user_model()
   user = User.objects.get(username='msoleja')
   
   memberships = OrganizationMember.objects.filter(user=user, is_active=True)
   print(f"Organizations: {memberships.count()}")
   
   for m in memberships:
       print(f"- {m.organization.name} ({m.role.name})")
   
   exit()
   ```
   
   **Expected output:**
   ```
   Organizations: 1
   - msoleja's Organization (Owner)
   ```

---

### Step 2: Check the User Dropdown

1. **Look at the top-right corner of any page**
2. **Click your avatar** (shows "MS" or your initials)
3. **You should see:**
   ```
   msoleja
   My Profile
   ─────────────
   Organization
   [msoleja's Organization ▼]
   Team Dashboard
   Activity Log
   ─────────────
   Settings
   Log out
   ```

4. **If you DON'T see the "Organization" section:**
   - The dropdown code is there, but middleware might not be working
   - Go to http://localhost:8000/debug/org/ to see what's wrong

---

### Step 3: Access Team Pages

1. **Click "Team Dashboard"** in the dropdown (or go to http://localhost:8000/team/)

2. **You should see:**
   - 4 colorful stat cards showing:
     - Team Members: 1
     - Active Roles: 3
     - Pending Approvals: 0
     - Permission Requests: 0
   - "Active Members" section with your info
   - "Recent Activity" section (might be empty)

3. **Click "Members" in the left sidebar**
   - You should see yourself listed as "Owner"
   - "Invite Member" button at the top

4. **Click "Activity Log" in the left sidebar**
   - Should show migration activities
   - Filter options available

---

### Step 4: Test Creating a Second User

This tests if new signups work correctly.

1. **Open a private/incognito browser window**

2. **Go to:** http://localhost:8000/accounts/signup/

3. **Create account:**
   - Username: `testuser`
   - Password: `testpass123`
   - Confirm password: `testpass123`

4. **After signup, go to:** http://localhost:8000/debug/org/

5. **You should see:**
   - ✅ Organization: "testuser's Organization"
   - ✅ Role: Owner
   - ✅ All green checkmarks

**If this works, new signup is FIXED! ✅**

---

### Step 5: Test Inviting testuser to Your Organization

1. **Close the incognito window, go back to your main browser**

2. **Make sure you're logged in as `msoleja`**

3. **Go to:** http://localhost:8000/team/members/

4. **Click "Invite Member"**

5. **Fill in the form:**
   - Email: (leave blank - we'll use username search)
   - Actually, the current system needs email, so first let's add an email to testuser

6. **Open terminal and run:**
   ```bash
   python manage.py shell
   ```
   
   ```python
   from django.contrib.auth import get_user_model
   User = get_user_model()
   
   testuser = User.objects.get(username='testuser')
   testuser.email = 'test@example.com'
   testuser.save()
   
   print(f"Updated {testuser.username} email to {testuser.email}")
   exit()
   ```

7. **Now try inviting:**
   - Go back to http://localhost:8000/team/members/
   - Click "Invite Member"
   - Email: `test@example.com`
   - Role: Select "Admin"
   - Click "Send Invitation"

8. **You should see:**
   - Success message
   - Page refreshes
   - testuser now appears in members list!

---

### Step 6: Test Organization Switching (Multiple Orgs)

This is for when you belong to multiple organizations.

1. **Create a second organization for yourself:**
   ```bash
   python manage.py shell
   ```
   
   ```python
   from django.contrib.auth import get_user_model
   from app_core.models import Organization, OrganizationRole, OrganizationMember
   from django.utils import timezone
   
   User = get_user_model()
   user = User.objects.get(username='msoleja')
   
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
   OrganizationMember.objects.create(
       organization=org2,
       user=user,
       role=owner_role,
       invited_by=user,
       accepted_at=timezone.now(),
       is_active=True
   )
   
   print(f"✅ Created: {org2.name}")
   print(f"✅ You now have 2 organizations!")
   exit()
   ```

2. **Refresh the page**

3. **Click your avatar dropdown**

4. **Click on the organization name** (you should see a dropdown arrow)

5. **You should see BOTH organizations:**
   - msoleja's Organization (Owner) - with blue highlight (current)
   - My Business LLC (Owner)

6. **Click "My Business LLC"**
   - Page refreshes
   - You're now in the new organization
   - All data filtered to this org

7. **Click avatar again, switch back to your personal org**

**This proves organization switching works! ✅**

---

## 🎯 Testing Checklist

Go through this checklist and mark what works:

- [ ] Debug page shows organization info correctly
- [ ] User dropdown shows "Organization" section
- [ ] Can see organization name in dropdown
- [ ] Can access /team/ page
- [ ] Team overview shows stats correctly
- [ ] Can access /team/members/
- [ ] See yourself listed as Owner
- [ ] Can access /team/activity/
- [ ] New signups create organization automatically
- [ ] Can invite existing users to organization
- [ ] Can switch between multiple organizations
- [ ] Team members page shows all members
- [ ] Can change member roles
- [ ] Can remove members (except Owner)

---

## 🐛 Common Issues & Solutions

### Issue 1: Dropdown doesn't show organization section

**Diagnosis:**
- Go to http://localhost:8000/debug/org/
- Check if "Current Organization" is showing

**Solution:**
- If no organization showing, run the shell script in Step 1
- Check if middleware is working: look for `request.organization` on debug page

### Issue 2: "No organization" error

**Diagnosis:**
- User doesn't have any organization membership

**Solution:**
```bash
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
from app_core.models import Organization, OrganizationRole, OrganizationMember
from django.utils.text import slugify
from django.utils import timezone

User = get_user_model()
user = User.objects.get(username='YOUR_USERNAME')

# Create organization
org_name = f"{user.username}'s Organization"
slug = slugify(user.username)

org = Organization.objects.create(
    name=org_name,
    slug=slug,
    owner=user,
    max_users=1,
    plan='free'
)

# Create Owner role
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
    can_view_reports=True,
)

# Create membership
OrganizationMember.objects.create(
    organization=org,
    user=user,
    role=owner_role,
    invited_by=user,
    accepted_at=timezone.now(),
    is_active=True
)

print(f"✅ Created organization for {user.username}")
exit()
```

### Issue 3: Can't invite members

**Check:**
- Do you have `can_manage_members` permission? (Owners always do)
- Does the user you're inviting exist? (Check with admin panel or shell)
- Is the email correct?

**Solution:**
Create the user first if they don't exist, then invite them.

---

## 📊 What Should Be Working Now

✅ **Auto-organization creation on signup**
✅ **Organization switching for multi-org users**
✅ **Team member management**
✅ **Role-based permissions**
✅ **Activity logging**
✅ **Team dashboard with stats**
✅ **Debug page for troubleshooting**

---

## 💡 Next Steps After Testing

Once you confirm everything works:

1. **Pricing Integration**
   - Connect plans to billing (Stripe?)
   - Enforce member limits per plan
   - Add "Upgrade" buttons

2. **UI Polish**
   - Show current plan in dropdown
   - Add usage stats (2/5 members)
   - Better error messages

3. **Advanced Features**
   - Custom role creation
   - Approval workflows
   - Email invitations
   - Organization settings page

---

## 🎉 Success Criteria

You'll know it's working when:

1. ✅ You can see your organization in the dropdown
2. ✅ You can access all team pages
3. ✅ New signups automatically get organizations
4. ✅ You can invite users and they appear in your team
5. ✅ You can switch between multiple organizations
6. ✅ All data is filtered by current organization

**Start with Step 1 and let me know what you see!** 🚀

