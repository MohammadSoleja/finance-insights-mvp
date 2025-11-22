# Data Preservation When User is Deleted

**Date:** November 22, 2025  
**Status:** ✅ FIXED  
**Priority:** 🔥 CRITICAL

## Problem

**Question:** If testuser creates a project but leaves the company, does that mean the project will be deleted or kept?

**Answer Before Fix:** ❌ **PROJECT WOULD BE DELETED** (and all their data!)

This was a **critical bug** in the team collaboration system.

---

## The Issue

All organization-shared data models had `on_delete=models.CASCADE` on the `user` field:

```python
# BEFORE (WRONG) ❌
user = models.ForeignKey(User, on_delete=models.CASCADE, ...)
```

**This meant:**
- If testuser is deleted from Django → **ALL their data is CASCADE deleted**
- Projects created by testuser → ❌ **DELETED**
- Invoices created by testuser → ❌ **DELETED**
- Transactions uploaded by testuser → ❌ **DELETED**
- Clients added by testuser → ❌ **DELETED**
- Budgets created by testuser → ❌ **DELETED**

**This is WRONG for team collaboration!** Organization data should belong to the organization, not individual users.

---

## The Fix

Changed `on_delete=models.CASCADE` to `on_delete=models.SET_NULL` for all organization-shared data:

```python
# AFTER (CORRECT) ✅
user = models.ForeignKey(
    User, 
    on_delete=models.SET_NULL, 
    null=True, 
    blank=True,
    related_name="...",
    help_text="User who created this (null if deleted)"
)
```

**Now:**
- If testuser is deleted → **Data is PRESERVED** ✅
- `user` field is set to `NULL` (shows as "Deleted User" or similar)
- Organization still has access to all the data
- Audit trail is maintained (created_at timestamps, etc.)

---

## Models Fixed

Updated 10 models to preserve data:

1. ✅ **Transaction** - Transactions stay even if user deleted
2. ✅ **Label** - Labels remain available
3. ✅ **AutoCategorizeRule** - Rules keep working
4. ✅ **Budget** - Budgets are preserved
5. ✅ **RecurringTransaction** - Recurring transactions continue
6. ✅ **Project** - Projects stay (THIS WAS THE QUESTION!)
7. ✅ **ProjectActivity** - Audit trail preserved
8. ✅ **Client** - Clients remain in system
9. ✅ **Invoice** - Invoices are kept
10. ✅ **InvoiceTemplate** - Templates available to organization

---

## Example Scenario

### Before Fix ❌

```
1. testuser joins organization
2. testuser creates:
   - Project "Website Redesign"
   - Invoice for $5,000
   - 500 transactions
   - 3 clients

3. testuser leaves company
4. Admin deletes testuser from system

RESULT: ❌ ALL DATA DELETED
- Project "Website Redesign" → GONE
- Invoice for $5,000 → GONE  
- 500 transactions → GONE
- 3 clients → GONE
```

### After Fix ✅

```
1. testuser joins organization
2. testuser creates:
   - Project "Website Redesign"
   - Invoice for $5,000
   - 500 transactions
   - 3 clients

3. testuser leaves company
4. Admin deletes testuser from system

RESULT: ✅ ALL DATA PRESERVED
- Project "Website Redesign" → KEPT (user field = null)
- Invoice for $5,000 → KEPT (user field = null)
- 500 transactions → KEPT (user field = null)
- 3 clients → KEPT (user field = null)

Organization can still:
- View all the data
- Edit the data
- Use it in reports
- Continue working on projects
- Send invoices
```

---

## How It Works

### Data Ownership Model

**Organization owns the data, user field is just for audit trail:**

```
Organization
    ├── Project "Website Redesign"
    │   ├── created by: testuser (now: null - user deleted)
    │   ├── organization: msoleja's Organization ✅
    │   └── Still accessible by all org members ✅
    │
    ├── Invoice #INV-001
    │   ├── created by: null (was testuser)
    │   ├── organization: msoleja's Organization ✅
    │   └── Can still be edited/sent ✅
    │
    └── Transactions (500)
        ├── uploaded by: null (was testuser)
        ├── organization: msoleja's Organization ✅
        └── Still in reports and analytics ✅
```

### User Field Purpose

The `user` field is now purely for **audit trail**, not ownership:

- **Purpose:** Track who created/modified something
- **Display:** Show creator name (or "Deleted User" if null)
- **Filtering:** Organization filtering is primary
- **Deletion:** Set to null if user deleted, data remains

---

## Migration

**Created:** `0021_preserve_data_on_user_delete.py`

**What it does:**
- Alters `user` field on 10 models
- Changes from `CASCADE` to `SET_NULL`
- Makes `user` field nullable
- Preserves all existing data

**To apply:**
```bash
python manage.py migrate
```

**Safe to run:** Yes - only changes deletion behavior, doesn't modify existing data

---

## Testing

### Test 1: Create data as testuser then delete user

```python
# 1. Create project as testuser
python manage.py shell
```

```python
from django.contrib.auth.models import User
from app_core.models import Project, Organization

testuser = User.objects.get(username='testuser')
org = Organization.objects.first()

project = Project.objects.create(
    user=testuser,
    organization=org,
    name="Test Project",
    description="Created by testuser"
)

print(f"✅ Created project: {project.name}")
print(f"   Created by: {project.user.username}")
print(f"   Organization: {project.organization.name}")

project_id = project.id
exit()
```

```python
# 2. Delete testuser
from django.contrib.auth.models import User
from app_core.models import Project

testuser = User.objects.get(username='testuser')
testuser.delete()  # Delete the user

# 3. Check if project still exists
project = Project.objects.get(id=project_id)
print(f"✅ Project still exists: {project.name}")
print(f"   Created by: {project.user}")  # Should be None
print(f"   Organization: {project.organization.name}")  # Still there!
```

**Expected Result:**
```
✅ Project still exists: Test Project
   Created by: None
   Organization: msoleja's Organization
```

### Test 2: Remove user from organization

**Different from deleting user!**

```python
from app_core.models import OrganizationMember

# Remove testuser from organization (but don't delete user)
membership = OrganizationMember.objects.get(
    user__username='testuser',
    organization=org
)
membership.delete()

# Check project
project = Project.objects.get(id=project_id)
print(f"✅ Project still exists: {project.name}")
print(f"   Created by: {project.user.username}")  # Still testuser!
print(f"   Organization: {project.organization.name}")  # Still there!
```

---

## Best Practices

### When removing users from organization:

1. **Option A: Deactivate membership**
   ```python
   membership.is_active = False
   membership.save()
   ```
   - User can't access organization
   - User object still exists
   - Data shows their name in audit trail

2. **Option B: Delete membership**
   ```python
   membership.delete()
   ```
   - User removed from organization
   - User object still exists
   - Data shows their name in audit trail
   - User could rejoin later

3. **Option C: Delete user entirely**
   ```python
   user.delete()
   ```
   - User completely removed from system
   - Data is PRESERVED (user field = null)
   - Shows as "Deleted User" in UI
   - Can't rejoin (would need new account)

---

## UI Updates Needed

When displaying data where user might be null:

```python
# In templates
{% if project.user %}
    Created by: {{ project.user.username }}
{% else %}
    Created by: <span class="text-muted">Deleted User</span>
{% endif %}
```

```python
# In views/serializers
'created_by': project.user.username if project.user else 'Deleted User'
```

---

## Related Models Not Changed

These models still use CASCADE (intentional):

1. **OrganizationMember** - CASCADE
   - If user deleted → Remove from all organizations ✅
   - Makes sense - can't be member without user account

2. **ActivityLog** - SET_NULL (changed)
   - Audit trail preserved even if user deleted ✅

3. **Approval** - CASCADE (for requester/approver)
   - Could be changed to SET_NULL in future

---

## Summary

**Before:** Deleting a user would CASCADE delete all their data ❌  
**After:** Deleting a user preserves all organization data ✅

**Your Question Answered:**

> If testuser creates a project but leaves the company, does that mean the project will be deleted or kept?

**Answer:** ✅ **PROJECT IS KEPT!**

The project (and all other data) remains in the organization. The `user` field will be null (showing "Deleted User" in the UI), but all the actual data, functionality, and organization access is preserved.

---

## Files Modified

1. `/Users/mohammadsoleja/Documents/GitHub/finance-insights-mvp/app_core/models.py`
   - 10 model fields updated from CASCADE to SET_NULL

2. Migration created:
   - `app_core/migrations/0021_preserve_data_on_user_delete.py`

---

**Status:** ✅ Ready to migrate  
**Migration:** Run `python manage.py migrate`  
**Risk:** Low - only changes deletion behavior, existing data unaffected

