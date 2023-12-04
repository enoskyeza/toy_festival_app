from django.shortcuts import render, get_object_or_404
from .models import Score, JudgingCriteria

from register.models import Contestant

# Create your views here.

def submit_score(request, contestant_id):
    contestant = get_object_or_404(Contestant, pk=contestant_id)

    # criteria per category
    criteria = JudgingCriteria.objects.all()
    fun_criteria = JudgingCriteria.objects.filter(category__name='Fun')
    function_criteria = JudgingCriteria.objects.filter(category__name='Function')
    engineering_criteria = JudgingCriteria.objects.filter(category__name='Engineering and crafting')
    creativity_criteria = JudgingCriteria.objects.filter(category__name='Creativity & Innovation')

    if request.method == 'POST':
        for criterion in criteria:
            score_value = request.POST.get(f'criteria_{criterion.id}')
            score = Score.objects.create(contestant=contestant, criteria=criterion, score=score_value)
            score.save()
        # Handle score submission
        return render(request, 'scores/submission_successful.html')
    return render(request, 'scores/submit_score.html', {
        'contestant': contestant,
        'fun_criteria' : fun_criteria,
        'function_criteria' : function_criteria,
        'engineering_criteria' : engineering_criteria,
        'creativity_criteria' : creativity_criteria,
        })

def contestant_scores(request, contestant_id):
    contestant = get_object_or_404(Contestant, pk=contestant_id)
    scores = Score.objects.filter(contestant=contestant)
    return render(request, 'scores/contestant_score_details.html', {'contestant': contestant, 'scores': scores})