from django import forms
from .models import JudgeComment

class CommentForm(forms.ModelForm):
    class Meta:
        model = JudgeComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Add comments...',
                'aria-label': 'judge-comment',
                'rows': 7
            })
        }
