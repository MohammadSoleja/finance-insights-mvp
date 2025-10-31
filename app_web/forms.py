# app_web/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from app_core.models import Transaction

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


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        # exclude account and user (account should be the current user's account and not editable)
        fields = ['date', 'description', 'amount', 'direction', 'category', 'subcategory']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'text', 'class': 'form-input form-date', 'placeholder': 'YYYY-MM-DD'}),
            'description': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Description'}),
            'amount': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'placeholder': 'Amount'}),
            'direction': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Category'}),
            'subcategory': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Subcategory'}),
        }

    def clean_description(self):
        d = self.cleaned_data.get('description', '').strip()
        if not d:
            raise forms.ValidationError('Description is required.')
        return d

    def clean_amount(self):
        a = self.cleaned_data.get('amount')
        if a is None:
            raise forms.ValidationError('Amount is required.')
        return a

    def clean(self):
        cleaned = super().clean()
        # additional cross-field validation if needed
        return cleaned
