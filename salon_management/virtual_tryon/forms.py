from django import forms
from .models import VirtualTryOn, UserFaceAnalysis

class UploadPhotoForm(forms.Form):
    """Form for uploading a photo for face analysis and virtual try-on"""
    photo = forms.ImageField(
        label='Upload your photo',
        help_text='Please upload a front-facing photo with good lighting',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

class HairstyleSelectionForm(forms.Form):
    """Form for selecting hairstyles to try on"""
    hairstyle = forms.ChoiceField(
        label='Select a hairstyle',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        hairstyle_choices = kwargs.pop('hairstyle_choices', [])
        super().__init__(*args, **kwargs)
        self.fields['hairstyle'].choices = hairstyle_choices