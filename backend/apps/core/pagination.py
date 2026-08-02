from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Page-number pagination with envelope {count, next, previous, results} (D-09)."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100
