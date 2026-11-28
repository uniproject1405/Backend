
from django.urls import path

from .views import (
    MembershipRequestCreateView,
    MembershipRequestListView,
    MembershipRequestStatusView,
    MembershipRequestCancelView,
    MembershipStatsView,
)

app_name = 'applications'

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
        'requests/stats/',
        MembershipStatsView.as_view(),
        name='request-stats'
    ),
    path(
        'requests/<uuid:public_id>/',
        MembershipRequestStatusView.as_view(),
        name='membership-request-status'
    ),
    path(
        'requests/<uuid:public_id>/cancel/',
        MembershipRequestCancelView.as_view(),
        name='membership-request-cancel'
    ),
]
