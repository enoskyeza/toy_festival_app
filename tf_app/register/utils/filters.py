import django_filters
from register.models import (
    School, Guardian, Participant,
    ProgramType, Program, Registration,
    Receipt, Coupon
)

class CreatedAtFilter(django_filters.FilterSet):
    created_from = django_filters.DateFilter(method='filter_created_from')
    created_to   = django_filters.DateFilter(field_name='created_at',
                                             lookup_expr='date__lte')

    def filter_created_from(self, queryset, name, value):
        """
        - If the client also passed ?created_to=…, we want created_at >= value
          (and let the created_to filter apply the <= side).
        - If they only passed ?created_from=…, we want only that exact date.
        """
        if self.data.get('created_to'):
            return queryset.filter(created_at__date__gte=value)
        return queryset.filter(created_at__date=value)

    class Meta:
        model  = None
        fields = []


class GuardianFilter(CreatedAtFilter):
    class Meta(CreatedAtFilter.Meta):
        model = Guardian
        # No extra exact lookups needed here; created_from/to cover date filter.
        fields = []


class SchoolFilter(CreatedAtFilter):
    class Meta(CreatedAtFilter.Meta):
        model = School
        fields = []


class ParticipantFilter(CreatedAtFilter):
    current_school = django_filters.NumberFilter(field_name='current_school_id', lookup_expr='exact')
    gender         = django_filters.ChoiceFilter(choices=Participant.Gender.choices)
    age            = django_filters.NumberFilter()
    guardian       = django_filters.NumberFilter(field_name='guardians__id', lookup_expr='exact')

    class Meta(CreatedAtFilter.Meta):
        model = Participant
        fields = [
            'current_school',
            'gender',
            'age',
            'guardian',
        ]


class ProgramTypeFilter(CreatedAtFilter):
    class Meta(CreatedAtFilter.Meta):
        model = ProgramType
        fields = []


class ProgramFilter(CreatedAtFilter):
    type = django_filters.NumberFilter(field_name='type_id', lookup_expr='exact')
    active = django_filters.BooleanFilter(field_name='active', lookup_expr='exact')

    class Meta(CreatedAtFilter.Meta):
        model = Program
        fields = ["type", 'active']


class RegistrationFilter(CreatedAtFilter):
    participant   = django_filters.NumberFilter(field_name='participant_id', lookup_expr='exact')
    status        = django_filters.ChoiceFilter(choices=Registration.Status.choices)
    program       = django_filters.NumberFilter(field_name='program_id', lookup_expr='exact')
    program__type = django_filters.NumberFilter(field_name='program__type_id', lookup_expr='exact')

    class Meta(CreatedAtFilter.Meta):
        model = Registration
        fields = [
            "status",
            "program",
            "program__type",
            "participant",
        ]


class ReceiptFilter(CreatedAtFilter):
    status       = django_filters.ChoiceFilter(choices=Receipt.Status.choices)
    registration = django_filters.NumberFilter(field_name='registration_id', lookup_expr='exact')
    participant  = django_filters.NumberFilter(field_name='registration__participant_id', lookup_expr='exact')
    program      = django_filters.NumberFilter(field_name='registration__program_id', lookup_expr='exact')

    class Meta(CreatedAtFilter.Meta):
        model  = Receipt
        fields = [
            'status',
            'registration',
            'participant',
            'program',
        ]


class CouponFilter(CreatedAtFilter):
    registration__participant__first_name = django_filters.CharFilter(
        field_name="registration__participant__first_name", lookup_expr="icontains"
    )
    registration__participant__last_name  = django_filters.CharFilter(
        field_name="registration__participant__last_name",  lookup_expr="icontains"
    )
    status = django_filters.ChoiceFilter(choices=Coupon.Status.choices)

    class Meta(CreatedAtFilter.Meta):
        model = Participant
        # No extra exact lookups needed here; created_from/to cover date filter.
        fields = []


