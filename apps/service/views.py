from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Count
from rest_framework import status
from apps.core.response import success_response, failure_response
from .models import Service, Subscription, Plan, Category, Country, City
from apps.core.pagination import BasePaginatedViewSet, CustomPagination
from .serializers import ServiceSerializer, UserSerializer, PlanSerializer, ServiceLocation, CategorySerializer, CountrySerializer, CitySerializer
from apps.auths.models import SocialMedia, CustomUser
from django.utils import timezone
import stripe            
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from datetime import datetime
from django.utils import timezone
from datetime import datetime, timezone as dt_timezone
from django.utils.timezone import now
stripe.api_key = settings.STRIPE_SECRET_KEY


class UserListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            queryset = CustomUser.objects.filter(
                is_active=True,
                current_plan__isnull=False,
            ).select_related(
                "current_plan",
                "current_plan__plan"
            ).prefetch_related(
                "service_set",
                "service_set__category",
                "service_set__subcategory",
                "service_set__country",
                "service_set__city",
            ).order_by("-id")

            plan_name = request.GET.get("plan_name")
            country   = request.GET.get("country")
            city      = request.GET.get("city")
            category  = request.GET.get("category")

            if plan_name:
                queryset = queryset.filter(current_plan__plan__plan_name__iexact=plan_name)
            if country:
                queryset = queryset.filter(service__country__name__iexact=country)
            if city:
                queryset = queryset.filter(service__city__name__iexact=city)
            if category:
                queryset = queryset.filter(service__category__id=category)

            queryset = queryset.distinct()

            # ── Filter lists ─────────────────────────────────────
            countries = list(Country.objects.values_list("name", flat=True).order_by("name"))
            cities    = list(City.objects.values_list("name", flat=True).order_by("name"))

            # category + subcategory list
            category_list = []
            for cat in Category.objects.prefetch_related('subcategories').all():
                category_list.append({
                    "id": cat.id,
                    "name": cat.name,
                    "subcategories": [
                        {"id": sub.id, "name": sub.name}
                        for sub in cat.subcategories.all()
                    ]
                })

            # ── Pagination ────────────────────────────────────────
            paginator = CustomPagination()
            paginated_queryset = paginator.paginate_queryset(queryset, request)
            serializer = UserSerializer(paginated_queryset, many=True)

            return success_response(
                message="User list fetched successfully",
                data={
                    "filters": {
                        "countries": countries,
                        "cities": cities,
                        "categories": category_list,
                    },
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
    
class ServiceCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            subscription = Subscription.objects.filter(
                user=request.user,
                is_active=True,
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gt=timezone.now())
            ).select_related("plan").first()

            if not subscription:
                return failure_response(
                    message="You need an active subscription to create a service.",
                    status=status.HTTP_403_FORBIDDEN
                )

            plan             = subscription.plan
            current_listings = Service.objects.filter(user=request.user).count()

            if current_listings >= plan.max_listings:
                existing_service = Service.objects.filter(user=request.user).first()
                return failure_response(
                    message=f"Your {plan.plan_name} plan allows maximum {plan.max_listings} listing(s). Please update your existing service.",
                    error={"service_id": existing_service.id if existing_service else None},
                    status=status.HTTP_403_FORBIDDEN
                )

            requested_subcategories = request.data.get("subcategory", [])
            requested_cities        = request.data.get("city", [])  # ✅ city wise
            requested_images        = request.data.get("images", [])

            errors = {}
            if requested_subcategories and len(requested_subcategories) > plan.max_sub_categories:
                errors["subcategory"] = f"Your {plan.plan_name} plan allows maximum {plan.max_sub_categories} subcategory(s)."
            if requested_cities and len(requested_cities) > plan.max_locations:  # ✅ city count
                errors["city"] = f"Your {plan.plan_name} plan allows maximum {plan.max_locations} city(s)."
            if requested_images and len(requested_images) > plan.max_images:
                errors["images"] = f"Your {plan.plan_name} plan allows maximum {plan.max_images} image(s)."

            if errors:
                return failure_response(
                    message="Plan limit exceeded.",
                    error=errors,
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = ServiceSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=request.user, is_published=False)
                return success_response(
                    message="Service created successfully. Waiting for admin approval.",
                    data=serializer.data,
                    status=status.HTTP_201_CREATED
                )

            return failure_response(
                message="Validation error",
                error=serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            return failure_response(
                message="Failed to create service",
                error=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )        
                     
class ServiceDetailAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id):
        try:
            service = Service.objects.select_related(
                "user",
                "user__current_plan",
                "user__current_plan__plan"
            ).prefetch_related(
                "category",
                "subcategory",        # ✅
                "city",               # ✅
                "country",            # ✅
                "prices",
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

class CategoryAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id=None):
        try:
            # Single category
            if id:
                category = Category.objects.prefetch_related(
                    "subcategories"
                ).get(id=id)

                serializer = CategorySerializer(category)

                return success_response(
                    message="Category fetched successfully",
                    data=serializer.data,
                    status=status.HTTP_200_OK
                )

            # All categories
            categories = Category.objects.prefetch_related(
                "subcategories"
            ).all().order_by("-created_at")

            serializer = CategorySerializer(categories, many=True)

            return success_response(
                message="Categories fetched successfully",
                data=serializer.data,
                status=status.HTTP_200_OK
            )

        except Category.DoesNotExist:
            return failure_response(
                message="Category not found",
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            return failure_response(
                message="Failed to fetch category",
                error=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class CountryAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id=None):
        try:
            # Single country with cities
            if id:
                country = Country.objects.prefetch_related("cities").get(id=id)
                serializer = CountrySerializer(country)
                return success_response(
                    message="Country fetched successfully",
                    data=serializer.data,
                    status=status.HTTP_200_OK
                )

            # Search by name
            search = request.query_params.get("search", "").strip()
            countries = Country.objects.prefetch_related("cities").order_by("name")

            if search:
                countries = countries.filter(name__icontains=search)

            data = [
                {
                    "id": country.id,
                    "name": country.name,
                    "cities": [
                        {"id": city.id, "name": city.name}
                        for city in country.cities.all()
                    ],
                }
                for country in countries
            ]

            return success_response(
                message="Countries fetched successfully",
                data=data,
                status=status.HTTP_200_OK
            )

        except Country.DoesNotExist:
            return failure_response(
                message="Country not found",
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return failure_response(
                message="Failed to fetch country",
                error=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ServiceUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id):
        try:
            service = Service.objects.get(id=id, user=request.user)

            subscription = Subscription.objects.filter(
                user=request.user,
                is_active=True,
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gt=timezone.now())
            ).select_related("plan").first()

            if not subscription:
                return failure_response(
                    message="You need an active subscription to update a service.",
                    status=status.HTTP_403_FORBIDDEN
                )

            plan = subscription.plan

            requested_subcategories = request.data.get("subcategory", [])
            requested_cities        = request.data.get("city", [])
            requested_images        = request.data.get("images", [])

            errors = {}
            if requested_subcategories and len(requested_subcategories) > plan.max_sub_categories:
                errors["subcategory"] = f"Your {plan.plan_name} plan allows maximum {plan.max_sub_categories} subcategory(s)."
            if requested_cities and len(requested_cities) > plan.max_locations:
                errors["city"] = f"Your {plan.plan_name} plan allows maximum {plan.max_locations} city(s)."
            if requested_images and len(requested_images) > plan.max_images:
                errors["images"] = f"Your {plan.plan_name} plan allows maximum {plan.max_images} image(s)."

            if errors:
                return failure_response(
                    message="Plan limit exceeded.",
                    error=errors,
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = ServiceSerializer(service, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return success_response(
                    message="Service updated successfully.",
                    data=serializer.data,
                    status=status.HTTP_200_OK
                )

            return failure_response(
                message="Validation error",
                error=serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        except Service.DoesNotExist:
            return failure_response(
                message="Service not found.",
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return failure_response(
                message="Failed to update service",
                error=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    
            
class PlanListView(APIView):
    
    def get(self, request):
        try:
            plans = Plan.objects.all()
            serializer = PlanSerializer(plans, many=True)
            return success_response("", serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return failure_response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            

class CreateCheckoutSession(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan_id = request.data.get("plan_id")

        try:
            plan = Plan.objects.get(id=plan_id)
        except Plan.DoesNotExist:
            return failure_response("Invalid plan")

        # Check if user already has an active subscription
        active_subscription = Subscription.objects.filter(
            user=request.user,
            is_active=True,
            status="active",
            end_date__gt=now()
        ).exists()

        if active_subscription:
            return failure_response("You already have an active subscription.")

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=request.user.email,
            line_items=[
                {
                    "price": plan.stripe_price_id,
                    "quantity": 1,
                }
            ],
            success_url="http://localhost:3000/success",
            cancel_url="http://localhost:3000/cancel",
        )

        return success_response(
            "Checkout created",
            {"checkout_url": session.url}
        )
        
        
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    if not sig_header:
        print("❌ Missing Stripe signature")
        return HttpResponse(status=400)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        print("❌ Webhook verification failed:", e)
        return HttpResponse(status=400)

    print("✅ EVENT:", event["type"])

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        try:
            email = session["customer_email"] or session["customer_details"]["email"]
            stripe_sub_id = session["subscription"]
            stripe_customer_id = session["customer"]

            if not email:
                print("❌ No email in session")
                return HttpResponse(status=200)

            user = CustomUser.objects.filter(email=email).first()
            if not user:
                print("❌ User not found:", email)
                return HttpResponse(status=200)

            line_items = stripe.checkout.Session.list_line_items(session["id"])
            price_id = line_items.data[0].price.id

            plan = Plan.objects.filter(stripe_price_id=price_id).first()
            if not plan:
                print("❌ Plan not found for price_id:", price_id)
                return HttpResponse(status=200)

            if not Subscription.objects.filter(stripe_subscription_id=stripe_sub_id).exists():
                
                stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)

                item = stripe_sub["items"]["data"][0]

                start_date = datetime.fromtimestamp(item["current_period_start"], tz=dt_timezone.utc)
                end_date   = datetime.fromtimestamp(item["current_period_end"], tz=dt_timezone.utc)

                subscription = Subscription.objects.create(
                    user=user,
                    plan=plan,
                    stripe_customer_id=stripe_customer_id,
                    stripe_subscription_id=stripe_sub_id,
                    is_active=True,
                    status="active",
                    start_date=start_date, 
                    end_date=end_date,      
                )
                user.current_plan = subscription
                user.save()
                print("🎉 SUBSCRIPTION CREATED for", email)

        except Exception as e:
            print("🔥 INTERNAL ERROR:", e)
            import traceback
            traceback.print_exc()
            return HttpResponse(status=500)

    return HttpResponse(status=200)