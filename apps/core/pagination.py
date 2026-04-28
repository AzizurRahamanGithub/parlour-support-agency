from rest_framework.pagination import PageNumberPagination

class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'limit'
    page_query_param = 'page'
    max_page_size = 100

    def get_paginated_data(self, data):
        total_count = self.page.paginator.count
        limit = self.get_page_size(self.request)
        import math
        total_pages = math.ceil(total_count / limit) if limit else 1
        current_page = self.page.number

        return {
            "pagination": {
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": current_page,
                "limit": limit,
            },
            "results": data
        }