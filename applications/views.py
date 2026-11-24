
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import MembershipRequest
from .serializers import (
    MembershipRequestSerializer,
    MembershipRequestStatusSerializer,
)
from users.permissions import IsProfileComplete


class MembershipRequestCreateView(generics.CreateAPIView):
    serializer_class = MembershipRequestSerializer
    permission_classes = [
        IsAuthenticated,
        IsProfileComplete,
    ]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MembershipRequestListView(generics.ListAPIView):
    serializer_class = MembershipRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MembershipRequest.objects.filter(
            project__creator=self.request.user
        ).select_related('project', 'user')


class MembershipRequestStatusView(generics.UpdateAPIView):
    serializer_class = MembershipRequestStatusSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['patch', 'options']

    def get_queryset(self):
        return MembershipRequest.objects.filter(
            project__creator=self.request.user
        )

class MembershipRequestCancelView(generics.DestroyAPIView):
    serializer_class = MembershipRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MembershipRequest.objects.filter(
            user=self.request.user,
            status=MembershipRequest.STATUS_PENDING
        )