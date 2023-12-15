from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import Score, JudgingCriteria

from register.models import Contestant
from judges.models import Judge
from utils.decorators import judge_required

# Create your views here.

def calc_score(contestant, judge ):
    categories = ['Fun', 'Function', 'Engineering and crafting', 'Creativity & Innovation']
    scores = Score.objects.filter(contestant=contestant, judge=judge)
    total_score = 0
    sub_scores = {}

    for category in categories:
        category_scores = Score.objects.filter(contestant=contestant, judge=judge, criteria__category__name=category)
        category_total_score = category_scores.aggregate(total_sum=Sum('score'))['total_sum'] or 0
        total_score += category_total_score
        sub_scores[category] = category_total_score

    return {
        'contestant': contestant,
        'scores': scores,
        'total_score': total_score,
        'sub_scores': sub_scores,
    }

@login_required
@judge_required
def submit_score(request, contestant_id):
    contestant = get_object_or_404(Contestant, pk=contestant_id)
    judge = Judge.objects.get(user=request.user)

    # criteria per category
    criteria_by_category = {
        'Fun': JudgingCriteria.objects.filter(category__name='Fun'),
        'Function': JudgingCriteria.objects.filter(category__name='Function'),
        'Engineering and crafting': JudgingCriteria.objects.filter(category__name='Engineering and crafting'),
        'Creativity & Innovation': JudgingCriteria.objects.filter(category__name='Creativity & Innovation'),
    }

    if request.method == 'POST':
        for criterion_category, criteria_list in criteria_by_category.items():
            for criterion in criteria_list:
                score_value = request.POST.get(f'criteria_{criterion.id}')
                score = Score.objects.create(contestant=contestant, criteria=criterion, score=score_value, judge=judge)
                score.save()
        # Handle score submission
        return render (request, 'scores/judge_scores.html', calc_score(contestant, judge))

    return render(request, 'scores/submit_score.html', {
        'contestant': contestant,
        'criteria_by_category': criteria_by_category,
    })


@login_required
@judge_required
def update_score(request, contestant_id):
    contestant = get_object_or_404(Contestant, pk=contestant_id)
    judge = Judge.objects.get(user=request.user)

    # Filtering Scores & Criteria by category
    filter_by_category = {
        'Fun': [
            JudgingCriteria.objects.filter(category__name='Fun'),
            Score.objects.filter(contestant=contestant, judge=judge, criteria__category__name='Fun')
            ],
        'Function': [
            JudgingCriteria.objects.filter(category__name='Function'),
            Score.objects.filter(contestant=contestant, judge=judge, criteria__category__name='Function')
            ],
        'Engineering and crafting': [
            JudgingCriteria.objects.filter(category__name='Engineering and crafting'),
            Score.objects.filter(contestant=contestant, judge=judge, criteria__category__name='Engineering and crafting')
            ],
        'Creativity & Innovation': [
            JudgingCriteria.objects.filter(category__name='Creativity & Innovation'),
            Score.objects.filter(contestant=contestant, judge=judge, criteria__category__name='Creativity & Innovation')
            ]
    }

    if request.method == 'POST':
        for category, criteria_list in filter_by_category.items():

            # Filtering scores according to the category
            scores = Score.objects.filter(contestant=contestant, judge=judge, criteria__category__name=category)

            for criterion in criteria_list[0]:
                for object in scores:
                    if object.criteria == criterion:
                        score_value = request.POST.get(f'criteria_{criterion.id}')
                        object.score = score_value
                        object.save()

        # Handle score submission
        return render(request, 'scores/judge_scores.html', calc_score(contestant, judge))


    return render(request, 'scores/update_score.html', {
        'contestant': contestant,
        'filter_by_category': filter_by_category,
    })

def judge_comment(request, contestant_id):
    contestant = get_object_or_404(Contestant, pk=contestant_id)

    return render(request, 'scores/judge_comment.html', {'contestant': contestant} )

@login_required
def contestant_scores(request, contestant_id):
    contestant = get_object_or_404(Contestant, pk=contestant_id)
    scores = Score.objects.filter(contestant=contestant)
    return render(request, 'scores/judge_scores.html', {'contestant': contestant, 'scores': scores})

