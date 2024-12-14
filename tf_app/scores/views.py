from django.db.models import Value
from django.db.models.functions import Concat
from django.db import transaction
from django.db.models import Avg, Sum, Prefetch
from django.http import JsonResponse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, status,  views
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import ListAPIView

from django_filters import rest_framework as filters
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination

from register.models import Contestant
from accounts.models import Judge
from .models import MainCategory, JudgingCriteria, Score, JudgeComment
from .serializers import (
    MainCategorySerializer,
    JudgingCriteriaSerializer,
    ScoreSerializer,
    JudgeCommentSerializer,
    ContestantDetailSerializer,
    BulkScoreSerializer,
)

class ResultsPagination(PageNumberPagination):
    page_size = 20  # Number of contestants per page
    page_size_query_param = 'page_size'
    max_page_size = 50

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
                    # Check if a matching record exists
                    existing_score = Score.objects.filter(
                        judge_id=item['judge'],
                        contestant_id=item['contestant'],
                        criteria_id=item['criteria']
                    ).first()

                    if existing_score:
                        # Update the existing record
                        for field, value in item.items():
                            setattr(existing_score, field, value)
                        existing_score.save()
                        updated.append(existing_score)
                    else:
                        # Create a new record
                        created.append(Score.objects.create(**item))

            return Response({
                "created": [score.id for score in created],
                "updated": [score.id for score in updated],
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ScoreReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    queryset = Score.objects.select_related(
        'judge',        # Fetch related Judge object
        'contestant',   # Fetch related Contestant object
        'criteria'      # Fetch related JudgingCriteria object
    )
    serializer_class = ScoreSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['judge', 'contestant']
    ordering_fields = ['criteria', 'score']
    ordering = ['-score']

    # def get_queryset(self):
    #     """
    #     Filter scores based on judge if they are not an admin.
    #     """
    #     user = self.request.user
    #     if user.role != "admin":  # Assuming `role` is a field in the user model
    #         return self.queryset.filter(judge=user)
    #     return self.queryset


# class ScoreReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = Score.objects.select_related(
#         'judge',        # Fetch related Judge object
#         'contestant',   # Fetch related Contestant object
#         'criteria'      # Fetch related JudgingCriteria object (no main_category)
#     )
#     serializer_class = ScoreSerializer
#     filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
#     filterset_fields = ['judge', 'contestant']  # Define fields to filter by
#     ordering_fields = ['criteria', 'score']    # Optional: Allow ordering
#     ordering = ['-score']

#     def get_queryset(self):
#         """
#         Filter scores based on judge if they are not an admin.
#         """
#         user = self.request.user
#         if user.role != "admin":  # Assuming `role` is a field in the user model
#             return self.queryset.filter(judge=user)
#         return self.queryset


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



class ResultsListView(ListAPIView):
    """
    API view to calculate and display contestant results with pagination and filtering.
    """
    permission_classes = [AllowAny]
    pagination_class = ResultsPagination
    queryset = Contestant.objects.filter(payment_status='paid').prefetch_related(
        Prefetch(
            'scores',
            queryset=Score.objects.select_related('criteria', 'criteria__category', 'judge')
        )
    )
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['age_category', 'gender']

    def list(self, request, *args, **kwargs):
        contestants = self.filter_queryset(self.get_queryset())
        paginated_contestants = self.paginate_queryset(contestants)

        # Retrieve all judges
        all_judges = Judge.objects.all()
        judge_names = [judge.username for judge in all_judges]

        # Prepare the result data
        results = []

        for contestant in paginated_contestants:
            # Base contestant info
            contestant_data = {
                "name": f"{contestant.first_name} {contestant.last_name}",
                "identifier": contestant.identifier,
                "age": contestant.age,
                "age_category": contestant.age_category,
                "gender": contestant.gender,
            }

            # Group scores by category and criteria
            categories = {}
            scores = contestant.scores.all()

            for score in scores:
                category_name = score.criteria.category.name
                criteria_name = score.criteria.name

                if category_name not in categories:
                    categories[category_name] = {"criteria": {}, "totals": {"judges": {}, "average": 0}}

                if criteria_name not in categories[category_name]["criteria"]:
                    categories[category_name]["criteria"][criteria_name] = {judge: 0 for judge in judge_names}

                # Add the judge's score
                categories[category_name]["criteria"][criteria_name][score.judge.username] = float(score.score)

                # Add judge totals
                if score.judge.username not in categories[category_name]["totals"]["judges"]:
                    categories[category_name]["totals"]["judges"][score.judge.username] = 0
                categories[category_name]["totals"]["judges"][score.judge.username] += float(score.score)

            # Ensure all judges are represented with default scores
            for category_name, data in categories.items():
                for criteria_name, judge_scores in data["criteria"].items():
                    for judge in judge_names:
                        if judge not in judge_scores:
                            judge_scores[judge] = 0

                # Calculate averages for each criteria and category totals
                category_total = 0
                criteria_count = 0

                for criteria_name, judge_scores in data["criteria"].items():
                    avg_score = sum(judge_scores.values()) / len(judge_scores)
                    data["criteria"][criteria_name] = {
                        "judge_scores": judge_scores,
                        "average": avg_score,
                    }
                    category_total += avg_score
                    criteria_count += 1

                # Total average for the category
                if criteria_count > 0:
                    data["totals"]["average"] = category_total / criteria_count

            # Add overall total across categories
            overall_total = sum(data["totals"]["average"] for data in categories.values())

            # Update contestant data
            contestant_data["categories"] = categories
            contestant_data["overall_total"] = overall_total
            results.append(contestant_data)

        # Sort results by overall_total in descending order
        sorted_results = sorted(results, key=lambda x: x["overall_total"], reverse=True)

        return self.get_paginated_response(sorted_results)

# class ResultsListView(ListAPIView):
#     """
#     API view to calculate and display contestant results with pagination and filtering.
#     """
#     permission_classes=[AllowAny]
#     pagination_class = ResultsPagination
#     queryset = Contestant.objects.filter(payment_status='paid').prefetch_related(
#         Prefetch(
#             'scores',
#             queryset=Score.objects.select_related('criteria', 'criteria__category', 'judge')
#         )
#     )
#     filter_backends = [DjangoFilterBackend]
#     filterset_fields = ['age_category', 'gender']  # Enable filtering by age_category and gender

#     def list(self, request, *args, **kwargs):
#         contestants = self.filter_queryset(self.get_queryset())
#         paginated_contestants = self.paginate_queryset(contestants)

#         # Prepare the result data
#         results = []

#         for contestant in paginated_contestants:
#             # Base contestant info
#             contestant_data = {
#                 "name": f"{contestant.first_name} {contestant.last_name}",
#                 "identifier": contestant.identifier,
#                 "age": contestant.age,
#                 "age_category": contestant.age_category,
#                 "gender": contestant.gender,
#             }

#             # Group scores by category and criteria
#             categories = {}
#             scores = contestant.scores.all()

#             for score in scores:
#                 category_name = score.criteria.category.name
#                 criteria_name = score.criteria.name

#                 if category_name not in categories:
#                     categories[category_name] = {}

#                 if criteria_name not in categories[category_name]:
#                     categories[category_name][criteria_name] = []

#                 # Add the judge's score and name to the criteria
#                 categories[category_name][criteria_name].append({
#                     "judge_name": score.judge.username,
#                     "score": float(score.score)
#                 })

#             # Calculate averages for each criteria
#             for category_name, criteria in categories.items():
#                 for criteria_name, judge_scores in criteria.items():
#                     avg_score = sum(judge["score"] for judge in judge_scores) / len(judge_scores)
#                     categories[category_name][criteria_name] = {
#                         "judge_scores": judge_scores,
#                         "average": avg_score,
#                     }

#             # Add categories to contestant data
#             contestant_data["categories"] = categories
#             results.append(contestant_data)

#         return self.get_paginated_response(results)



class ResultsView(APIView):
    """
    API view to calculate and display contestant results.
    """

    def get(self, request, *args, **kwargs):
        # Fetch only contestants with payment_status set to "paid"
        contestants = Contestant.objects.filter(payment_status='paid')


        # Prepare the result data
        results = []

        for contestant in contestants:
            # Base contestant info
            contestant_data = {
                "name": f"{contestant.first_name} {contestant.last_name}",
                "identifier": contestant.identifier,
                "age": contestant.age,
            }

            # Group scores by category and criteria
            categories = {}
            scores = Score.objects.filter(contestant=contestant).select_related('criteria', 'criteria__category', 'judge')

            for score in scores:
                category_name = score.criteria.category.name
                criteria_name = score.criteria.name

                if category_name not in categories:
                    categories[category_name] = {}

                if criteria_name not in categories[category_name]:
                    categories[category_name][criteria_name] = []

                # Add the judge's score and name to the criteria
                categories[category_name][criteria_name].append({
                    "judge_name": score.judge.username,  # Assuming Judge model has a `username` field
                    "score": float(score.score)
                })

            # Calculate averages for each criteria
            for category_name, criteria in categories.items():
                for criteria_name, judge_scores in criteria.items():
                    avg_score = sum(judge["score"] for judge in judge_scores) / len(judge_scores)
                    categories[category_name][criteria_name] = {
                        "judge_scores": judge_scores,
                        "average": avg_score,
                    }

            # Add categories to contestant data
            contestant_data["categories"] = categories
            results.append(contestant_data)

        # Return results as a JSON response
        return Response({"results": results})



def results_view(request):
    # Fetch all contestants
    contestants = Contestant.objects.all()

    # Prepare the result data
    results = []

    for contestant in contestants:
        # Base contestant info
        contestant_data = {
            "name": f"{contestant.first_name} {contestant.last_name}",
            "identifier": contestant.identifier,
            "age": contestant.age,
        }

        # Group scores by category and criteria
        categories = {}
        scores = Score.objects.filter(contestant=contestant).select_related('criteria', 'criteria__category', 'judge')

        for score in scores:
            category_name = score.criteria.category.name
            criteria_name = score.criteria.name

            if category_name not in categories:
                categories[category_name] = {}

            if criteria_name not in categories[category_name]:
                categories[category_name][criteria_name] = []

            # Add the judge's score and name to the criteria
            categories[category_name][criteria_name].append({
                "judge_name": score.judge.username,  # Assuming Judge model has a `username` field
                "score": float(score.score)
            })

        # Calculate averages for each criteria
        for category_name, criteria in categories.items():
            for criteria_name, judge_scores in criteria.items():
                avg_score = sum(judge["score"] for judge in judge_scores) / len(judge_scores)
                categories[category_name][criteria_name] = {
                    "judge_scores": judge_scores,
                    "average": avg_score,
                }

        # Add categories to contestant data
        contestant_data["categories"] = categories
        results.append(contestant_data)

    return JsonResponse({"results": results}, safe=False)






# def list(self, request, *args, **kwargs):
#     contestants = self.filter_queryset(self.get_queryset())

#     # Prepare the result data
#     results = []

#     # Retrieve all judges
#     all_judges = Judge.objects.all()
#     judge_names = [judge.username for judge in all_judges]

#     for contestant in contestants:
#         # Base contestant info
#         contestant_data = {
#             "name": f"{contestant.first_name} {contestant.last_name}",
#             "identifier": contestant.identifier,
#             "age": contestant.age,
#             "age_category": contestant.age_category,
#             "gender": contestant.gender,
#         }

#         # Group scores by category and criteria
#         categories = {}
#         scores = contestant.scores.all()

#         for score in scores:
#             category_name = score.criteria.category.name
#             criteria_name = score.criteria.name

#             if category_name not in categories:
#                 categories[category_name] = {"criteria": {}, "totals": {"judges": {}, "average": 0}}

#             if criteria_name not in categories[category_name]["criteria"]:
#                 categories[category_name]["criteria"][criteria_name] = {judge: 0 for judge in judge_names}

#             # Add the judge's score
#             categories[category_name]["criteria"][criteria_name][score.judge.username] = float(score.score)

#             # Add judge totals
#             if score.judge.username not in categories[category_name]["totals"]["judges"]:
#                 categories[category_name]["totals"]["judges"][score.judge.username] = 0
#             categories[category_name]["totals"]["judges"][score.judge.username] += float(score.score)

#         # Ensure all judges are represented with default scores
#         for category_name, data in categories.items():
#             for criteria_name, judge_scores in data["criteria"].items():
#                 for judge in judge_names:
#                     if judge not in judge_scores:
#                         judge_scores[judge] = 0

#             # Calculate averages for each criteria and category totals
#             category_total = 0
#             criteria_count = 0

#             for criteria_name, judge_scores in data["criteria"].items():
#                 avg_score = sum(judge_scores.values()) / len(judge_scores)
#                 data["criteria"][criteria_name] = {
#                     "judge_scores": judge_scores,
#                     "average": avg_score,
#                 }
#                 category_total += avg_score
#                 criteria_count += 1

#             # Total average for the category
#             if criteria_count > 0:
#                 data["totals"]["average"] = category_total / criteria_count

#         # Add overall total across categories
#         overall_total = sum(data["totals"]["average"] for data in categories.values())

#         # Update contestant data
#         contestant_data["categories"] = categories
#         contestant_data["overall_total"] = overall_total
#         results.append(contestant_data)

#     # Sort by overall total in descending order
#     sorted_results = sorted(results, key=lambda x: x["overall_total"], reverse=True)

#     # Paginate the sorted results
#     paginated_results = self.paginate_queryset(sorted_results)

#     return self.get_paginated_response(paginated_results)












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
