from django.urls import path
from .views import UserListAPIView, ServiceDetailAPIView, CreateCheckoutSession, stripe_webhook, PlanListView, ServiceCreateAPIView, ServiceUpdateAPIView, CategoryAPIView, CountryAPIView, PurchaseAddOnView, UpgradeSubscriptionView, CancelSubscriptionView, MyServiceDetailAPIView


# URL Patterns
urlpatterns = [
    path('list/<int:id>/', ServiceDetailAPIView.as_view(), name='service-detail'),
    path('update/<int:id>/', ServiceUpdateAPIView.as_view(), name='service-update'),
    path("categories/", CategoryAPIView.as_view()),
    path("categories/<int:id>/", CategoryAPIView.as_view()),
    path("locations/", CountryAPIView.as_view()),
    path("locations/<int:id>/", CountryAPIView.as_view()),
    path('list/', UserListAPIView.as_view(), name='user-list'),
    path('plans/', PlanListView.as_view(), name='plan-list'),
    path('create/', ServiceCreateAPIView.as_view(), name='service-create'),
    path("subscription/upgrade/", UpgradeSubscriptionView.as_view(), name="service-upgrade"),
    path("subscription/cancel/", CancelSubscriptionView.as_view(), name="service-cancel"),
    
    path("my-service/", MyServiceDetailAPIView.as_view(), name="my-service"),
    
    path("create-checkout/", CreateCheckoutSession.as_view()),
    path("addon/purchase/", PurchaseAddOnView.as_view(), name="addon-purchase"),
path("stripe/webhook/", stripe_webhook),    
]
