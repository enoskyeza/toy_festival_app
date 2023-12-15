from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.urls import reverse

from .forms import UserLoginForm

from register.models import Contestant

# Create your views here.

@login_required
def index(request):
    contestants = Contestant.objects.all()
    user = request.user
    return render(request, "admin_dashboard/dashboard.html", context={'contestants': contestants,
                                                                      'user':user,})


# def custom_login(request):
#     form = UserLoginForm(request.POST)

#     if request.method == 'POST':
#         username = request.POST.get('username')
#         password = request.POST.get('password')
#         user = authenticate(request, username=username, password=password)
#         if user is not None:
#             login(request, user)
#             return HttpResponseRedirect(reverse('dashboard'))
#         else:
#             return render(request, 'admin_dashboard/login.html', {'error_message': 'Invalid credentials'})
#     else:
#         return render(request, 'admin_dashboard/login.html')

def custom_login(request):
    if request.user.is_authenticated:
        # If the user is already authenticated, redirect them to the dashboard
        return HttpResponseRedirect(reverse('admin_dashboard:dashboard'))

    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return HttpResponseRedirect(reverse('admin_dashboard:dashboard'))
        # If authentication fails or form data is invalid, render the login page with an error message
        return render(request, 'admin_dashboard/login.html', {'form': form, 'error_message': 'Invalid credentials'})
    else:
        form = UserLoginForm()
        return render(request, 'admin_dashboard/login.html', {'form': form})