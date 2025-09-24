from rest_framework import viewsets, filters
from rest_framework.pagination import LimitOffsetPagination
from .models import Media
from .serializers import MediaSerializer

class MediaViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only API for browsing media with search and pagination"""
    queryset = Media.objects.filter(is_deleted=False)
    serializer_class = MediaSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['caption']
    ordering_fields = ['created_at']
    pagination_class = LimitOffsetPagination