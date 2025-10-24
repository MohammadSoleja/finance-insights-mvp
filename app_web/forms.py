# app_web/forms.py
from django import forms

ALLOWED_EXTS = {".csv", ".xlsx"}

class UploadFileForm(forms.Form):
    file = forms.FileField(
        label="Upload a CSV or Excel file",
        help_text="Accepted formats: .csv, .xlsx (max ~10MB)"
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        name = f.name.lower()
        if not any(name.endswith(ext) for ext in ALLOWED_EXTS):
            raise forms.ValidationError("Please upload a .csv or .xlsx file.")
        # Optional: simple size guard (e.g. 10MB)
        if f.size and f.size > 10 * 1024 * 1024:
            raise forms.ValidationError("File is too large (limit: 10MB).")
        return f
