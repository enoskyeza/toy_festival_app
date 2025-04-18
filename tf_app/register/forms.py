# from django import forms
#
# from .models import Parent, Contestant, Payment
#
#
# class ParentForm(forms.ModelForm):
#     class Meta:
#         model = Parent
#         fields = ['first_name', 'last_name', 'proffession', 'address', 'email', 'phone_number']
#
# class ContestantForm(forms.ModelForm):
#     class Meta:
#         model = Contestant
#         fields = ['first_name', 'last_name', 'email', 'age', 'gender', 'school']
#
#
# class PaymentForm(forms.ModelForm):
#     class Meta:
#         model = Payment
#         fields = ['pay_type']
#
#         #set initial value to "NOT_PAID"
#         initial = {'pay_status': 'not_paid'}
#
# class RegForm(forms.Form):
#     parent = ParentForm()
#     contestant = ContestantForm()
#     payment = PaymentForm()
#
# # Combined Form for all the three models
#
# #Styles widget
# common_attrs = {'class': 'form-control'}
#
# #Radio select widget for choices
# class RadioSelect(forms.widgets.RadioSelect):
#     template_name = 'reg/register.html'
#
#
#
#
# class RegistrationForm(forms.Form):
#     # Hidden fields to set default values
#     parent = forms.CharField(widget=forms.HiddenInput(), required=False)
#     payment_status = forms.CharField(widget=forms.HiddenInput(), required=False)
#
#     # Include all fields from ParentForm
#     parent_first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'First Name'}))
#     parent_last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'Last Name'}))
#     parent_proffession = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'Proffession'}), required=False)
#     parent_address = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'Address'}))
#     parent_email = forms.EmailField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'Email'}), required=False)
#     parent_phone_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'Phone Number'}))
#
#     # Include all fields from ContestantForm
#     contestant_first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'First Name'}))
#     contestant_last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'Last Name'}))
#     contestant_email = forms.EmailField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'Email'}), required=False)
#     contestant_age = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder':'Age'}))
#     contestant_gender = forms.ChoiceField(choices=Contestant.ContestantGender.choices, widget=RadioSelect,)
#     contestant_school = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'School'}), required=False)
#
#     # Include the pay_type field from PaymentForm
#     pay_type = forms.ChoiceField(choices=Payment.PaymentType.choices, widget=RadioSelect,)
#
#     # #Set place holders for all fields
#     # def __init__(self, *args, **kwargs):
#     #     super().__init__(*args, **kwargs)
#
#     #     # Set field placeholders to their respective labels
#     #     for field_name, field in self.fields.items():
#     #         field.widget.attrs['placeholder'] = field.label
#
#
#
#
