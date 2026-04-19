from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.db.models import Count
from rest_framework import status
from apps.core.response import success_response, failure_response
from .models import Service
from apps.core.pagination import BasePaginatedViewSet, CustomPagination
from .serializers import ServiceSerializer, UserSerializer
from apps.auths.models import SocialMedia, Designation, CustomUser


class UserListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            queryset = CustomUser.objects.select_related(
                "current_plan"
            ).prefetch_related(
                "location"
            ).order_by("-id")

            # -------------------
            # 🔍 FILTER SECTION
            # -------------------
            vip = request.GET.get("vip")
            country = request.GET.get("country")
            city = request.GET.get("city")
            category = request.GET.get("category")

            if vip is not None:
                queryset = queryset.filter(current_plan__is_vip=(vip.lower() == "true"))

            if country:
                queryset = queryset.filter(location__country__iexact=country)

            if city:
                queryset = queryset.filter(location__city__iexact=city)

            if category:
                queryset = queryset.filter(service__category__id=category)

            queryset = queryset.distinct()

            # -------------------
            # 📄 PAGINATION
            # -------------------
            paginator = CustomPagination()
            paginated_queryset = paginator.paginate_queryset(queryset, request)

            serializer = UserSerializer(paginated_queryset, many=True)

            return success_response(
                message="User list fetched successfully",
                data={
                    "results": serializer.data,
                    "pagination": {
                        "count": paginator.page.paginator.count,
                        "page_size": paginator.get_page_size(request),
                        "next": paginator.get_next_link(),
                        "previous": paginator.get_previous_link(),
                    }
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return failure_response(
                message="Failed to fetch users",
                error=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
            
class ServiceDetailAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id):
        try:
            service = Service.objects.select_related(
                "user", "user__current_plan"
            ).prefetch_related(
                "category",
                "locations",
                "prices",
                "user__designation",
                "user__social_media",
            ).get(id=id)

            serializer = ServiceSerializer(service)

            return success_response(
                message="Service fetched successfully",
                data=serializer.data,
                status=status.HTTP_200_OK
            )

        except Service.DoesNotExist:
            return failure_response(
                message="Service not found",
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            return failure_response(
                message="Failed to fetch service",
                error=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )            