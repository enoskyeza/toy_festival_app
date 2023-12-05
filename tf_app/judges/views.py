from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import JudgeLoginForm

from register.models import Contestant
from .models import Judge

# Create your views here.
# def judge_login(request):
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         password = request.POST.get('password')
#         user = authenticate(username=username, password=password)

#         if user is not None and user.is_judge:
#             login(request, user)
#             return redirect('judging_page')
#         else:
#             # Invalid credentials or user is not a judge, handle accordingly
#             return render(request, 'judges/judge_login.html', {'error_message': 'Invalid login credentials'})
#     else:
#         return render(request, 'judges/judge_login.html')


@login_required
def judge_page(request):
    contestants = Contestant.objects.all()
    judge = Judge.objects.get(user=request.user)


    return render(request, 'judge_page.html', {'judge':judge, 'contenstants':contestants} )



def judge_login(request):
    if request.method == 'POST':
        form = JudgeLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)

            if user is not None and user.is_judge:
                login(request, user)
                return redirect('judging_page')

        # Invalid credentials or user is not a judge, handle accordingly
        error_message = 'Invalid login credentials or user in not a judge'
    else:
        form = JudgeLoginForm()  # Create an instance of the form for GET requests
        error_message = None

    return render(request, 'judges/judge_login.html', {'form': form, 'error_message': error_message})