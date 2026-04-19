from django.urls import path
from .views import UserListAPIView, ServiceDetailAPIView


# URL Patterns
urlpatterns = [
    path('list/<int:id>/', ServiceDetailAPIView.as_view(), name='service-detail'),
    path('list', UserListAPIView.as_view(), name='user-list'),
]
