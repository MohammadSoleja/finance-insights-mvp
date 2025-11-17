# Projects Feature - Quick Start Guide

## How to Access
1. Log in to your account
2. Click **Projects** in the navigation menu
3. You'll see the Projects Management page

## Creating Your First Project

### Step 1: Click "Add Project"
The Add Project modal will open with the following fields:

### Step 2: Fill in Project Details
- **Project Name** (Required): e.g., "Q4 Marketing Campaign"
- **Description** (Optional): Brief overview of the project
- **Budget** (Optional): Set a spending limit (e.g., 5000.00)
- **Status**: Choose Active, On Hold, or Completed
- **Color**: Pick a color for visual identification
- **Start Date**: When the project begins
- **End Date**: Project deadline

### Step 3: Assign Labels
- Select which labels should be tracked in this project
- Any transactions with these labels will automatically appear in the project
- Example: If you select "Marketing" and "Advertising" labels, all transactions tagged with these will count toward this project

### Step 4: Save
Click "Create Project" and you're done!

## Understanding Project Cards

Each project card shows:

### Financial Metrics
- **Budget**: Total allocated budget
- **Spent**: Total outflow (expenses)
- **Income**: Total inflow (revenue)
- **Net**: Income minus expenses (profit/loss)

### Budget Progress Bar
- **Green**: Under 80% of budget (safe)
- **Yellow**: 80-100% of budget (approaching limit)
- **Red**: Over budget (exceeded limit)

### Timeline (if dates set)
- **Time Progress Bar**: Shows how much time has elapsed
- **Days Remaining**: Countdown to deadline
- Visual warnings when deadline is approaching

### Status Badge
- **Active**: Project is ongoing
- **Completed**: Project finished
- **On Hold**: Project paused

## Using Projects

### View Project Details
1. Click "View Details" on any project card
2. See comprehensive breakdown:
   - Total financial summary
   - Income breakdown by label
   - Expense breakdown by label
   - Recent transactions (up to 100)
   - Profit margin percentage

### Edit a Project
1. Click "Edit" on the project card
2. Modify any fields
3. Save changes

### Delete a Project
1. Click "Delete" on a single project
2. Or check multiple projects and use "Delete Selected"
3. Confirm deletion (this cannot be undone)

## Filtering and Searching

### Filter by Status
Use the Status dropdown to show:
- All Projects
- Active Only
- Completed Only
- On Hold Only

### Sort Projects
Sort by:
- Name (A-Z)
- Newest First
- Oldest First
- Budget: High to Low
- Budget: Low to High

### Search
Type in the search box to filter by:
- Project name
- Project description

## Automatic Transaction Tracking

### How It Works
When you create a project and assign labels:
1. All future transactions with those labels are automatically included
2. All existing transactions with those labels (within date range) are included
3. You don't need to manually assign each transaction

### Example
**Project**: "Website Redesign"
**Labels**: "Web Development", "Design", "Hosting"
**Date Range**: Jan 1, 2025 - Mar 31, 2025

Result: Any transaction tagged with those labels between Jan-Mar will automatically appear in this project's financial summary.

## Manual Transaction Allocation (Advanced)

For complex scenarios, you can:
1. Assign a transaction to multiple projects
2. Split a transaction percentage across projects
3. Use Django Admin to create ProjectTransaction records

Example: A £1000 expense could be:
- 60% allocated to Project A (£600)
- 40% allocated to Project B (£400)

## Best Practices

### 1. Use Descriptive Names
✅ "Q4 2025 Marketing Campaign"
❌ "Project 1"

### 2. Set Realistic Budgets
- Review past spending for similar projects
- Add 10-20% buffer for unexpected costs
- Update budget if scope changes

### 3. Leverage Labels
- Create labels that match your business structure
- Use consistent labeling for transactions
- One transaction can have one label, but projects can track multiple labels

### 4. Regular Monitoring
- Check project status weekly
- Review P&L breakdown monthly
- Update status when projects complete

### 5. Archive Completed Projects
- Change status to "Completed" when done
- Keep for historical reference
- Filter to show only Active projects for cleaner view

## Common Use Cases

### Client Projects
- **Project**: "Client ABC - Website"
- **Labels**: "Client ABC", "Web Development"
- **Track**: All work and expenses for this client
- **Benefit**: See profitability per client

### Department Budgets
- **Project**: "IT Department Q1 2025"
- **Labels**: "IT", "Software", "Hardware"
- **Track**: Quarterly department spending
- **Benefit**: Stay within departmental budget

### Marketing Campaigns
- **Project**: "Summer Sale 2025"
- **Labels**: "Advertising", "Social Media", "Email Marketing"
- **Track**: Campaign ROI
- **Benefit**: Calculate cost per acquisition

### Event Planning
- **Project**: "Annual Conference 2025"
- **Labels**: "Events", "Catering", "Venue"
- **Track**: Event budget vs actual
- **Benefit**: Prevent overspending

### Product Development
- **Project**: "Product X Launch"
- **Labels**: "R&D", "Product X", "Marketing"
- **Track**: Total investment to launch
- **Benefit**: Calculate break-even point

## Tips & Tricks

1. **Color Coding**: Use similar colors for related projects (all client projects in blue, internal projects in green)

2. **Naming Convention**: Use prefixes like "CLIENT-", "DEPT-", "CAMPAIGN-" for easier sorting

3. **Quarterly Reviews**: Set end dates for quarters and review all projects at quarter-end

4. **Budget Alerts**: When a project hits 80% budget, review spending and adjust if needed

5. **Label Strategy**: Create a label hierarchy - main categories with sub-labels

## Troubleshooting

### Transactions Not Showing in Project
- Check if transactions have the correct labels assigned
- Verify transaction dates fall within project date range
- Ensure labels are selected in project settings

### Budget Not Calculating Correctly
- Budget tracking only counts outflow (expenses)
- Inflow (income) is separate and shows as "Income"
- Net = Income - Expenses

### Can't Delete Project
- Ensure you're not trying to delete someone else's project
- Check if you have proper permissions
- Try refreshing the page

## Next Features (Planned)
- Export project reports to PDF
- Project templates for quick setup
- Budget forecasting based on spending trends
- Team member assignment
- Project milestones and tasks

---

**Need Help?** Check the main documentation or contact support.

