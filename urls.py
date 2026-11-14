from django.urls import path
from .views import (
    MembershipRequestListCreateView,
    MembershipRequestDetailView
)

app_name = 'applications'

urlpatterns = [
    path('requests/', MembershipRequestListCreateView.as_view(), name='request-list-create'),
    path('requests/<int:pk>/', MembershipRequestDetailView.as_view(), name='request-detail'),
]

