# current views.py

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

from rest_framework import viewsets, filters, status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action

from decimal import Decimal

from .models import ProgramForm, FormResponse, FormResponseEntry
from .serializers import (
    ProgramFormSerializer,
    ProgramFormStructureSerializer,
    DynamicFormSubmissionSerializer,
    HybridRegistrationSerializer,
)

from .serializers import (
    PaymentSerializer, ContestantSerializer, ParentSerializer,
    ParentCreateUpdateSerializer, TicketSerializer, SchoolSerializer,
    GuardianSerializer,
    ParticipantSerializer,
    ProgramTypeSerializer,
    ProgramSerializer,
    RegistrationSerializer,
    SelfRegistrationSerializer,
    ReceiptSerializer,
    ApprovalSerializer
)
from .utils.filters import (
    GuardianFilter, SchoolFilter, ParticipantFilter, ProgramFilter,
    ProgramTypeFilter, RegistrationFilter, ReceiptFilter, CouponFilter
)
from .models import (
    Parent, Contestant, Payment, Ticket,  School, Guardian,
    Participant, ProgramType, Program, Registration, Receipt, Approval, Coupon
)
from django.db.models import Count, Q, Sum, DecimalField, Value
from django.db.models.functions import Coalesce
from .utils.pagination import CustomPagination
# from .forms import RegistrationForm, ParentForm, ContestantForm, PaymentForm



# API VIEWS.
class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [AllowAny]


# Viewset for Contestant
class ContestantViewSet(viewsets.ModelViewSet):
    queryset = Contestant.objects.select_related('payment_method', 'parent').prefetch_related('scores')
    serializer_class = ContestantSerializer
    permission_classes = [AllowAny]


# Viewset for Parent
class ParentViewSet(viewsets.ModelViewSet):
    queryset = Parent.objects.prefetch_related('contestants').all()
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ParentCreateUpdateSerializer
        return ParentSerializer


class TicketViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A viewset for retrieving tickets.
    """
    queryset = Ticket.objects.select_related('participant')  # Optimize query with related participant
    serializer_class = TicketSerializer
    permission_classes = [AllowAny]

    # def get_queryset(self):
    #     """
    #     Optionally filter tickets based on the current user.
    #     """
    #     # Filter by a specific participant if needed (e.g., based on user context or request data)
    #     return super().get_queryset()


