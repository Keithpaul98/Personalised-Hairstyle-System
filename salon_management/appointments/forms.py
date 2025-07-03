from django import forms
from .models import Appointment, Rating
from services.models import Service

class AppointmentForm(forms.ModelForm):
    service = forms.ModelChoiceField(
        queryset=Service.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time'
        })
    )

    class Meta:
        model = Appointment
        fields = ['service', 'date', 'time']

class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(
                attrs={'class': 'rating-input'},
                choices=[(5, '★★★★★'), (4, '★★★★'), (3, '★★★'), (2, '★★'), (1, '★')]
            ),
            'comment': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Tell us about your experience...'
                }
            )
        }