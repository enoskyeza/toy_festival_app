from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect
from django.urls import reverse

from register.models import Contestant

# Create your views here.

@login_required
def index(request):
    students = Contestant.objects.all()
    return render(request, "admin_dashboard/dashboard.html", context={'students': students})

def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse('dashboard'))
        else:
            return render(request, 'admin_dashboard/login.html', {'error_message': 'Invalid credentials'})
    else:
        return render(request, 'admin_dashboard/login.html')