from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic.edit import CreateView, UpdateView

from .models import Parent, Contestant, Payment
from .forms import RegistrationForm, ParentForm, ContestantForm, PaymentForm

# Create your views here.

def home(request):
    return render(request, 'reg/home.html')

def success_page(request, contestant_id):
    contestant = Contestant.objects.get(pk=contestant_id)

    context = {
        'contestant': contestant,
    }

    return render(request, 'reg/success.html', context)


# class ParentCreateView(CreateView):
#     model = Parent
#     form_class = ParentForm
#     template_name = 'reg/register.html'
#     success_url = reverse_lazy('register:success-page')

class RegistrationView(View):
    template_name = 'reg/register.html'

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
                pay_status='NOT_PAID'
            )

            # Create a new contestant object
            contestant = Contestant.objects.create(
                first_name=form.cleaned_data['contestant_first_name'],
                last_name=form.cleaned_data['contestant_last_name'],
                email=form.cleaned_data['contestant_email'],
                age=form.cleaned_data['contestant_age'],
                gender=form.cleaned_data['contestant_gender'],
                school=form.cleaned_data['contestant_school'],
                parent=parent,
                payment_status=payment
            )

            #Redirect to the success page if all successful
            return redirect('register:success-page', contestant_id=contestant.id)

        #If form is not valid, re-render the form with errors
        return render(request, self.template_name, {form: form})
