
from django.db import IntegrityError, transaction
from rest_framework import serializers

from .models import MembershipRequest
from projects.models import Project, ProjectMember


class MembershipRequestSerializer(serializers.ModelSerializer):
    applicant_username = serializers.CharField(
        source='user.username',
        read_only=True
    )

    class Meta:
        model = MembershipRequest
        fields = [
            'id',
            'project',
            'user',
            'applicant_username',
            'status',
            'message',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'user',
            'applicant_username',
            'status',
            'created_at',
            'updated_at',
        ]

    def validate_project(self, project):
        user = self.context['request'].user

        if project.creator_id == user.id:
            raise serializers.ValidationError(
                "You cannot apply to your own project."
            )

        if project.status != Project.STATUS_OPEN:
            raise serializers.ValidationError(
                "This project is closed."
            )

        if project.members.filter(user=user).exists():
            raise serializers.ValidationError(
                "You are already a member of this project."
            )

        if project.members.count() >= project.capacity:
            raise serializers.ValidationError(
                "This project has reached its capacity."
            )

        if MembershipRequest.objects.filter(
            project=project,
            user=user,
            status=MembershipRequest.STATUS_PENDING
        ).exists():
            raise serializers.ValidationError(
                "You already have a pending request for this project."
            )

        return project

    def create(self, validated_data):
        try:
            with transaction.atomic():
                return MembershipRequest.objects.create(**validated_data)
        except IntegrityError:
            raise serializers.ValidationError({
                'project': 'You already have a pending request for this project.'
            })


class MembershipRequestStatusSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(
        choices=[
            MembershipRequest.STATUS_ACCEPTED,
            MembershipRequest.STATUS_REJECTED,
        ]
    )

    class Meta:
        model = MembershipRequest
        fields = ['status']

    def update(self, instance, validated_data):
        new_status = validated_data['status']

        with transaction.atomic():
            request_obj = MembershipRequest.objects.select_for_update().get(
                pk=instance.pk
            )

            project = Project.objects.select_for_update().get(
                pk=request_obj.project_id
            )

            if request_obj.status != MembershipRequest.STATUS_PENDING:
                raise serializers.ValidationError({
                    'status': 'This request has already been processed.'
                })

            if new_status == MembershipRequest.STATUS_ACCEPTED:

                if project.status != Project.STATUS_OPEN:
                    raise serializers.ValidationError({
                        'status': 'Cannot accept requests for a closed project.'
                    })

                if project.members.filter(user=request_obj.user).exists():
                    raise serializers.ValidationError({
                        'status': 'This applicant is already a project member.'
                    })

                if project.members.count() >= project.capacity:
                    raise serializers.ValidationError({
                        'status': 'This project has reached its capacity.'
                    })

                ProjectMember.objects.create(
                    project=project,
                    user=request_obj.user
                )

            request_obj.status = new_status
            request_obj.save(update_fields=['status', 'updated_at'])

        return request_obj
