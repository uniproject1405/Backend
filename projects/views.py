from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from .models import Project, ProjectMember
from django.db import models
from .serializers import (
    ProjectSerializer,
    MyProjectsSerializer,
    ProjectMemberSerializer,
)
from rest_framework.filters import SearchFilter, OrderingFilter
from .permissions import IsCreatorOrReadOnly
from users.permissions import IsProfileComplete

class ProjectListCreateView(generics.ListCreateAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [
    IsAuthenticatedOrReadOnly,
    IsProfileComplete,
]

    filter_backends = [SearchFilter]
    search_fields = ['title']

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsCreatorOrReadOnly]



class MyProjectsView(generics.ListAPIView):
    serializer_class = MyProjectsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        return Project.objects.filter(
            models.Q(creator=user) | models.Q(members__user=user)
        ).distinct()

class ExploreProjectsView(generics.ListAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = ['title', 'description']

    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = Project.objects.all()

        status = self.request.query_params.get(
            'status',
            Project.STATUS_OPEN
        )

        valid_statuses = [
            Project.STATUS_OPEN,
            Project.STATUS_CLOSED
        ]

        if status not in valid_statuses:
            raise serializers.ValidationError({
                'status': 'Invalid status. Choose either open or closed.'
            })

        queryset = queryset.filter(status=status)

        skill_id = self.request.query_params.get('skill')

        if skill_id:
            queryset = queryset.filter(
                skills__id=skill_id
            ).distinct()

        return queryset

class ProjectMembersView(generics.ListAPIView):
    serializer_class = ProjectMemberSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return ProjectMember.objects.filter(
            project_id=self.kwargs['pk']
        ).select_related('user')