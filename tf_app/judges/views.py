from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from functools import wraps
from .forms import JudgeLoginForm

from register.models import Contestant
from .models import Judge

# Custom decorator to restrict judge page to judges

def judge_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_judge:  # Assuming is_judge is a boolean field in your Judge model
                return view_func(request, *args, **kwargs)
            else:
                # If the user is logged in but not a judge, handle accordingly
                return redirect('admin_dashboard:dashboard')  # Redirect to an error page or another view
        else:
            # If the user is not logged in, redirect to login page
            return redirect('judge:judge-login')  # Redirect to your login page

    return _wrapped_view


@login_required
@judge_required
def judge_page(request):
    contestants = Contestant.objects.all()
    judge = Judge.objects.get(user=request.user)

    return render(request, 'judges/judge_page.html', {'judge':judge, 'contestants':contestants} )



def judge_login(request):
    if request.method == 'POST':
        form = JudgeLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)

            if user is not None:
                judge_profile = Judge.objects.filter(user=user).first()

                if judge_profile and judge_profile.is_judge:  # Check if the user is a judge
                    login(request, user)
                    return redirect('judge:judge-page')
                login(request, user)
                return redirect('judge:judge-page')

        error_message = 'Invalid login credentials or user in not a judge'
    else:
        form = JudgeLoginForm()  # Create an instance of the form for GET requests
        error_message = None

    return render(request, 'judges/judge_login.html', {'form': form, 'error_message': error_message})