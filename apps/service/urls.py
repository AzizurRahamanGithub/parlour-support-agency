from django.urls import path
from .views import UserListAPIView, ServiceDetailAPIView, CreateCheckoutSession, stripe_webhook, PlanListView, ServiceCreateAPIView, ServiceDetailUpdateAPIView


# URL Patterns
urlpatterns = [
    path('list/<int:id>/', ServiceDetailAPIView.as_view(), name='service-detail'),
    path('update/<int:id>/', ServiceDetailUpdateAPIView.as_view(), name='service-update'),
    path('list', UserListAPIView.as_view(), name='user-list'),
    path('plans/', PlanListView.as_view(), name='plan-list'),
    path('create/', ServiceCreateAPIView.as_view(), name='service-create'),
    
    path("create-checkout/", CreateCheckoutSession.as_view()),
path("stripe/webhook/", stripe_webhook),    
]
