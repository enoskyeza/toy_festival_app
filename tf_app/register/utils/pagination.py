from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class CustomPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "pagination": {
                    "page_size": self.get_page_size(self.request),
                    "total_pages": self.page.paginator.num_pages,
                    "total_records": self.page.paginator.count,
                    "current_page": int(self.get_page_number(self.request, self.django_paginator_class)),
                    "links": self.get_html_context()
                },
                "results": data,
            }
        )

    def paginate_queryset(self, queryset, request, view=None):
        page_size = request.query_params.get("page_size", self.page_size)
        # Remove pagination if pagesize is all
        if page_size == "all":
            return None
        return super().paginate_queryset(queryset, request, view)