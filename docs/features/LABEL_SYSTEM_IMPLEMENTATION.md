# Label System Implementation - IN PROGRESS

## Overview
Implementing a tag/label-based categorization system to replace rigid string-based categories. This solves the "Fee" vs "Fees" problem and enables flexible project-based budgeting.

## Design Decisions (Based on User Requirements)

### 1. Single Label Per Transaction
- **Simple**: Each transaction has ONE label
- **Clear**: No ambiguity about categorization
- **Easy UI**: Dropdown/autocomplete selector

### 2. Multi-Label Budgets  
- **Flexible**: Budget can track MULTIPLE labels
- **Business-Focused**: Perfect for project-based tracking
- **Example**: "Q4 Marketing" budget tracks [Advertising, Events, Social Media]

### 3. User-Managed Labels
- **Control**: Users create their own labels in Settings
- **Customizable**: Set label names and colors
- **Unique**: Each user has their own label set

### 4. Backward Compatibility
- **Migration**: Auto-convert existing categories → labels
- **Graceful**: Keep old category field during transition
- **Safe**: No data loss

## Database Schema Changes

### New Model: Label
```python
Label:
  - id (PK)
  - user (FK to User)
  - name (str, max 64 chars)
  - color (hex code, default #2563eb)
  - created_at (timestamp)
  - UNIQUE(user, name)  # Each user's labels are unique
```

### Updated: Transaction
```python
Transaction:
  - label (FK to Label, nullable) # NEW!
  - category (str) # DEPRECATED, kept for migration
  ... (other fields unchanged)
```

### Updated: Budget
```python
Budget:
  - name (str) # NEW! Budget name (e.g., "Q4 Marketing")
  - labels (M2M to Label) # NEW! Multiple labels per budget
  - category (str) # DEPRECATED, kept for migration
  ... (other fields unchanged)
```

## Implementation Status

### ✅ Completed
1. **Models**:
   - Label model created
   - Transaction updated with label FK
   - Budget updated with name + labels M2M
   - Backward compatibility fields retained

2. **Business Logic**:
   - budgets.py updated to track spending across multiple labels
   - calculate_budget_usage() works with label lists
   - get_budget_summary() returns label info

3. **Admin Panel**:
   - Label registered in admin
   - Transaction/Budget admin updated
   - Nice M2M UI for budget labels

4. **Migration File**:
   - 0010_label_transaction_label_budget_name_budget_labels_and_more.py created
   - Schema changes defined
   - Ready to apply

### 🚧 In Progress / To Do
1. **Migration Application**:
   - Apply migration to database (having NumPy compatibility issues)
   - Create data migration to convert categories → labels
   
2. **Forms**:
   - Update TransactionForm with label selector
   - Update BudgetForm with multi-label picker + name field
   - Label create/edit forms

3. **Views**:
   - Label management in Settings page
   - Update budget/transaction views for labels
   - API endpoints for label CRUD

4. **Templates**:
   - Settings page: Label management UI
   - Transaction form: Label dropdown
   - Budget form: Name field + multi-label selector
   - Budget cards: Show labels instead of category

5. **Auto-Conversion**:
   - Data migration script
   - Convert existing categories to labels
   - Assign labels to existing transactions
   - Update existing budgets

## Migration Strategy

### Phase 1: Schema (Current)
- Add Label model
- Add label fields to Transaction/Budget
- Keep old category fields

### Phase 2: Data Migration (Next)
```python
# For each user:
  categories = get_distinct_categories(user)
  for cat in categories:
    label = Label.create(user=user, name=cat)
    Transaction.filter(user=user, category=cat).update(label=label)
    Budget.filter(user=user, category=cat).add_label(label)
```

### Phase 3: UI Updates (After Migration)
- Forms use labels
- Views query by label
- Display labels with colors

### Phase 4: Cleanup (Future)
- Remove category fields (optional)
- Fully deprecate old system

## User Experience

### Settings Page - Label Management
```
Labels
───────────────────────────────────────
+ Create New Label

Existing Labels:
┌────────────────────────────┐
│ ● Office Supplies  #2563eb │  [Edit] [Delete]
│ ● Client A         #16a34a │  [Edit] [Delete]
│ ● Marketing        #f59e0b │  [Edit] [Delete]
└────────────────────────────┘
```

### Transaction Form - Label Selector
```
Label:  [Office Supplies ▼]  + Create New
        (Autocomplete dropdown with colors)
```

### Budget Form - Multi-Label
```
Budget Name: [Q4 Marketing Campaign           ]

Labels:  [× Advertising] [× Events] [× Social Media]  + Add Label
         (Tag picker - click to add/remove)

Amount: [£5000.00]
Period: [Custom Date Range ▼]
```

### Budget Card - Show Labels
```
┌────────────────────────────────────┐
│ Q4 Marketing Campaign              │
│ ● Advertising  ● Events  ● Social  │
│                                    │
│ ████████░░░░ 67% used             │
│                                    │
│ £3,350 / £5,000                   │
└────────────────────────────────────┘
```

## Benefits

### Problem Solved
❌ **Before**: "Fee" ≠ "Fees" ≠ "Banking Fee"
✅ **After**: One "Fees" label catches all

### Project-Based Budgeting
✅ Track spending across multiple categories
✅ Real business use case: "Client Project Alpha" budget tracks [Consulting, Travel, Materials]

### Flexibility
✅ Users control their taxonomy
✅ Colors for visual distinction
✅ Easy to reorganize

## Technical Notes

### NumPy Compatibility Issue
- Anaconda's NumPy 2.2.6 conflicts with bottleneck
- Migration commands timing out
- Workaround: Use venv Python or manually apply migration

### Database Indexes
- Label: (user, name) for fast lookups
- Transaction: (user, label) for filtering
- Maintains existing indexes

### Foreign Key Cascade
- Label deleted → Transaction.label = NULL (SET_NULL)
- User deleted → Labels deleted (CASCADE)
- Preserves data integrity

## Next Steps

1. **Resolve Migration**: Apply 0010 migration successfully
2. **Data Migration**: Convert existing categories to labels
3. **Settings UI**: Build label management page
4. **Form Updates**: Label selectors in transaction/budget forms
5. **Testing**: Verify label tracking works correctly
6. **Documentation**: Update user guide

## Files Modified

### Models
- `app_core/models.py` - Label, Transaction, Budget

### Business Logic
- `app_core/budgets.py` - Multi-label budget tracking

### Admin
- `app_core/admin.py` - Label registration

### Migrations
- `app_core/migrations/0010_*.py` - Schema changes

### To Be Created
- Label management views
- Label forms
- Settings page template updates
- Transaction/Budget form updates
- Data migration script

---

## Current Blocker

**NumPy/Pandas compatibility** causing migration commands to hang.

**Solutions**:
1. Use venv Python instead of Anaconda
2. Run migration in production environment
3. Apply migration manually via SQL

Once migration applies, we can proceed with UI and data migration!

