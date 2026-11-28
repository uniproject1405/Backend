from django.db import models

from rest_framework import generics, permissions, status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from .models import MembershipRequest
from .pagination import MembershipRequestPagination
from .serializers import (
    MembershipRequestSerializer,
    MembershipRequestCreateSerializer,
    MembershipRequestStatusUpdateSerializer,
)
from users.permissions import IsProfileComplete


class MembershipRequestCreateView(generics.CreateAPIView):
    serializer_class = MembershipRequestCreateSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsProfileComplete,
    ]

    def perform_create(self, serializer):
        serializer.save()


class MembershipRequestListView(generics.ListAPIView):
    serializer_class = MembershipRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MembershipRequestPagination
    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = [
        'project__title',
        'user__username',
        'user__email',
        'message'
    ]

    ordering_fields = ['created_at', 'status', 'project__title']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user

        queryset = MembershipRequest.objects.filter(
            project__creator=user
        ).select_related('project', 'user')

        project_public_id = self.request.query_params.get('project')
        if project_public_id:
            queryset = queryset.filter(
                project__public_id=project_public_id
            )

        req_status = self.request.query_params.get('status')
        if req_status:
            queryset = queryset.filter(status=req_status)

        return queryset


class MembershipRequestStatusView(generics.UpdateAPIView):
    serializer_class = MembershipRequestStatusUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['patch', 'options']
    lookup_field = 'public_id'
    lookup_url_kwarg = 'public_id'

    def get_queryset(self):
        return MembershipRequest.objects.filter(
            project__creator=self.request.user
        ).select_related('project', 'user')


class MembershipRequestCancelView(generics.DestroyAPIView):
    serializer_class = MembershipRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'public_id'
    lookup_url_kwarg = 'public_id'

    def get_queryset(self):
        return MembershipRequest.objects.filter(
            user=self.request.user,
            status=MembershipRequest.STATUS_PENDING
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()

        return Response(
            {"message": "Membership request cancelled successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )


class MembershipStatsView(APIView):
    """
    Aggregated membership request metrics for user dashboard.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        sent = MembershipRequest.objects.filter(user=user)
        received = MembershipRequest.objects.filter(
            project__creator=user
        )

        by_project = (
            received.filter(status=MembershipRequest.STATUS_PENDING)
            .values('project__public_id', 'project__title')
            .annotate(pending_count=models.Count('id'))
            .order_by('-pending_count')
        )

        data = {
            "sent": {
                "total": sent.count(),
                "pending": sent.filter(
                    status=MembershipRequest.STATUS_PENDING
                ).count(),
                "accepted": sent.filter(
                    status=MembershipRequest.STATUS_ACCEPTED
                ).count(),
                "rejected": sent.filter(
                    status=MembershipRequest.STATUS_REJECTED
                ).count(),
            },
            "received": {
                "total": received.count(),
                "pending": received.filter(
                    status=MembershipRequest.STATUS_PENDING
                ).count(),
                "accepted": received.filter(
                    status=MembershipRequest.STATUS_ACCEPTED
                ).count(),
                "rejected": received.filter(
                    status=MembershipRequest.STATUS_REJECTED
                ).count(),
            },
            "projects_to_review": [
                {
                    "project_public_id": str(item['project__public_id']),
                    "project_title": item['project__title'],
                    "pending_count": item['pending_count'],
                }
                for item in by_project
            ],
        }

        return Response(data, status=status.HTTP_200_OK)
