import django_filters
from django.db.models import Q

from .models import Judge
from register.models import Contestant
from scores.models import Score

# class ContestantFilter(django_filters.FilterSet):
#     age_category = django_filters.CharFilter(method='filter_by_age_category')

#     class Meta:
#         model = Contestant
#         fields = ['first_name','last_name','age', 'age_category']

#     def filter_by_age_category(self, queryset, name, value):
#         if value in ['young', 'middle', 'old']:  # Check if the value is a valid age category
#             return queryset.filter(age_category=value)
#         return queryset
class ContestantFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(method='filter_by_name')

    class Meta:
        model = Contestant
        fields = ['name']

    def filter_by_name(self, queryset, name, value):
        return queryset.filter(Q(first_name__icontains=value) | Q(last_name__icontains=value))

# class ContestantFilter(django_filters.FilterSet):
#     first_name = django_filters.CharFilter(field_name='first_name', lookup_expr='icontains')
#     last_name = django_filters.CharFilter(field_name='last_name', lookup_expr='icontains')

#     class Meta:
#         model = Contestant
#         fields = ['first_name', 'last_name']


class ContestantGenderFilter(django_filters.FilterSet):

    class Meta:
        model = Contestant
        fields = ['gender']

class ContestantAgeFilter(django_filters.FilterSet):

    class Meta:
        model = Contestant
        fields = ['age_category']