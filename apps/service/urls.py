from django.urls import path
from .views import UserListAPIView, ServiceDetailAPIView, CreateCheckoutSession, stripe_webhook, PlanListView, ServiceCreateAPIView, ServiceUpdateAPIView, CategoryAPIView, CountryAPIView


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
    
    path("create-checkout/", CreateCheckoutSession.as_view()),
path("stripe/webhook/", stripe_webhook),    
]
