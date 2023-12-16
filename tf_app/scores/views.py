from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import Score, JudgingCriteria, JudgeComment
from .forms import CommentForm

from register.models import Contestant
from judges.models import Judge
from utils.decorators import judge_required

# Create your views here.

def calc_score(contestant, judge ):
    categories = ['Fun', 'Function', 'Engineering and crafting', 'Creativity & Innovation']
    scores = Score.objects.filter(contestant=contestant, judge=judge)
    total_score = 0
    sub_scores = {}
    has_empty_field = {}

    for category in categories:
        category_scores = Score.objects.filter(contestant=contestant, judge=judge, criteria__category__name=category)
        category_total_score = category_scores.aggregate(total_sum=Sum('score'))['total_sum'] or 0
        total_score += category_total_score
        sub_scores[category] = category_total_score

        # Check for empty fields
        if len(Score.objects.filter(contestant=contestant, judge=judge, criteria__category__name=category, score=0.00)) > 0:
            has_empty_field[category] = True
        else:
            has_empty_field[category] = False

    return {
        'contestant': contestant,
        'scores': scores,
        'total_score': total_score,
        'sub_scores': sub_scores,
        'has_empty_field': has_empty_field,
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
    judge = get_object_or_404(Judge, user=request.user)

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment_obj = form.save(commit=False)
            comment_obj.contestant = contestant
            comment_obj.judge = judge
            comment_obj.save()
            return redirect('judge:judge-page')  # Change 'judge_detail' to your detail view name
    else:
        form = CommentForm()

    return render(request, 'scores/judge_comment.html', {'form': form,
                                                         'contestant': contestant})


@login_required
def contestant_scores(request, contestant_id):
    contestant = get_object_or_404(Contestant, pk=contestant_id)
    judge = get_object_or_404(Judge, user=request.user)

    return render(request, 'scores/judge_scores.html', calc_score(contestant, judge))



# Event scores calculation functions
def total_by_judge():
    contestants = Contestant.objects.all()
    judges = Judge.objects.all()
    comments = JudgeComment.all()

    total_by_judge = {}

    total_all_judges = {}

    avg_all_judges = {}


    for contestant in contestants:
        judge_totals = []
        for judge in judges:
            scores = Score.objects.filter(contestant=contestant, judge=judge)
            total_score = scores.aggregate(total_sum=Sum('score'))['total_sum'] or 0
            judge_totals.append(total_score)

        total_by_judge[contestant.id] = judge_totals
        total_all_judges[contestant.id] = sum(judge_totals)
        avg_all_judges[contestant.id] = sum(judge_totals) / len(judge_totals)

    return {'total_by_judge': total_by_judge,
            'total_all_judges': total_all_judges,
            'avg_all_judges': avg_all_judges,
            }

@login_required
def event_scores(request):

    return render(request, 'scores/event_scores.html', total_by_judge())



# def judge_comment(request, contestant_id):
#     contestant = get_object_or_404(Contestant, pk=contestant_id)
#     judge = Judge.objects.get(user=request.user)

#     if request.method == 'POST':
#         comment_value = request.POST.get(f'comment')
#         comment_obj = JudgeComment.objects.create(contestant=contestant, judge=judge, comment=comment_value)
#         comment_obj.save()
#         # Handle score submission
#         return redirect ('/judge/?name=contestant.first_name')

#     return render(request, 'scores/judge_comment.html')

# def judge_comment(request, contestant_id):
#     contestant = get_object_or_404(Contestant, pk=contestant_id)
#     judge = get_object_or_404(Judge, user=request.user)

#     if request.method == 'POST':
#         comment_value = request.POST.get('comment')  # Get the comment from POST data
#         comment_obj = JudgeComment.objects.create(contestant=contestant, judge=judge, comment=comment_value)
#         comment_obj.save()

#         print(f'The comment is - {comment_value} - by {judge} given to { contestant }')

#         return redirect('judge:judge_page', pk=contestant_id)  # Change 'judge_detail' to your detail view name

#     print(f'View failed')
#     return render (request, 'scores/judge_comment.html', {'contestant': contestant})
