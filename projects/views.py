from django.db import models
from django.shortcuts import get_object_or_404

from rest_framework import generics, serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from .models import Project, Skill, ProjectMember
from .permissions import IsCreatorOrReadOnly
from .serializers import (
    ProjectSerializer,
    MyProjectsSerializer,
    SkillSerializer,
    ProjectMemberSerializer,
)

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

    search_fields = ['title', 'description', 'skills__name']

    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = Project.objects.all()
        status = self.request.query_params.get('status', Project.STATUS_OPEN)

        valid_statuses = [Project.STATUS_OPEN, Project.STATUS_CLOSED]
        if status not in valid_statuses:
            raise serializers.ValidationError({
                'status': 'Invalid status. Choose either open or closed.'
            })

        queryset = queryset.filter(status=status)

        skill_name = self.request.query_params.get('skill')
        if skill_name:
            skill_name = skill_name.strip()

            queryset = queryset.filter(
                skills__name__iexact=skill_name
            ).distinct()

        return queryset

class ProjectMembersView(generics.ListAPIView):
    serializer_class = ProjectMemberSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        public_id = self.kwargs.get('public_id')

        return ProjectMember.objects.filter(
            project__public_id=public_id
        ).select_related('user')


class ProjectMemberDetailView(generics.DestroyAPIView):
    """
    Remove a member from the project or allow a member to leave.
    If removal frees capacity on a closed project, the project automatically re-opens.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, public_id, member_public_id):
        project = get_object_or_404(
            Project,
            public_id=public_id
        )

        member = get_object_or_404(
            ProjectMember.objects.select_related('user__profile'),
            project=project,
            user__profile__public_id=member_public_id
        )

        is_creator = project.creator_id == request.user.id
        is_self = member.user_id == request.user.id

        if not is_creator and not is_self:
            raise PermissionDenied(
                "You are not authorized to remove this member."
            )

        member.delete()

        if (
            project.status == Project.STATUS_CLOSED
            and project.members.count() < project.capacity
        ):
            project.status = Project.STATUS_OPEN
            project.save(update_fields=['status', 'updated_at'])

        return Response(
            {"message": "Member removed from project successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )
