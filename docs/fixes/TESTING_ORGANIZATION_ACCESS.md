# Testing Instructions - Organization Data Access

## Background
We've fixed the organization filtering so that all members of an organization can now see and work with the organization's data (based on their role permissions).

## Test Status
✅ **Backend Test Passed** - The test script confirms:
- testuser can access 4 projects
- testuser can access 3 invoices  
- testuser can access 1 client
- testuser can access 1 budget
- All 1,484 transactions are accessible

## Browser Testing

### 1. Test as testuser (Admin Role)

#### Login
```
Username: testuser
Password: testpassword
```

#### What to Test

**✅ Projects Page** (`/projects/`)
- Should see all 4 projects:
  - Fixed Costs
  - Q3 Marketing Campaign
  - Q4 Marketing Campaign
  - Test
- Click on any project → Should see project details (financials, milestones, etc.)
- Previously: ❌ Project details would not load
- Now: ✅ Should work

**✅ Invoices Page** (`/invoices/`)
- Should see all 3 invoices:
  - INV-2025-0003
  - INV-2025-0002
  - INV-2025-0004
- Click View/Edit → Should see invoice details
- Previously: ❌ No invoices visible
- Now: ✅ Should show all invoices

**✅ Clients Page** (`/clients/`)
- Should see 1 client: Mohammad Bin Ali Soleja
- Click to view/edit client details
- Previously: ❌ No clients visible
- Now: ✅ Should show all clients

**✅ Budgets Page** (`/budgets/`)
- Should see 1 budget: COGS - £200.00
- Click to edit budget
- Previously: ❌ No budgets visible
- Now: ✅ Should show all budgets

**✅ Transactions Page** (`/transactions/`)
- Should see all 1,484 transactions
- This was already working

**✅ Dashboard** (`/dashboard/`)
- Should show KPIs and charts based on all organization data
- This was already working

### 2. Test as msoleja (Owner Role)

All functionality should continue to work as before. Owner should see the same data.

### 3. Test Organization Switcher

In the top-right dropdown menu:
- Should see "msoleja's Organization" 
- Both users are members of this organization
- Organization switcher should be visible

### 4. Test Permissions

While testuser is an Admin, verify role-based permissions work:

**testuser (Admin) should be able to:**
- ✅ View all data
- ✅ Create/edit projects
- ✅ Create/edit invoices
- ✅ Create/edit clients
- ✅ Create/edit budgets
- ✅ Delete items (if admin has delete permissions)

**If you create a Viewer role user, they should:**
- ✅ View all data
- ❌ NOT be able to edit/delete

## Expected Results

### Before Fix
```
testuser logs in →
- Sees transactions ✅
- Sees projects list ✅
- Clicks project → ❌ Error or empty
- Goes to invoices → ❌ Empty list
- Goes to clients → ❌ Empty list
- Goes to budgets → ❌ Empty list
```

### After Fix
```
testuser logs in →
- Sees transactions ✅
- Sees projects list ✅
- Clicks project → ✅ Shows full details
- Goes to invoices → ✅ Shows all 3 invoices
- Goes to clients → ✅ Shows 1 client
- Goes to budgets → ✅ Shows 1 budget
```

## Debug Page

Visit `/debug/org/` while logged in as either user to see:
- Current organization
- Organization memberships
- Request context details

## Troubleshooting

### If data still not visible:
1. Check the debug page (`/debug/org/`) to ensure organization is set
2. Clear browser cookies/cache
3. Log out and log back in
4. Check browser console for JavaScript errors
5. Check server logs for Python errors

### If getting permission errors:
1. Check the user's role permissions in Team Dashboard (`/team/`)
2. Verify the organization middleware is working (check debug page)
3. Check activity log for any permission denied events

## Next Steps

After confirming everything works:
1. Test creating new data as testuser (projects, invoices, etc.)
2. Verify the created data shows for both users
3. Test editing data created by the other user
4. Test the audit log to ensure user actions are tracked
5. Test switching between organizations (if you have multiple)

## Files Changed

See `/docs/implementations/ORGANIZATION_FILTERING_FIX.md` for complete list of changes.

