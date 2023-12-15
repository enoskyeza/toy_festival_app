from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import JudgeLoginForm
from .models import Judge
from .filters import ContestantFilter, ContestantAgeFilter, ContestantGenderFilter

from register.models import Contestant
from scores.models import Score
from utils.decorators import judge_required


@login_required
@judge_required
def judge_page(request):
    contestants = Contestant.objects.all()

    judge = Judge.objects.get(user=request.user)

    nameFilter = ContestantFilter(request.GET, queryset=contestants)
    genderFilter = ContestantGenderFilter(request.GET, queryset=contestants)
    categoryFilter = ContestantAgeFilter(request.GET, queryset=contestants)

    contestants = nameFilter.qs


    # Check if contestant has scores
    score_by_contestant = {}

    for contestant in contestants:
        has_score = Score.objects.filter(judge=judge, contestant=contestant).exists()
        score_by_contestant[contestant.id] = has_score

    return render(request, 'judges/judge_page.html', {'judge':judge,
                                                      'contestants':contestants,
                                                      'score_by_contestant':score_by_contestant,
                                                      'namefilter':nameFilter,
                                                      'genderfilter':genderFilter,
                                                      'categoryfilter':categoryFilter,} )



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