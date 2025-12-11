# How to Delete Duplicate Files - 3 Options

## The Problem
4 duplicate files were created in wrong subdirectories and need to be deleted.

## Option 1: Run the Cleanup Script (Easiest)

I've created a script that will check and delete the files for you:

```bash
cd /Users/mohammadsoleja/Documents/GitHub/finance-insights-mvp
./cleanup_duplicates.sh
```

The script will:
- Show you which files exist
- Ask for confirmation before deleting
- Optionally remove empty directories

## Option 2: Delete Manually in Your IDE

Open your IDE file explorer and delete these 4 files:

1. `app_web/static/app_web/css/invoices.css`
2. `app_web/static/app_web/css/clients.css`
3. `app_web/static/app_web/js/invoices.js`
4. `app_web/static/app_web/js/clients.js`

Right-click each file → Delete

## Option 3: Terminal Commands

```bash
cd /Users/mohammadsoleja/Documents/GitHub/finance-insights-mvp

# Delete the 4 duplicate files
rm -f app_web/static/app_web/css/invoices.css
rm -f app_web/static/app_web/css/clients.css
rm -f app_web/static/app_web/js/invoices.js
rm -f app_web/static/app_web/js/clients.js

# Optionally remove the empty directories
rmdir app_web/static/app_web/css 2>/dev/null
rmdir app_web/static/app_web/js 2>/dev/null

echo "✓ Cleanup complete"
```

## Verify After Deletion

After deleting, verify only the correct files remain:

```bash
# These 4 files should exist (correct location):
ls -lh app_web/static/app_web/invoices.css
ls -lh app_web/static/app_web/clients.css
ls -lh app_web/static/app_web/invoices.js
ls -lh app_web/static/app_web/clients.js

# These should NOT exist (duplicates):
ls app_web/static/app_web/css/invoices.css  # Should error
ls app_web/static/app_web/css/clients.css   # Should error
ls app_web/static/app_web/js/invoices.js    # Should error
ls app_web/static/app_web/js/clients.js     # Should error
```

## What to Keep

✅ **KEEP these files** (correct location):
- `app_web/static/app_web/invoices.css` (14 KB)
- `app_web/static/app_web/clients.css` (8 KB)
- `app_web/static/app_web/invoices.js` (12 KB)
- `app_web/static/app_web/clients.js` (5 KB)

❌ **DELETE these files** (wrong location):
- `app_web/static/app_web/css/invoices.css`
- `app_web/static/app_web/css/clients.css`
- `app_web/static/app_web/js/invoices.js`
- `app_web/static/app_web/js/clients.js`

## After Cleanup

Once deleted, you can test the invoicing feature:

```bash
python manage.py runserver
```

Then visit:
- http://127.0.0.1:8000/clients/
- http://127.0.0.1:8000/invoices/

