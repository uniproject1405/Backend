
from django.urls import path
from .views import (
    MembershipRequestCreateView,
    MembershipRequestListView,
    MembershipRequestStatusView,
    MembershipRequestCancelView
)

urlpatterns = [
    path(
        'requests/',
        MembershipRequestCreateView.as_view(),
        name='membership-request-create'
    ),
    path(
        'requests/incoming/',
        MembershipRequestListView.as_view(),
        name='membership-request-list'
    ),
    path(
        'requests/<int:pk>/',
        MembershipRequestStatusView.as_view(),
        name='membership-request-status'
    ),
    path(
        'requests/<int:pk>/cancel/',
        MembershipRequestCancelView.as_view(),
        name='membership-request-cancel'
    ),
]
