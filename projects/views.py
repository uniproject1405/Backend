from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from .models import Project, Skill
from django.db import models
from .serializers import (
    ProjectSerializer,
    MyProjectsSerializer,
    SkillSerializer,
)
from rest_framework.filters import SearchFilter, OrderingFilter
from .permissions import IsCreatorOrReadOnly

class ProjectListCreateView(generics.ListCreateAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    filter_backends = [SearchFilter]
    search_fields = ['title']

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsCreatorOrReadOnly]
    lookup_field = 'public_id'


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

        skill_name = self.request.query_params.get('skill')

        if skill_name:
            skill_name = skill_name.strip()

            queryset = queryset.filter(
                models.Q(skills__name__iexact=skill_name) |
                models.Q(skills__aliases__name__iexact=skill_name)
            ).distinct()

        return queryset

class SkillListView(generics.ListAPIView):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer