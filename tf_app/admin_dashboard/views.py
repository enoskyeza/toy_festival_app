from django.shortcuts import render

from register.models import Contestant

# Create your views here.

def index(request):
    students = Contestant.objects.all()
    return render(request, "admin_dashboard/dashboard.html", context={'students': students})

