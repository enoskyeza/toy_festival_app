from django import forms

class JudgeLoginForm(forms.Form):
    username = forms.CharField(label='Username')
    password = forms.CharField(label='Password', widget=forms.PasswordInput)
    remember_me = forms.BooleanField(label='Remember me', required=False)
    # Add other fields or customizations as needed
