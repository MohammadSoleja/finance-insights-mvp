# Invoice PDF View - Button Updates

## Changes Made

### ✅ Removed Emojis from Buttons
**Before:**
- 🖨️ Print
- ⬇️ Download PDF

**After:**
- Print
- Download PDF

### ✅ Fixed Download PDF Button Text Color
Added `!important` to ensure white text color is always applied:
```css
.btn-primary {
  background: #2563eb;
  color: white !important;
}

.btn-primary:hover {
  background: #1d4ed8;
  color: white !important;
}
```

## File Modified
- `app_web/templates/app_web/invoice_view.html`

## Result
- Clean, professional buttons without emoji icons
- Download PDF button now has guaranteed white text on blue background
- Better accessibility (no reliance on emoji rendering)
- Consistent with the text-based action buttons used elsewhere in the app

## Testing
Navigate to any invoice PDF view page (`/invoices/<id>/pdf/`) to see:
- ✅ "Print" button (no emoji)
- ✅ "Download PDF" button with white text on blue background (no emoji)

