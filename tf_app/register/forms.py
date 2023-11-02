from django import forms

from .models import Parent, Child, Payment


class ParentForm(forms.ModelForm):
    class Meta:
        model = Parent
        fields = ['first_name', 'last_name', 'proffession', 'address', 'email', 'phone_number']

class ChildForm(forms.ModelForm):
    class Meta:
        model = Child
        fields = ['first_name', 'last_name', 'email', 'age', 'gender', 'school']


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['pay_type']

        #set initial value to "NOT_PAID"
        initial = {'pay_status': 'not_paid'}

class RegForm(forms.Form):
    parent = ParentForm()
    child = ChildForm()
    payment = PaymentForm()

# Combined Form for all the three models
class RegistrationForm(forms.Form):
    # Hidden fields to set default values
    parent = forms.CharField(widget=forms.HiddenInput(), required=False)
    payment_status = forms.CharField(widget=forms.HiddenInput(), required=False)

    # Include all fields from ParentForm
    parent_first_name = forms.CharField()
    parent_last_name = forms.CharField()
    parent_proffession = forms.CharField()
    parent_address = forms.CharField()
    parent_email = forms.EmailField()
    parent_phone_number = forms.CharField()

    # Include all fields from ChildForm
    child_first_name = forms.CharField()
    child_last_name = forms.CharField()
    child_email = forms.EmailField()
    child_age = forms.IntegerField()
    child_gender = forms.ChoiceField(choices=Child.ChildGender.choices)
    child_school = forms.CharField()

    # Include the pay_type field from PaymentForm
    pay_type = forms.ChoiceField(choices=Payment.PaymentType.choices)



