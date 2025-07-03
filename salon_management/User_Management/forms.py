from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from services.models import ServiceCategory, Service

class CustomerRegistrationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'address', 'phone_number', 'password1', 'password2']
        labels = {
            'email': 'Email',
            'address': 'Address',
            'phone_number': 'Phone Number'
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'})
        }

class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'address', 'phone_number']
        labels = {
            'email': 'Email',
            'address': 'Address',
            'phone_number': 'Phone Number'
            
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
    
        }

class AdminRegistrationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']
        labels = {
            'email': 'Email'
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'})
        }

from django.contrib.auth.forms import AuthenticationForm
class CustomLoginForm(AuthenticationForm): 
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'})) 
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

class StaffForm(UserCreationForm):
    expertise = forms.CharField(max_length=150, required=True)
    rating = forms.DecimalField(max_digits=3, decimal_places=2, required=True)

    class Meta:
        model = CustomUser
        fields = ['first_name','last_name','username', 'email', 'expertise', 'rating', 'password1', 'password2']
    
    def cleanpassword2(self):
        password1 = self.cleaned_data
        password2 = self.cleaned_data
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match')
        return password2

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'category', 'description', 'price', 'duration_minutes', 'image', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control-file'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'duration_minutes': 'Duration (minutes)',
            'is_active': 'Active',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['duration_minutes'].help_text = 'Format: HH:MM'
        self.fields['category'].queryset = ServiceCategory.objects.all()

class CustomLoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Enter your username',
                'id': 'username'
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Enter your password',
                'id': 'password'
            }
        )
    )