# NEW ARCHITECTURE
class SchoolViewSet(viewsets.ModelViewSet):
    """CRUD for schools"""
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    permission_classes = [AllowAny]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = SchoolFilter
    search_fields = ['name', 'phone_number']
    
    @action(detail=False, methods=['get'], url_path='search')
    def search_schools(self, request):
        """
        Search schools by name for registration modal.
        """
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response([])
        
        schools = School.objects.filter(
            name__icontains=query
        ).order_by('name')[:10]
        
        return Response([
            {
                'id': school.id,
                'name': school.name,
                'address': school.address,
                'phone_number': school.phone_number,
            }
            for school in schools
        ])
    
    @action(detail=False, methods=['post'], url_path='create')
    def create_school(self, request):
        """
        Create a new school from registration modal.
        """
        serializer = SchoolSerializer(data=request.data)
        if serializer.is_valid():
            school = serializer.save()
            return Response({
                'id': school.id,
                'name': school.name,
                'address': school.address,
                'phone_number': school.phone_number,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    ordering_fields = '__all__'
    ordering = ['-created_at']
    # pagination_class = CustomPagination


class GuardianViewSet(viewsets.ModelViewSet):
    """CRUD for guardians"""
    queryset = Guardian.objects.all()
    serializer_class = GuardianSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = GuardianFilter
    search_fields = ['first_name', 'last_name', 'phone_number']
    ordering_fields = '__all__'
    ordering = ['-created_at']
    # pagination_class = CustomPagination


class ParticipantViewSet(viewsets.ModelViewSet):
    """CRUD for participants"""
    queryset = Participant.objects.all().order_by('last_name', 'first_name')
    serializer_class = ParticipantSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class ProgramTypeViewSet(viewsets.ModelViewSet):
    """CRUD for program types/categories"""
    queryset = ProgramType.objects.all().order_by('name')
    serializer_class = ProgramTypeSerializer
    permission_classes = [AllowAny]  # Allow all operations for now


class ProgramViewSet(viewsets.ModelViewSet):
    """CRUD for programs"""
    queryset = Program.objects.select_related(
        'type'
    ).order_by('name')
    serializer_class = ProgramSerializer
    permission_classes = [AllowAny]  # Public access as requested

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ProgramFilter

    search_fields = [
        'name',
    ]

    ordering_fields = '__all__'
    ordering = ['created_at']
    # pagination_class = CustomPagination

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete: mark the program inactive instead of deleting from DB.
        """
        try:
            instance = self.get_object()
            instance.active = False
            instance.save(update_fields=["active"])
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Soft delete program error: {str(e)}")
            return Response({"error": "Failed to delete program"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='dashboard-stats')
    def dashboard_stats(self, request):
        """
        Get dashboard statistics including program counts, enrollments, and form submissions
        """
        try:
            # Get program statistics
            total_programs = Program.objects.count()
            active_programs = Program.objects.filter(active=True).count()
            
            # Get enrollment statistics (registrations)
            total_enrollments = Registration.objects.count()
            
            # Get form submission statistics (with error handling for missing tables)
            try:
                total_form_submissions = FormResponse.objects.count()
            except:
                total_form_submissions = 0
            
            # Get recent programs with enrollment counts
            programs_with_enrollments = Program.objects.annotate(
                enrollments=Count('registrations')
            ).order_by('-created_at')[:10]
            
            # Get recent forms with submission counts (with error handling)
            try:
                forms_with_submissions = ProgramForm.objects.annotate(
                    submissions=Count('responses')
                ).select_related('program').order_by('-id')[:10]
            except:
                forms_with_submissions = []
            
            # Serialize program data
            programs_data = []
            for program in programs_with_enrollments:
                programs_data.append({
                    'id': str(program.id),
                    'title': program.name,
                    'category': program.type.name if program.type else 'General',
                    'status': 'active' if program.active else 'inactive',
                    'enrollments': program.enrollments,
                    'createdAt': program.created_at.strftime('%Y-%m-%d') if program.created_at else None
                })
            
            # Serialize form data
            forms_data = []
            for form in forms_with_submissions:
                try:
                    forms_data.append({
                        'id': f'form-{form.id}',
                        'name': form.title,
                        'programId': str(form.program.id),
                        'programTitle': form.program.name,
                        'fields': form.fields.count() if hasattr(form, 'fields') else 0,
                        'submissions': form.submissions,
                        'createdAt': form.program.created_at.strftime('%Y-%m-%d') if form.program.created_at else None
                    })
                except Exception as e:
                    # Skip forms that cause errors
                    continue
            
            response_data = {
                'stats': {
                    'total_programs': total_programs,
                    'active_programs': active_programs,
                    'total_enrollments': total_enrollments,
                    'total_form_submissions': total_form_submissions
                },
                'programs': programs_data,
                'forms': forms_data
            }
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"Dashboard stats error: {str(e)}")
            return Response(
                {'error': 'Failed to fetch dashboard statistics'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='forms')
    def get_program_forms(self, request, pk=None):
        """
        Get all forms associated with a specific program
        """
        try:
            program = self.get_object()
            forms = ProgramForm.objects.filter(program=program).select_related('program').prefetch_related('fields')

            forms_data = []
            for form in forms:
                # Count form responses/submissions
                try:
                    submissions_count = FormResponse.objects.filter(form=form).count()
                except:
                    submissions_count = 0

                # Count form fields
                try:
                    fields_count = form.fields.count()
                except:
                    fields_count = 0

                forms_data.append({
                    'id': str(form.id),
                    'name': form.title,
                    'description': form.description or '',
                    'fields': fields_count,
                    'submissions': submissions_count,
                    'is_active': form.is_active,
                    'isActive': form.is_active,  # Both formats for compatibility
                    'is_default': form.is_default,
                    'createdAt': form.created_at.isoformat() if hasattr(form, 'created_at') else None,
                    'steps': []  # TODO: Add form steps structure if needed
                })

            return Response(forms_data)

        except Exception as e:
            logger.error(f"Get program forms error: {str(e)}")
            return Response(
                {'error': 'Failed to fetch program forms'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='forms/(?P<form_id>[^/.]+)/set-active')
    def set_active_form(self, request, pk=None, form_id=None):
        """Set a specific form as the active registration form for this program."""
        try:
            program = self.get_object()

            try:
                target_form = ProgramForm.objects.get(id=form_id, program=program)
            except ProgramForm.DoesNotExist:
                return Response(
                    {'error': 'Form not found or does not belong to this program'},
                    status=status.HTTP_404_NOT_FOUND
                )

            with transaction.atomic():
                ProgramForm.objects.filter(program=program).update(is_active=False)
                target_form.is_active = True
                target_form.save(update_fields=['is_active'])

            logger.info("Form '%s' set as active for program '%s'", target_form.title, program.name)

            return Response({
                'success': True,
                'message': f'Form "{target_form.title}" is now the active form for registration',
                'active_form_id': target_form.id,
                'active_form_title': target_form.title
            })

        except Exception as exc:
            logger.error("Set active form error: %s", exc)
            return Response(
                {'error': 'Failed to set active form'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='forms/(?P<form_id>[^/.]+)/inactivate')
    def inactivate_form(self, request, pk=None, form_id=None):
        """Mark the specified form as inactive without activating another."""
        try:
            program = self.get_object()
            try:
                target_form = ProgramForm.objects.get(id=form_id, program=program)
            except ProgramForm.DoesNotExist:
                return Response(
                    {'error': 'Form not found or does not belong to this program'},
                    status=status.HTTP_404_NOT_FOUND
                )

            target_form.is_active = False
            target_form.save(update_fields=['is_active'])

            return Response({
                'success': True,
                'message': f'Form "{target_form.title}" has been inactivated',
                'inactivated_form_id': target_form.id
            })

        except Exception as exc:
            logger.error("Inactivate form error: %s", exc)
            return Response(
                {'error': 'Failed to inactivate form'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='registration-form')
    def get_registration_form(self, request, pk=None):
        """
        Get the complete registration form structure for a program.
        Returns static steps (Guardian + Participant) + dynamic steps from form builder.
        """
        program = self.get_object()
        
        # Get the program's active form for registration
        custom_form = ProgramForm.get_active_form_for_program(program)
        
        # Static steps structure
        static_steps = [
            {
                'step': 1,
                'title': 'Guardian Information',
                'description': 'Parent or guardian details',
                'editable': False,
                'fields': [
                    {'name': 'first_name', 'label': 'First Name', 'type': 'text', 'required': True},
                    {'name': 'last_name', 'label': 'Last Name', 'type': 'text', 'required': True},
                    {'name': 'email', 'label': 'Email Address', 'type': 'email', 'required': False},
                    {'name': 'phone_number', 'label': 'Phone Number', 'type': 'tel', 'required': True},
                    {'name': 'profession', 'label': 'Profession', 'type': 'text', 'required': False},
                    {'name': 'address', 'label': 'Address', 'type': 'text', 'required': False},
                ]
            },
            {
                'step': 2,
                'title': 'Participant Information',
                'description': 'Details of participants to register',
                'editable': False,
                'fields': [
                    {'name': 'participants', 'label': 'Participants', 'type': 'participant_list', 'required': True},
                ]
            }
        ]
        
        # Dynamic steps from custom form
        dynamic_steps = []
        if custom_form:
            fields_by_key = {}
            for field in custom_form.fields.all().order_by('order', 'id'):
                step_key = field.step_key or 'dynamic-step-1'
                fields_by_key.setdefault(step_key, []).append({
                    'name': field.field_name,
                    'label': field.label,
                    'type': field.field_type,
                    'required': field.is_required,
                    'help_text': field.help_text,
                    'options': field.options,
                    'max_length': field.max_length,
                    'min_value': field.min_value,
                    'max_value': field.max_value,
                    'allowed_file_types': field.allowed_file_types,
                    'max_file_size': field.max_file_size,
                    'conditional_logic': field.conditional_logic,
                    'per_participant': True,
                    'column_span': field.column_span,
                })

            metadata = custom_form.step_metadata or []
            if metadata:
                ordered_meta = sorted(
                    [step for step in metadata if isinstance(step, dict)],
                    key=lambda step: step.get('order', 0)
                )
                base_index = len(static_steps)
                for idx, meta in enumerate(ordered_meta, start=1):
                    step_key = meta.get('key') or f'step-{idx}'
                    step_number = base_index + idx
                    dynamic_steps.append({
                        'step': step_number,
                        'title': meta.get('title') or f'Additional Information {idx}',
                        'description': meta.get('description', ''),
                        'editable': True,
                        'per_participant': meta.get('per_participant', True),
                        'fields': fields_by_key.pop(step_key, []),
                        'conditional_logic': meta.get('conditional_logic') or None,
                    })

            # Any remaining steps without metadata fallback to sequential order
            if fields_by_key:
                base_index = len(static_steps) + len(dynamic_steps)
                for offset, (step_key, fields) in enumerate(sorted(fields_by_key.items()), start=1):
                    dynamic_steps.append({
                        'step': base_index + offset,
                        'title': f'Additional Information {base_index + offset - len(static_steps)}',
                        'description': '',
                        'editable': True,
                        'per_participant': True,
                        'fields': fields,
                        'conditional_logic': None,
                    })

        return Response({
            'program': {
                'id': program.id,
                'name': program.name,
                'description': program.description,
                'registration_fee': program.registration_fee,
                'age_min': program.age_min,
                'age_max': program.age_max,
                'category_label': program.category_label,
                'category_options': program.category_options,
            },
            'form_structure': {
                'static_steps': static_steps,
                'dynamic_steps': dynamic_steps,
                'total_steps': len(static_steps) + len(dynamic_steps)
            }
        })

    @action(detail=True, methods=['post'], url_path='register')
    def hybrid_register(self, request, pk=None):
        """
        Handle hybrid registration with static + dynamic form data.
        """
        program = self.get_object()
        
        # Add program to request data
        data = request.data.copy()
        data['program'] = program.id
        
        serializer = HybridRegistrationSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='dashboard')
    def program_dashboard(self, request, pk=None):
        program = self.get_object()

        base_queryset = Registration.objects.select_related(
            'participant',
            'program',
            'program__type',
            'school_at_registration',
            'guardian_at_registration'
        ).select_related('coupon').prefetch_related('receipts', 'approvals').filter(program=program).order_by('-created_at')

        # Map UI date filters (date_from/date_to) to filterset fields (created_from/created_to)
        params = request.query_params.copy()
        if 'date_from' in params and 'created_from' not in params:
            params['created_from'] = params.get('date_from')
        if 'date_to' in params and 'created_to' not in params:
            params['created_to'] = params.get('date_to')

        reg_filter = RegistrationFilter(params, queryset=base_queryset)
        filtered_queryset = reg_filter.qs

        # Overall statistics (unfiltered)
        registrations_for_stats = Registration.objects.filter(program=program)
        status_counts = registrations_for_stats.aggregate(
            total=Count('id', distinct=True),
            paid=Count('id', filter=Q(status=Registration.Status.PAID), distinct=True),
            pending=Count('id', filter=Q(status=Registration.Status.PENDING), distinct=True),
            cancelled=Count('id', filter=Q(status=Registration.Status.CANCELLED), distinct=True),
            refunded=Count('id', filter=Q(status=Registration.Status.REFUNDED), distinct=True),
        )

        expected_revenue = registrations_for_stats.exclude(status=Registration.Status.CANCELLED).aggregate(
            expected=Coalesce(
                Sum('program__registration_fee'),
                Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))
            )
        )['expected'] or Decimal('0')

        collected_revenue = Approval.objects.filter(
            registration__program=program,
            status=Approval.Status.PAID
        ).aggregate(
            total=Coalesce(
                Sum('amount'),
                Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))
            )
        )['total'] or Decimal('0')

        outstanding_revenue = expected_revenue - collected_revenue
        if outstanding_revenue < Decimal('0'):
            outstanding_revenue = Decimal('0')

        # Category breakdown (overall)
        category_counts = registrations_for_stats.values('category_value').annotate(
            count=Count('id')
        )
        option_counts = {item['category_value'] or 'UNCATEGORIZED': item['count'] for item in category_counts}

        breakdown = []
        options = program.category_options or []
        available_categories = list(options)
        for option in options:
            breakdown.append({
                'label': option,
                'value': option,
                'count': option_counts.pop(option, 0)
            })

        for label, count in option_counts.items():
            if label != 'UNCATEGORIZED' and label not in available_categories:
                available_categories.append(label)
            breakdown.append({
                'label': label if label != 'UNCATEGORIZED' else 'Uncategorised',
                'value': None if label == 'UNCATEGORIZED' else label,
                'count': count
            })

        # Paginate filtered registrations
        paginator = CustomPagination()
        page = paginator.paginate_queryset(filtered_queryset, request, view=self)
        serializer = RegistrationSerializer(
            page if page is not None else filtered_queryset,
            many=True,
            context={'request': request}
        )

        if page is not None:
            registrations_payload = paginator.get_paginated_response(serializer.data).data
        else:
            registrations_payload = {
                'pagination': None,
                'results': serializer.data,
            }

        applied_filters = {}
        for key in request.query_params:
            values = request.query_params.getlist(key)
            applied_filters[key] = values if len(values) > 1 else values[0]

        response_payload = {
            'program': ProgramSerializer(program, context={'request': request}).data,
            'stats': {
                'total_registrations': status_counts.get('total', 0),
                'paid_registrations': status_counts.get('paid', 0),
                'pending_registrations': status_counts.get('pending', 0),
                'cancelled_registrations': status_counts.get('cancelled', 0),
                'refunded_registrations': status_counts.get('refunded', 0),
                'expected_revenue': expected_revenue,
                'collected_revenue': collected_revenue,
                'outstanding_revenue': outstanding_revenue,
            },
            'filters': {
                'applied': applied_filters,
                'available': {
                    'statuses': [
                        {'value': choice[0], 'label': choice[1]}
                        for choice in Registration.Status.choices
                    ],
                    'categories': available_categories,
                }
            },
            'category_breakdown': breakdown,
            'registrations': registrations_payload,
        }

        return Response(response_payload)


class RegistrationViewSet(viewsets.ModelViewSet):
    """CRUD for registrations"""
    queryset = Registration.objects.select_related(
        'participant',
        'program',
        'program__type',
        'school_at_registration',
        'guardian_at_registration'
    ).select_related('coupon').prefetch_related('receipts', 'approvals').order_by('-created_at')
    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = RegistrationFilter
    search_fields = ['participant__first_name', 'participant__last_name']
    ordering_fields = '__all__'
    ordering = ['-created_at']
    pagination_class = CustomPagination


class SelfRegistrationAPIView(APIView):
    permission_classes = [AllowAny]
    logger = logging.getLogger(__name__)

    def post(self, request, *args, **kwargs):
        serializer = SelfRegistrationSerializer(data=request.data, context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            self.logger.error(
                "Self‐registration validation failed: %s\nPayload: %s",
                exc.detail,
                request.data,
                exc_info=True,
            )
            return Response({'errors': exc.detail}, status=status.HTTP_400_BAD_REQUEST)

        result = serializer.save()
        return Response(result, status=status.HTTP_201_CREATED)



class ReceiptViewSet(viewsets.ModelViewSet):
    """CRUD for receipts"""
    queryset         = Receipt.objects.select_related(
        'registration__participant',
        'registration__program',
        'issued_by'
    ).all()
    serializer_class = ReceiptSerializer
    permission_classes = [AllowAny]

    filter_backends  = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class  = ReceiptFilter

    search_fields    = [
        'registration__participant__first_name',
        'registration__participant__last_name',
    ]

    ordering_fields  = '__all__'
    ordering         = ['created_at']
    pagination_class = CustomPagination


class ApprovalViewSet(viewsets.ModelViewSet):
    """
    Create payments/refunds on a Registration via Approval records.
    """
    queryset = Approval.objects.all()
    serializer_class = ApprovalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        logger.info(f"ApprovalViewSet.get_queryset - User: {user}, Authenticated: {user.is_authenticated}, Is Staff: {user.is_staff}")
        if user.is_staff:
            return super().get_queryset()
        return Approval.objects.filter(created_by=user)

    def perform_create(self, serializer):
        user = self.request.user
        logger.info(f"ApprovalViewSet.perform_create - User: {user}, Authenticated: {user.is_authenticated}")
        # The serializer.create() will set `created_by` and run post_process()
        serializer.save()


class ProgramFormViewSet(viewsets.ModelViewSet):
    queryset = ProgramForm.objects.all().select_related('program').prefetch_related('fields')
    serializer_class = ProgramFormSerializer
    # Use default pk lookup so /forms/{id}/ works
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        # Use write serializer for creates/updates, read serializer otherwise
        from .serializers import ProgramFormWriteSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return ProgramFormWriteSerializer
        return ProgramFormSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        program_slug = self.kwargs.get('program_slug')
        program_id = self.request.query_params.get('program')
        
        if program_slug:
            return queryset.filter(program__slug=program_slug)
        elif program_id:
            # Support filtering by program ID for flat endpoint access
            return queryset.filter(program_id=program_id)
        
        # Return all forms for flat route access
        return queryset

    @action(detail=True, methods=['get'])
    def structure(self, request, pk=None, program_slug=None, slug=None):
        form = self.get_object()
        serializer = ProgramFormStructureSerializer(form, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='set-active')
    def set_active_flat(self, request, pk=None):
        """
        Set this form as active; deactivate other forms under the same program.
        """
        try:
            form = self.get_object()
            with transaction.atomic():
                ProgramForm.objects.filter(program=form.program).update(is_active=False)
                form.is_active = True
                form.save(update_fields=['is_active'])
            return Response({
                'success': True,
                'message': f'Form "{form.title}" is now active',
                'active_form_id': form.id,
            })
        except Exception as e:
            logger.error(f"Flat set active form error: {str(e)}")
            return Response({'error': 'Failed to set active form'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='inactivate')
    def inactivate_flat(self, request, pk=None):
        """
        Inactivate this specific form without activating another one.
        """
        try:
            form = self.get_object()
            form.is_active = False
            form.save(update_fields=['is_active'])
            return Response({
                'success': True,
                'message': f'Form "{form.title}" has been inactivated',
                'inactivated_form_id': form.id,
            })
        except Exception as e:
            logger.error(f"Flat inactivate form error: {str(e)}")
            return Response({'error': 'Failed to inactivate form'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None, program_slug=None, slug=None):
        form = self.get_object()
        serializer = DynamicFormSubmissionSerializer(data=request.data, form=form)
        serializer.is_valid(raise_exception=True)

        user = request.user if request.user.is_authenticated else None
        response = FormResponse.objects.create(
            form=form,
            submitted_by=user,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", "")
        )

        for field in form.fields.all():
            val = serializer.validated_data.get(field.field_name)
            entry = FormResponseEntry(response=response, field=field)
            if field.field_type == 'file' and val:
                entry.file_upload = val
                entry.value = val.name
            else:
                entry.value = str(val or '')
            entry.save()

        return Response({"message": "Form submitted successfully", "response_id": response.id}, status=201)


# class SelfRegistrationAPIView(APIView):
#     """
#     Public endpoint allowing a guardian to register one or more
#     participants for a program in one go.
#     """
#     permission_classes = [AllowAny]
#
#     def post(self, request, *args, **kwargs):
#         serializer = SelfRegistrationSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         registrations = serializer.save()
#         output = RegistrationSerializer(registrations, many=True).data
#         return Response(output, status=status.HTTP_201_CREATED)

# DJANGO TEMPLATES VIEWS
# def home(request):
#     return render(request, 'reg/home.html')
#
# def success_page(request, contestant_id):
#     contestant = Contestant.objects.get(pk=contestant_id)
#
#     context = {
#         'contestant': contestant,
#     }
#
#     return render(request, 'reg/success.html', context)
#
# class RegistrationView(View):
#     template_name = 'reg/register.html'
#
#     def get(self, request):
#         #Rendering the initial form with the 3 sections
#         form = RegistrationForm()
#         return render(request, self.template_name, {'form': form})
#
#     def post(self, request):
#         form = RegistrationForm(request.POST)
#
#         if form.is_valid():
#             # Create a parent object first
#             parent = Parent.objects.create(
#                 first_name=form.cleaned_data['parent_first_name'],
#                 last_name=form.cleaned_data['parent_last_name'],
#                 proffession=form.cleaned_data['parent_proffession'],
#                 address=form.cleaned_data['parent_address'],
#                 email=form.cleaned_data['parent_email'],
#                 phone_number=form.cleaned_data['parent_phone_number'],
#             )
#
#             # Create a new payment object
#             payment = Payment.objects.create(
#                 pay_type=form.cleaned_data['pay_type'],
#                 pay_status='NOT_PAID'
#             )
#
#             # Create a new contestant object
#             contestant = Contestant.objects.create(
#                 first_name=form.cleaned_data['contestant_first_name'],
#                 last_name=form.cleaned_data['contestant_last_name'],
#                 email=form.cleaned_data['contestant_email'],
#                 age=form.cleaned_data['contestant_age'],
#                 gender=form.cleaned_data['contestant_gender'],
#                 school=form.cleaned_data['contestant_school'],
#                 parent=parent,
#                 payment_status=payment
#             )
#
#             #Redirect to the success page if all successful
#             return redirect('register:success-page', contestant_id=contestant.id)
#
#         #If form is not valid, re-render the form with errors
#         return render(request, self.template_name, {form: form})
#
# def contestant_list_view(request):
#     contestants = Contestant.objects.all()
#
#     return render(request, 'reg/contestant_list.html', {'contestants':contestants})
