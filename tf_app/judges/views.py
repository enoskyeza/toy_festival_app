from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

# Create your views here.
def judge_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)

        if user is not None and user.is_judge:
            login(request, user)
            return redirect('judging_page')
        else:
            # Invalid credentials or user is not a judge, handle accordingly
            return render(request, 'judges/judge_login.html', {'error_message': 'Invalid login credentials'})
    else:
        return render(request, 'judges/judge_login.html')


@login_required
def judging_page(request):
    # Your judging page logic here
    return render(request, 'judging_page.html')