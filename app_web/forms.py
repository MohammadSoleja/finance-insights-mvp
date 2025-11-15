# app_web/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from app_core.models import Transaction, Budget

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


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['name', 'labels', 'amount', 'period', 'start_date', 'end_date', 'active', 'is_recurring', 'recurrence_count']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g., Q4 Marketing, Office Renovation', 'class': 'form-input'}),
            'labels': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
            'amount': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0', 'class': 'form-input'}),
            'period': forms.Select(attrs={'class': 'form-select', 'id': 'id_period'}),
            'start_date': forms.DateInput(attrs={'type': 'text', 'class': 'form-input form-date', 'placeholder': 'Start date', 'id': 'id_start_date'}),
            'end_date': forms.DateInput(attrs={'type': 'text', 'class': 'form-input form-date', 'placeholder': 'End date', 'id': 'id_end_date'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_recurring': forms.CheckboxInput(attrs={'class': 'form-checkbox', 'id': 'id_is_recurring'}),
            'recurrence_count': forms.NumberInput(attrs={'class': 'form-input', 'min': '1', 'max': '12', 'placeholder': '3', 'id': 'id_recurrence_count'}),
        }
        labels = {
            'name': 'Budget Name',
            'labels': 'Track Labels',
            'amount': 'Budget Amount (£)',
            'period': 'Period Type',
            'start_date': 'Start Date',
            'end_date': 'End Date',
            'active': 'Active',
            'is_recurring': 'Make this recurring',
            'recurrence_count': 'Number of periods',
        }
        help_texts = {
            'name': 'Give your budget a descriptive name',
            'labels': 'Select one or more labels to track in this budget',
            'recurrence_count': 'How many future periods to create (e.g., 3 = this month + next 3 months)',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Filter labels to only show user's labels
        if user:
            self.fields['labels'].queryset = user.labels.all().order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        period = cleaned_data.get('period')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        # Validate custom period has dates
        if period == 'custom':
            if not start_date:
                self.add_error('start_date', 'Start date is required for custom period')
            if not end_date:
                self.add_error('end_date', 'End date is required for custom period')
            if start_date and end_date and start_date > end_date:
                self.add_error('end_date', 'End date must be after start date')

        return cleaned_data



class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        # exclude account and user (account should be the current user's account and not editable)
        fields = ['date', 'description', 'amount', 'direction', 'label', 'subcategory']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'text', 'class': 'form-input form-date', 'placeholder': 'YYYY-MM-DD'}),
            'description': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Transaction description'}),
            'amount': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '0.00', 'step': '0.01'}),
            'direction': forms.Select(attrs={'class': 'form-select'}),
            'label': forms.Select(attrs={'class': 'form-select'}),
            'subcategory': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Subcategory (optional)'}),
        }
        labels = {
            'date': 'Date',
            'description': 'Description',
            'amount': 'Amount',
            'direction': 'Type',
            'label': 'Label',
            'subcategory': 'Subcategory',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Filter labels to only show user's labels
        if user:
            self.fields['label'].queryset = user.labels.all().order_by('name')
            self.fields['label'].empty_label = "-- Select Label --"

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
