# app_web/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

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

class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "placeholder": "Username",
            "autocomplete": "username",
        })
        self.fields["password"].widget.attrs.update({
            "placeholder": "Password",
            "autocomplete": "current-password",
        })

# (Optional) If you want placeholders on the signup page too:
class SignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "email")
        widgets = {
            "username": forms.TextInput(attrs={"placeholder": "Username"}),
            "email": forms.EmailInput(attrs={"placeholder": "Email (optional)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"placeholder": "Password"})
        self.fields["password2"].widget.attrs.update({"placeholder": "Confirm password"})