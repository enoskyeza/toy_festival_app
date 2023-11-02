from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic.edit import CreateView, UpdateView

from .models import Parent, Child, Payment
from .forms import RegistrationForm, ParentForm, ChildForm, PaymentForm

# Create your views here.

def home(request):
    return render(request, 'reg/home.html')

def success_page(request):
    return render(request, 'reg/success.html')


# class ParentCreateView(CreateView):
#     model = Parent
#     form_class = ParentForm
#     template_name = 'reg/register.html'
#     success_url = reverse_lazy('register:success-page')

class RegistrationView(View):
    template_name = 'register.html'

    def get(self, request):
        #Rendering the initial form with the 3 sections
        form = RegistrationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = RegistrationForm(request.POST)

        if form.is_valid():
            # Create a parent object first
            parent = Parent.objects.create(
                first_name=form.cleaned_data['parent_first_name'],
                last_name=form.cleaned_data['parent_last_name'],
                proffession=form.cleaned_data['parent_proffession'],
                address=form.cleaned_data['parent_address'],
                email=form.cleaned_data['parent_email'],
                phone_number=form.cleaned_data['parent_phone_number'],
            )

            # Create a new payment object
            payment = Payment.objects.create(
                pay_type=form.cleaned_data['pay_type'],
                pay_status=form.cleaned_data['payment_status']
            )

            # Create a new child object
            child = Child.objects.create(
                first_name=form.cleaned_data['child_first_name'],
                last_name=form.cleaned_data['child_last_name'],
                email=form.cleaned_data['child_email'],
                age=form.cleaned_data['child_age'],
                gender=form.cleaned_data['child_gender'],
                school=form.cleaned_data['child_school'],
                parent=parent,
                payment_status=payment
            )

            #Redirect to the success page if all successful
            return redirect('success-page')

        #If form is not valid, re-render the form with errors
        return render(request, self.template_name, {form: form})
