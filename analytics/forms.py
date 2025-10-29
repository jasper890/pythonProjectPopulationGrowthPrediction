# analytics/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import User, City, PopulationData

# ---------- Login Form ----------
class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Username', 'class': 'form-control'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-control'})
    )

# ---------- Admin User Creation Form (for Superadmin) ----------
class AdminUserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-control'}),
        label="Password"
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'class': 'form-control'}),
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password != password_confirm:
            raise ValidationError("Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])  # Hash the password
        user.role = 'admin'
        user.is_staff = True  # Allows admin panel access if needed
        user.is_active = True
        if commit:
            user.save()
        return user

# ---------- City Creation Form ----------
class CityForm(forms.ModelForm):
    class Meta:
        model = City
        fields = ['city_name', 'region']
        widgets = {
            'city_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City Name'}),
            'region': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Region'}),
        }

# ---------- Population Data Form ----------
class PopulationDataForm(forms.ModelForm):
    class Meta:
        model = PopulationData
        fields = ['city', 'year', 'population_count', 'source']
        widgets = {
            'city': forms.Select(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'population_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'source': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Data Source'}),

        }
