from django.db.models import Value
from django.db.models.functions import Concat
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, status,  views
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny

from register.models import Contestant
from .models import MainCategory, JudgingCriteria, Score, JudgeComment
from .serializers import (
    MainCategorySerializer,
    JudgingCriteriaSerializer,
    ScoreSerializer,
    JudgeCommentSerializer,
    ContestantDetailSerializer,
    BulkScoreSerializer,
)

class MainCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for retrieving main categories.
    """
    queryset = MainCategory.objects.all()
    serializer_class = MainCategorySerializer
    permission_classes = [AllowAny]


class JudgingCriteriaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for retrieving judging criteria.
    """
    queryset = JudgingCriteria.objects.select_related('category').all()
    serializer_class = JudgingCriteriaSerializer
    permission_classes = [AllowAny]


class ScoreListAPIView(APIView):
    """
    Custom API view to fetch scores with optimized queries and include judge, contestant, and criteria fields.
    """
    def get(self, request, *args, **kwargs):
        # Optimize the queryset by using select_related for judge, contestant, and criteria
        scores = Score.objects.select_related('judge', 'contestant', 'criteria').all()

        # Serialize the queryset with the ScoreSerializer
        serializer = ScoreSerializer(scores, many=True)

        # Return the response with serialized data
        return Response(serializer.data, status=status.HTTP_200_OK)


class ScoreViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing scores.
    """
    queryset = Score.objects.select_related(
        'judge',        # Fetch related Judge object
        'contestant',   # Fetch related Contestant object
        'criteria'      # Fetch related JudgingCriteria object (no main_category)
    )

    serializer_class = ScoreSerializer
    permission_classes = [AllowAny]


# class BulkScoreView(views.APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         serializer = BulkScoreSerializer(data=request.data, many=True)
#         if serializer.is_valid():
#             created, updated = [], []

#             with transaction.atomic():
#                 for item in serializer.validated_data:
#                     if 'id' in item:
#                         try:
#                             score_instance = Score.objects.get(id=item['id'])
#                             updated.append(BulkScoreSerializer().update(score_instance, item))
#                         except Score.DoesNotExist:
#                             raise serializers.ValidationError(f"Score with id {item['id']} does not exist.")
#                     else:
#                         created.append(BulkScoreSerializer().create(item))

#             return Response({
#                 "created": [score.id for score in created],
#                 "updated": [score.id for score in updated],
#             }, status=status.HTTP_200_OK)

#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BulkScoreView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = BulkScoreSerializer(data=request.data, many=True)
        if serializer.is_valid():
            created, updated = [], []

            with transaction.atomic():
                for item in serializer.validated_data:
                    if 'id' in item:
                        try:
                            score_instance = Score.objects.get(id=item['id'])
                            updated.append(BulkScoreSerializer().update(score_instance, item))
                        except Score.DoesNotExist:
                            raise serializers.ValidationError(f"Score with id {item['id']} does not exist.")
                    else:
                        created.append(BulkScoreSerializer().create(item))

            return Response({
                "created": [score.id for score in created],
                "updated": [score.id for score in updated],
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ScoreReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Score.objects.select_related(
        'judge',        # Fetch related Judge object
        'contestant',   # Fetch related Contestant object
        'criteria'      # Fetch related JudgingCriteria object (no main_category)
    )
    serializer_class = ScoreSerializer

    def get_queryset(self):
        """
        Filter scores based on judge if they are not an admin.
        """
        user = self.request.user
        if user.role != "admin":  # Assuming `role` is a field in the user model
            return self.queryset.filter(judge=user)
        return self.queryset


class JudgeCommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing judge comments.
    """
    queryset = JudgeComment.objects.select_related(
        'judge',        # Fetch related Judge object
        'contestant'    # Fetch related Contestant object
    ).all()
    serializer_class = JudgeCommentSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """
        Filter comments based on judge if they are not an admin.
        """
        user = self.request.user
        if user.role != "admin":  # Assuming `role` is a field in the user model
            return self.queryset.filter(judge=user)
        return self.queryset


class ContestantDetailViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A read-only viewset for fetching contestant details with related scores and comments.
    """
    queryset = Contestant.objects.prefetch_related('scores__criteria', 'scores__judge', 'comments__judge').all()
    serializer_class = ContestantDetailSerializer
    permission_classes = [AllowAny]





















# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth.decorators import login_required
# from django.db.models import Sum
# from .models import Score, JudgingCriteria, JudgeComment
# from .forms import CommentForm
#
# from register.models import Contestant
# from judges.models import Judge
# from utils.decorators import judge_required
#
# # Create your views here.
#
# def calc_score(contestant, judge ):
#     categories = ['Fun', 'Function', 'Engineering and crafting', 'Creativity & Innovation']
#     scores = Score.objects.filter(contestant=contestant, judge=judge)
#     total_score = 0
#     sub_scores = {}
#     has_empty_field = {}
#
#     for category in categories:
#         category_scores = Score.objects.filter(contestant=contestant, judge=judge, criteria__category__name=category)
#         category_total_score = category_scores.aggregate(total_sum=Sum('score'))['total_sum'] or 0
#         total_score += category_total_score
#         sub_scores[category] = category_total_score
#
#         # Check for empty fields
#         if len(Score.objects.filter(contestant=contestant, judge=judge, criteria__category__name=category, score=0.00)) > 0:
#             has_empty_field[category] = True
#         else:
#             has_empty_field[category] = False
#
#     return {
#         'contestant': contestant,
#         'scores': scores,
#         'total_score': total_score,
#         'sub_scores': sub_scores,
#         'has_empty_field': has_empty_field,
#     }
#
# @login_required
# @judge_required
# def submit_score(request, contestant_id):
#     contestant = get_object_or_404(Contestant, pk=contestant_id)
#     judge = Judge.objects.get(user=request.user)
#
#     # criteria per category
#     criteria_by_category = {
#         'Fun': JudgingCriteria.objects.filter(category__name='Fun'),
#         'Function': JudgingCriteria.objects.filter(category__name='Function'),
#         'Engineering and crafting': JudgingCriteria.objects.filter(category__name='Engineering and crafting'),
#         'Creativity & Innovation': JudgingCriteria.objects.filter(category__name='Creativity & Innovation'),
#     }
#
#     if request.method == 'POST':
#         for criterion_category, criteria_list in criteria_by_category.items():
#             for criterion in criteria_list:
#                 score_value = request.POST.get(f'criteria_{criterion.id}')
#                 score = Score.objects.create(contestant=contestant, criteria=criterion, score=score_value, judge=judge)
#                 score.save()
#         # Handle score submission
#         return render (request, 'scores/judge_scores.html', calc_score(contestant, judge))
#
#     return render(request, 'scores/submit_score.html', {
#         'contestant': contestant,
#         'criteria_by_category': criteria_by_category,
#     })
#
#
# @login_required
# @judge_required
# def update_score(request, contestant_id):
#     contestant = get_object_or_404(Contestant, pk=contestant_id)
#     judge = Judge.objects.get(user=request.user)
#
#     # Filtering Scores & Criteria by category
#     filter_by_category = {
#         'Fun': [
#             JudgingCriteria.objects.filter(category__name='Fun'),
#             Score.objects.filter(contestant=contestant, judge=judge, criteria__category__name='Fun')
#             ],
#         'Function': [
#             JudgingCriteria.objects.filter(category__name='Function'),
#             Score.objects.filter(contestant=contestant, judge=judge, criteria__category__name='Function')
#             ],
#         'Engineering and crafting': [
#             JudgingCriteria.objects.filter(category__name='Engineering and crafting'),
#             Score.objects.filter(contestant=contestant, judge=judge, criteria__category__name='Engineering and crafting')
#             ],
#         'Creativity & Innovation': [
#             JudgingCriteria.objects.filter(category__name='Creativity & Innovation'),
#             Score.objects.filter(contestant=contestant, judge=judge, criteria__category__name='Creativity & Innovation')
#             ]
#     }
#
#     if request.method == 'POST':
#         for category, criteria_list in filter_by_category.items():
#
#             # Filtering scores according to the category
#             scores = Score.objects.filter(contestant=contestant, judge=judge, criteria__category__name=category)
#
#             for criterion in criteria_list[0]:
#                 for object in scores:
#                     if object.criteria == criterion:
#                         score_value = request.POST.get(f'criteria_{criterion.id}')
#                         object.score = score_value
#                         object.save()
#
#         # Handle score submission
#         return render(request, 'scores/judge_scores.html', calc_score(contestant, judge))
#
#
#     return render(request, 'scores/update_score.html', {
#         'contestant': contestant,
#         'filter_by_category': filter_by_category,
#     })
#
#
# def judge_comment(request, contestant_id):
#     contestant = get_object_or_404(Contestant, pk=contestant_id)
#     judge = get_object_or_404(Judge, user=request.user)
#
#     if request.method == 'POST':
#         form = CommentForm(request.POST)
#         if form.is_valid():
#             comment_obj = form.save(commit=False)
#             comment_obj.contestant = contestant
#             comment_obj.judge = judge
#             comment_obj.save()
#             return redirect('judge:judge-page')  # Change 'judge_detail' to your detail view name
#     else:
#         form = CommentForm()
#
#     return render(request, 'scores/judge_comment.html', {'form': form,
#                                                          'contestant': contestant})
#
#
# @login_required
# def contestant_scores(request, contestant_id):
#     contestant = get_object_or_404(Contestant, pk=contestant_id)
#     judge = get_object_or_404(Judge, user=request.user)
#
#     return render(request, 'scores/judge_scores.html', calc_score(contestant, judge))
#
#
#
# # Event scores calculation functions
# def total_by_judge():
#     contestants = Contestant.objects.all()
#     judges = Judge.objects.all()
#     comments = JudgeComment.objects.all()
#
#     total_by_judge = {}
#
#     total_all_judges = {}
#
#     avg_all_judges = {}
#
#
#     for contestant in contestants:
#         judge_totals = []
#         for judge in judges:
#             scores = Score.objects.filter(contestant=contestant, judge=judge)
#             total_score = scores.aggregate(total_sum=Sum('score'))['total_sum'] or 0
#             judge_totals.append(total_score)
#
#         total_by_judge[contestant.id] = judge_totals
#         total_all_judges[contestant.id] = sum(judge_totals)
#         avg_all_judges[contestant.id] = sum(judge_totals) / len(judge_totals)
#
#     return {'total_by_judge': total_by_judge,
#             'total_all_judges': total_all_judges,
#             'avg_all_judges': avg_all_judges,
#             'contestants': contestants
#             }
#
# @login_required
# def event_scores(request):
#
#     return render(request, 'scores/event_scores.html', total_by_judge())
#
#
#
# # def judge_comment(request, contestant_id):
# #     contestant = get_object_or_404(Contestant, pk=contestant_id)
# #     judge = Judge.objects.get(user=request.user)
#
# #     if request.method == 'POST':
# #         comment_value = request.POST.get(f'comment')
# #         comment_obj = JudgeComment.objects.create(contestant=contestant, judge=judge, comment=comment_value)
# #         comment_obj.save()
# #         # Handle score submission
# #         return redirect ('/judge/?name=contestant.first_name')
#
# #     return render(request, 'scores/judge_comment.html')
#
# # def judge_comment(request, contestant_id):
# #     contestant = get_object_or_404(Contestant, pk=contestant_id)
# #     judge = get_object_or_404(Judge, user=request.user)
#
# #     if request.method == 'POST':
# #         comment_value = request.POST.get('comment')  # Get the comment from POST data
# #         comment_obj = JudgeComment.objects.create(contestant=contestant, judge=judge, comment=comment_value)
# #         comment_obj.save()
#
# #         print(f'The comment is - {comment_value} - by {judge} given to { contestant }')
#
# #         return redirect('judge:judge_page', pk=contestant_id)  # Change 'judge_detail' to your detail view name
#
# #     print(f'View failed')
# #     return render (request, 'scores/judge_comment.html', {'contestant': contestant})
#
#
# # Refactored Overall score view
# from django.db.models import Sum, Avg
# from django.shortcuts import render
# from .models import Contestant, Judge, JudgeComment, Score
#
# @login_required
# def overall_scores(request):
#     # Filter contestants by age category, gender, etc. (customize as needed)
#     age_category = request.GET.get('age_category')
#     gender = request.GET.get('gender')
#
#     contestants = Contestant.objects.all()
#
#     if age_category:
#         # Filter contestants by age category
#         # Assuming the age is stored in a field named 'age' in the Contestant model
#         if age_category == '3-7':
#             contestants = contestants.filter(age__range=(3, 7))
#         elif age_category == '8-12':
#             contestants = contestants.filter(age__range=(8, 12))
#         elif age_category == '13-17':
#             contestants = contestants.filter(age__range=(13, 17))
#
#     if gender:
#         # Filter contestants by gender
#         # Assuming gender is a field in the Contestant model
#         contestants = contestants.filter(gender=gender)
#
#     # Retrieve all judges and judge comments
#     judges = Judge.objects.all()
#     comments = JudgeComment.objects.all()
#
#     contestant_scores = []
#
#     for contestant in contestants:
#         # Fetch scores for each contestant
#         scores = Score.objects.filter(contestant=contestant, judge__in=judges)
#         judge_scores = scores.values_list('judge_id', 'score')
#
#         total_score = scores.aggregate(total_sum=Sum('score'))['total_sum'] or 0
#         avg_score = scores.aggregate(avg_score=Avg('score'))['avg_score'] or 0
#
#         contestant_scores.append({
#             'contestant': contestant,
#             'total_score': total_score,
#             'avg_score': avg_score,
#             'judge_scores': judge_scores,  # Store judge scores for each contestant
#         })
#
#     # Sort contestant scores by highest total score
#     contestant_scores = sorted(contestant_scores, key=lambda x: x['total_score'], reverse=True)
#
#     return render(request, 'scores/overall_scores.html', {
#         'contestant_scores': contestant_scores,
#         'age_category': age_category,
#         'gender': gender,
#     })
