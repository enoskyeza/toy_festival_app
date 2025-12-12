from django.db.models import Value
from django.db.models.functions import Concat
from django.db import transaction
from django.db.models import Avg, Sum, Prefetch
from django.http import JsonResponse
from decimal import Decimal

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

from accounts.models import Judge
from .models import MainCategory, JudgingCriteria
from .serializers import (
    MainCategorySerializer,
    JudgingCriteriaSerializer,
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


# NEW JUDGING SYSTEM VIEWS (for Participant/Registration architecture)
from register.models import Participant, Registration
from .models import Point, JudgeComment as ParticipantComment


class PointViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing points (scores) in the new architecture.
    """
    queryset = Point.objects.select_related(
        'judge',
        'participant',
        'registration',
        'criteria'
    )
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        # Import here to avoid circular dependency
        from .serializers import PointSerializer, BulkPointSerializer
        return PointSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by registration if provided
        registration_id = self.request.query_params.get('registration_id')
        if registration_id:
            queryset = queryset.filter(registration_id=registration_id)
        
        # Filter by participant if provided
        participant_id = self.request.query_params.get('participant_id')
        if participant_id:
            queryset = queryset.filter(participant_id=participant_id)
        
        # Filter by judge if provided
        judge_id = self.request.query_params.get('judge_id')
        if judge_id:
            queryset = queryset.filter(judge_id=judge_id)
        
        return queryset


class BulkPointView(views.APIView):
    """
    Submit or update multiple scores at once for the new architecture.
    Checks for existing records and updates them if found, or creates new ones.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        # Import here to avoid circular dependency
        from .serializers import BulkPointSerializer
        
        serializer = BulkPointSerializer(data=request.data, many=True)
        if serializer.is_valid():
            created, updated = [], []
            
            with transaction.atomic():
                for item in serializer.validated_data:
                    # Check if a matching record exists
                    filters = {
                        'judge': item['judge'],
                        'participant': item['participant'],
                        'criteria': item['criteria'],
                    }
                    
                    # Add registration to filter if provided
                    if item.get('registration'):
                        filters['registration'] = item['registration']
                    
                    existing_point = Point.objects.filter(**filters).first()
                    
                    if existing_point:
                        # Update the existing record
                        existing_point.score = item['score']
                        if item.get('registration'):
                            existing_point.registration = item['registration']
                        existing_point.save()
                        updated.append(existing_point)
                    else:
                        # Create a new record
                        created.append(Point.objects.create(**item))
            
            return Response({
                "created": [point.id for point in created],
                "updated": [point.id for point in updated],
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ParticipantCommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing comments on participants in the new architecture.
    """
    queryset = ParticipantComment.objects.select_related(
        'judge',
        'participant'
    ).all()
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        # Import here to avoid circular dependency
        from .serializers import ParticipantCommentSerializer
        return ParticipantCommentSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by participant if provided
        participant_id = self.request.query_params.get('participant_id')
        if participant_id:
            queryset = queryset.filter(participant_id=participant_id)
        
        return queryset.order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """Override create to auto-set judge from authenticated user."""
        from accounts.models import Judge
        
        data = request.data.copy()
        
        # Auto-set judge from authenticated user if not provided or invalid
        if request.user.is_authenticated:
            # Get or find the judge by user ID
            judge_id = data.get('judge')
            try:
                # Try to get judge - could be passed as user ID
                judge = Judge.objects.get(id=judge_id)
                data['judge'] = judge.id
            except Judge.DoesNotExist:
                # If user is a judge, use their ID
                try:
                    judge = Judge.objects.get(id=request.user.id)
                    data['judge'] = judge.id
                except Judge.DoesNotExist:
                    return Response(
                        {'error': 'You must be a judge to add comments'},
                        status=status.HTTP_403_FORBIDDEN
                    )
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


# ============================================================================
# PHASE 3: VIEWSETS FOR PHASE 2 MODELS
# ============================================================================

from .models import (
    RubricCategory, Rubric, RubricCriteria, ScoringConfiguration,
    JudgeAssignment, JudgingScore, ConflictOfInterest
)
from .serializers import (
    RubricCategorySerializer, RubricSerializer, RubricCriteriaSerializer,
    RubricForRegistrationSerializer, ScoringConfigurationSerializer,
    JudgeAssignmentSerializer, JudgingScoreSerializer, ConflictOfInterestSerializer
)


class RubricCategoryViewSet(viewsets.ModelViewSet):
    """CRUD for rubric categories."""
    queryset = RubricCategory.objects.all().order_by('order', 'name')
    serializer_class = RubricCategorySerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['order', 'name']


class RubricViewSet(viewsets.ModelViewSet):
    """CRUD for rubrics with nested criteria. Supports category filtering."""
    queryset = Rubric.objects.select_related('program', 'created_by').prefetch_related(
        'criteria__category'
    ).all()
    serializer_class = RubricSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['program', 'is_active', 'category_value']
    ordering_fields = ['created_at', 'name', 'category_value']
    
    @action(detail=False, methods=['get'], url_path='for-registration/(?P<registration_id>[^/.]+)')
    def for_registration(self, request, registration_id=None):
        """
        Get the appropriate rubric for a registration.
        Uses the registration's category_value to find a matching rubric.
        Falls back to a general rubric (category_value=NULL) if no match.
        
        Usage: GET /score/rubrics/for-registration/{registration_id}/
        """
        try:
            registration = Registration.objects.select_related('program').get(id=registration_id)
        except Registration.DoesNotExist:
            return Response(
                {'error': f'Registration with id {registration_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        rubric = Rubric.get_for_registration(registration)
        
        if not rubric:
            return Response(
                {'error': f'No active rubric found for program "{registration.program.name}" '
                          f'with category "{registration.category_value or "general"}"'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = RubricForRegistrationSerializer(rubric)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='for-program/(?P<program_id>[^/.]+)')
    def for_program(self, request, program_id=None):
        """
        Get all active rubrics for a program, organized by category.
        
        Usage: GET /score/rubrics/for-program/{program_id}/
        Returns: List of rubrics (one per category if program has categories)
        """
        from register.models import Program
        
        try:
            program = Program.objects.get(id=program_id)
        except Program.DoesNotExist:
            return Response(
                {'error': f'Program with id {program_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        rubrics = Rubric.objects.filter(
            program=program,
            is_active=True
        ).prefetch_related('criteria__category').order_by('category_value')
        
        serializer = RubricSerializer(rubrics, many=True)
        return Response({
            'program_id': program.id,
            'program_name': program.name,
            'category_label': program.category_label,
            'category_options': program.category_options,
            'rubrics': serializer.data
        })


class RubricCriteriaViewSet(viewsets.ModelViewSet):
    """CRUD for rubric criteria."""
    queryset = RubricCriteria.objects.select_related('rubric', 'category').all()
    serializer_class = RubricCriteriaSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['rubric', 'category']
    ordering_fields = ['order', 'name']


class ScoringConfigurationViewSet(viewsets.ModelViewSet):
    """CRUD for scoring configurations."""
    queryset = ScoringConfiguration.objects.select_related('program').all()
    serializer_class = ScoringConfigurationSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['program', 'calculation_method']


class JudgeAssignmentViewSet(viewsets.ModelViewSet):
    """CRUD for judge assignments."""
    queryset = JudgeAssignment.objects.select_related(
        'program', 'judge', 'assigned_by'
    ).all()
    serializer_class = JudgeAssignmentSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['program', 'judge', 'status', 'category_value']
    ordering_fields = ['assigned_at', 'status']


class JudgingScoreViewSet(viewsets.ModelViewSet):
    """CRUD for judging scores with bulk create support."""
    queryset = JudgingScore.objects.select_related(
        'program', 'registration__participant', 'judge', 'criteria'
    ).all()
    serializer_class = JudgingScoreSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['program', 'judge', 'registration', 'criteria']
    ordering_fields = ['submitted_at', 'raw_score']
    
    @action(detail=False, methods=['post'], url_path='bulk_create')
    def bulk_create(self, request):
        """
        Bulk create or update scores for a registration.
        
        Expected payload:
        {
            "scores": [
                {"registration": 1, "criteria": 1, "raw_score": 8.5},
                {"registration": 1, "criteria": 2, "raw_score": 9.0},
                ...
            ]
        }
        """
        scores_data = request.data.get('scores', [])
        
        if not scores_data:
            return Response(
                {'error': 'No scores provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get judge from authenticated user or request data
        judge = None
        
        # Try authenticated user first
        if request.user.is_authenticated:
            try:
                judge = Judge.objects.get(id=request.user.id)
            except Judge.DoesNotExist:
                pass
        
        # Fallback: try to get judge_id from request data or first score entry
        if not judge:
            judge_id = request.data.get('judge_id') or (scores_data[0].get('judge') if scores_data else None)
            if judge_id:
                try:
                    judge = Judge.objects.get(id=judge_id)
                except Judge.DoesNotExist:
                    pass
        
        if not judge:
            return Response(
                {'error': 'Judge authentication required. Please ensure you are logged in as a judge.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        created_scores = []
        updated_scores = []
        errors = []
        
        with transaction.atomic():
            for score_data in scores_data:
                try:
                    registration_id = score_data.get('registration')
                    criteria_id = score_data.get('criteria')
                    raw_score = score_data.get('raw_score')
                    
                    if not all([registration_id, criteria_id, raw_score is not None]):
                        errors.append({
                            'data': score_data,
                            'error': 'Missing required fields: registration, criteria, raw_score'
                        })
                        continue
                    
                    # Get registration and criteria
                    try:
                        registration = Registration.objects.select_related('program').get(id=registration_id)
                    except Registration.DoesNotExist:
                        errors.append({'data': score_data, 'error': f'Registration {registration_id} not found'})
                        continue
                    
                    # Get rubric for this registration's category
                    rubric = Rubric.get_for_registration(registration)
                    if not rubric:
                        errors.append({
                            'data': score_data, 
                            'error': f'No rubric found for registration {registration_id}'
                        })
                        continue
                    
                    # Validate criteria belongs to this rubric
                    try:
                        criteria = RubricCriteria.objects.get(id=criteria_id, rubric=rubric)
                    except RubricCriteria.DoesNotExist:
                        errors.append({
                            'data': score_data, 
                            'error': f'Criteria {criteria_id} not valid for this registration\'s rubric'
                        })
                        continue
                    
                    # Validate score range
                    if float(raw_score) > float(criteria.max_score):
                        errors.append({
                            'data': score_data,
                            'error': f'Score {raw_score} exceeds max {criteria.max_score} for {criteria.name}'
                        })
                        continue

                    # Ensure Decimal math for model save() computations
                    raw_score_decimal = Decimal(str(raw_score))
                    
                    # Check if score already exists (update) or create new
                    existing_score = JudgingScore.objects.filter(
                        program=registration.program,
                        registration=registration,
                        judge=judge,
                        criteria=criteria
                    ).first()
                    
                    if existing_score:
                        # Update existing score
                        existing_score.raw_score = raw_score_decimal
                        existing_score.max_score = criteria.max_score
                        existing_score.save()
                        updated_scores.append(existing_score.id)
                    else:
                        # Create new score
                        new_score = JudgingScore.objects.create(
                            program=registration.program,
                            registration=registration,
                            judge=judge,
                            criteria=criteria,
                            raw_score=raw_score_decimal,
                            max_score=criteria.max_score
                        )
                        created_scores.append(new_score.id)
                        
                except Exception as e:
                    errors.append({'data': score_data, 'error': str(e)})
        
        return Response({
            'created': created_scores,
            'updated': updated_scores,
            'errors': errors,
            'summary': {
                'created_count': len(created_scores),
                'updated_count': len(updated_scores),
                'error_count': len(errors)
            }
        }, status=status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS)


class ConflictOfInterestViewSet(viewsets.ModelViewSet):
    """CRUD for conflicts of interest."""
    queryset = ConflictOfInterest.objects.select_related(
        'judge', 'participant', 'flagged_by', 'reviewed_by'
    ).all()
    serializer_class = ConflictOfInterestSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['judge', 'participant', 'status', 'relationship_type']
    ordering_fields = ['flagged_at', 'reviewed_at']
