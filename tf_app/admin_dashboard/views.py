from django.shortcuts import render

from register.models import Child

# Create your views here.

def index(request):
    students = Child.objects.all()
    return render(request, "admin_dashboard/dashboard.html", context={'students': students})

