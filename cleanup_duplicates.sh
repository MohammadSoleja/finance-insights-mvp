#!/bin/bash
# Script to clean up duplicate invoicing files

echo "=== Checking for duplicate files ==="
echo ""

# Files to delete (in wrong subdirectories)
FILES_TO_DELETE=(
  "app_web/static/app_web/css/invoices.css"
  "app_web/static/app_web/css/clients.css"
  "app_web/static/app_web/js/invoices.js"
  "app_web/static/app_web/js/clients.js"
)

# Correct files (should exist)
CORRECT_FILES=(
  "app_web/static/app_web/invoices.css"
  "app_web/static/app_web/clients.css"
  "app_web/static/app_web/invoices.js"
  "app_web/static/app_web/clients.js"
)

echo "Checking correct files (these should exist):"
for file in "${CORRECT_FILES[@]}"; do
  if [ -f "$file" ]; then
    size=$(du -h "$file" | cut -f1)
    echo "  ✓ $file ($size)"
  else
    echo "  ✗ MISSING: $file"
  fi
done

echo ""
echo "Checking duplicate files (these should be deleted):"
for file in "${FILES_TO_DELETE[@]}"; do
  if [ -f "$file" ]; then
    size=$(du -h "$file" | cut -f1)
    echo "  ⚠️  EXISTS: $file ($size)"
  else
    echo "  ✓ Already deleted: $file"
  fi
done

echo ""
echo "Do you want to delete the duplicate files? (y/n)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
  echo ""
  echo "Deleting duplicate files..."
  for file in "${FILES_TO_DELETE[@]}"; do
    if [ -f "$file" ]; then
      rm "$file"
      echo "  ✓ Deleted $file"
    fi
  done

  echo ""
  echo "✅ Cleanup complete!"

  # Check if css and js directories are now empty
  if [ -d "app_web/static/app_web/css" ] && [ -z "$(ls -A app_web/static/app_web/css)" ]; then
    echo "The css/ directory is now empty. Remove it? (y/n)"
    read -r response2
    if [[ "$response2" =~ ^[Yy]$ ]]; then
      rmdir app_web/static/app_web/css
      echo "  ✓ Removed empty css/ directory"
    fi
  fi

  if [ -d "app_web/static/app_web/js" ] && [ -z "$(ls -A app_web/static/app_web/js)" ]; then
    echo "The js/ directory is now empty. Remove it? (y/n)"
    read -r response3
    if [[ "$response3" =~ ^[Yy]$ ]]; then
      rmdir app_web/static/app_web/js
      echo "  ✓ Removed empty js/ directory"
    fi
  fi

else
  echo "Cancelled. No files deleted."
fi

echo ""
echo "Done!"

