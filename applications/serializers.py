
from rest_framework import serializers
from django.db import IntegrityError, transaction

from .models import MembershipRequest
from projects.models import Project, ProjectMember


class MembershipRequestSerializer(serializers.ModelSerializer):
    applicant_username = serializers.CharField(
        source='user.username',
        read_only=True
    )
    applicant_public_id = serializers.UUIDField(
        source='user.profile.public_id',
        read_only=True
    )
    project_title = serializers.ReadOnlyField(source='project.title')
    project = serializers.UUIDField(
        source='project.public_id',
        read_only=True
    )

    class Meta:
        model = MembershipRequest
        fields = [
            'public_id',
            'project',
            'project_title',
            'applicant_public_id',
            'applicant_username',
            'status',
            'message',
            'response_message',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class MembershipRequestCreateSerializer(serializers.ModelSerializer):
    project = serializers.SlugRelatedField(
        slug_field='public_id',
        queryset=Project.objects.all()
    )
    applicant_username = serializers.ReadOnlyField(source='user.username')
    status = serializers.ReadOnlyField()
    created_at = serializers.ReadOnlyField()

    class Meta:
        model = MembershipRequest
        fields = [
            'public_id',
            'project',
            'message',
            'status',
            'applicant_username',
            'created_at'
        ]
        read_only_fields = [
            'public_id',
            'status',
            'applicant_username',
            'created_at'
        ]

    def validate_project(self, project):
        user = self.context['request'].user

        if project.status != Project.STATUS_OPEN:
            raise serializers.ValidationError(
                "This project is closed."
            )

        if project.creator_id == user.id:
            raise serializers.ValidationError(
                "You cannot apply to your own project."
            )

        if ProjectMember.objects.filter(
            project=project,
            user=user
        ).exists():
            raise serializers.ValidationError(
                "You are already a member of this project."
            )

        if MembershipRequest.objects.filter(
            project=project,
            user=user,
            status=MembershipRequest.STATUS_PENDING
        ).exists():
            raise serializers.ValidationError(
                "You already have a pending request for this project."
            )

        if ProjectMember.objects.filter(
            project=project
        ).count() >= project.capacity:
            raise serializers.ValidationError(
                "This project has reached its capacity."
            )

        return project

    def create(self, validated_data):
        user = self.context['request'].user

        try:
            with transaction.atomic():
                return MembershipRequest.objects.create(
                    user=user,
                    **validated_data
                )
        except IntegrityError:
            raise serializers.ValidationError({
                'project': 'You already have a pending request for this project.'
            })


class MembershipRequestStatusUpdateSerializer(serializers.ModelSerializer):
    response_message = serializers.CharField(
        required=False,
        allow_blank=True,
        default=''
    )

    class Meta:
        model = MembershipRequest
        fields = ['status', 'response_message']

    def validate_status(self, value):
        valid_transitions = [
            MembershipRequest.STATUS_ACCEPTED,
            MembershipRequest.STATUS_REJECTED
        ]

        if value not in valid_transitions:
            raise serializers.ValidationError(
                "Status can only be updated to 'accepted' or 'rejected'."
            )

        return value

    def update(self, instance, validated_data):
        new_status = validated_data.get('status')
        response_msg = validated_data.get('response_message', '')
        request_user = self.context['request'].user

        with transaction.atomic():
            request_obj = MembershipRequest.objects.select_for_update().get(
                pk=instance.pk
            )

            project = Project.objects.select_for_update().get(
                pk=request_obj.project_id
            )

            if project.creator_id != request_user.id:
                raise serializers.ValidationError({
                    "detail": "Only the project creator can accept or reject requests."
                })

            if request_obj.status != MembershipRequest.STATUS_PENDING:
                raise serializers.ValidationError({
                    "detail": f"This request is already {request_obj.status}."
                })

            if new_status == MembershipRequest.STATUS_ACCEPTED:

                if project.status != Project.STATUS_OPEN:
                    raise serializers.ValidationError({
                        "detail": "Cannot accept requests for a closed project."
                    })

                if project.members.filter(user=request_obj.user).exists():
                    raise serializers.ValidationError({
                        "detail": "This applicant is already a project member."
                    })

                if project.members.count() >= project.capacity:
                    raise serializers.ValidationError({
                        "detail": "Cannot accept request because project capacity is full."
                    })

                ProjectMember.objects.get_or_create(
                    project=project,
                    user=request_obj.user
                )

                if project.members.count() >= project.capacity:
                    project.status = Project.STATUS_CLOSED
                    project.save(update_fields=['status', 'updated_at'])

            request_obj.status = new_status

            if response_msg:
                request_obj.response_message = response_msg.strip()

            request_obj.save(
                update_fields=[
                    'status',
                    'response_message',
                    'updated_at'
                ]
            )

        return request_obj
