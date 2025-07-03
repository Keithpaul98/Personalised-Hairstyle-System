from django import forms
from .models import Message, Thread
from django.contrib.auth import get_user_model

User = get_user_model()

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Type your message...'}),
        }

class StartConversationForm(forms.Form):
    # We'll set up the field in __init__
    recipient = forms.ModelChoiceField(queryset=User.objects.none(), label='Recipient')
    content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Type your message...'})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and user.is_staff:
            # Manager: pick a customer
            self.fields['recipient'].queryset = User.objects.filter(is_staff=False)
            self.fields['recipient'].label = 'Customer'
        else:
            # Customer: pick a manager
            self.fields['recipient'].queryset = User.objects.filter(is_staff=True)
            self.fields['recipient'].label = 'Manager'

