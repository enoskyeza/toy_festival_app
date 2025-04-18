from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import (
    PaymentSerializer, ContestantSerializer, ParentSerializer,
    ParentCreateUpdateSerializer, TicketSerializer, SchoolSerializer,
    GuardianSerializer,
    ParticipantSerializer,
    ProgramTypeSerializer,
    ProgramSerializer,
    RegistrationSerializer,
    SelfRegistrationSerializer
)
from .models import (
    Parent, Contestant, Payment, Ticket,  School, Guardian,
    Participant, ProgramType, Program, Registration
)
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
    queryset = School.objects.all().order_by('name')
    serializer_class = SchoolSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class GuardianViewSet(viewsets.ModelViewSet):
    """CRUD for guardians"""
    queryset = Guardian.objects.all().order_by('last_name', 'first_name')
    serializer_class = GuardianSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class ParticipantViewSet(viewsets.ModelViewSet):
    """CRUD for participants"""
    queryset = Participant.objects.all().order_by('last_name', 'first_name')
    serializer_class = ParticipantSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class ProgramTypeViewSet(viewsets.ModelViewSet):
    """CRUD for programs"""
    queryset = ProgramType.objects.all().order_by('name')
    serializer_class = ProgramSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class ProgramViewSet(viewsets.ModelViewSet):
    """CRUD for programs"""
    queryset = Program.objects.all().order_by('name')
    serializer_class = ProgramSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class RegistrationViewSet(viewsets.ModelViewSet):
    """CRUD for registrations"""
    queryset = Registration.objects.all().order_by('-created_at')
    serializer_class = RegistrationSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]



class SelfRegistrationAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = SelfRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_201_CREATED)


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