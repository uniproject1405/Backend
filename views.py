from rest_framework import generics, permissions
from django.db import models
from .models import MembershipRequest
from .serializers import (
    MembershipRequestSerializer,
    MembershipRequestCreateSerializer,
    MembershipRequestStatusUpdateSerializer
)
from .permissions import IsApplicantOrProjectCreator


class MembershipRequestListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MembershipRequestCreateSerializer
        return MembershipRequestSerializer

    def get_queryset(self):
        user = self.request.user
        # Return requests where the user is either the applicant OR the project creator
        return MembershipRequest.objects.filter(
            models.Q(user=user) | models.Q(project__creator=user)
        ).select_related('project', 'user').order_by('-created_at')


class MembershipRequestDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsApplicantOrProjectCreator]
    queryset = MembershipRequest.objects.all().select_related('project', 'user')

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return MembershipRequestStatusUpdateSerializer
        return MembershipRequestSerializer

