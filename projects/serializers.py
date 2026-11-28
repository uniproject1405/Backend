import re

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework import serializers

from .models import Project, Skill, ProjectMember

User = get_user_model()

SKILL_NAME_PATTERN = re.compile(
    r"(?=.*[A-Za-z])[A-Za-z0-9.+#][A-Za-z0-9 .+#&()/_-]*"
)

class SkillNamesField(serializers.ListField):
    def to_representation(self, data):
        if hasattr(data, 'all'):
            data = data.all()

        return [skill.name for skill in data]

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['name']


class ProjectMemberSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMember
        fields = ['user', 'joined_at']

    def get_user(self, obj):
        profile = getattr(obj.user, 'profile', None)

        return {
            'public_id': str(profile.public_id) if profile else None,
            'username': obj.user.username,
            'name': profile.name if profile else '',
        }


class ProjectSerializer(serializers.ModelSerializer):
    creator = serializers.SerializerMethodField()
    skills = SkillNamesField(
        child=serializers.CharField(
            max_length=100,
            trim_whitespace=True
        ),
        required=True,
        allow_empty=False
    )

    accepted_count = serializers.SerializerMethodField()
    remaining_capacity = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'public_id',
            'title',
            'goal',
            'description',
            'creator',
            'capacity',
            'accepted_count',
            'remaining_capacity',
            'status',
            'project_type',
            'custom_project_type',
            'skills',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'public_id',
            'creator',
            'remaining_capacity',
            'created_at',
            'updated_at',
        ]

    def get_creator(self, obj):
        profile = getattr(obj.creator, 'profile', None)

        return {
            'public_id': str(profile.public_id) if profile else None,
            'username': obj.creator.username,
            'name': profile.name if profile else '',
        }

    def validate_skills(self, skills):
        if not skills:
            raise serializers.ValidationError(
                "At least one skill is required."
            )

        if len(skills) > 15:
            raise serializers.ValidationError(
                "You can have up to 15 skills."
            )

        seen = set()

        for name in skills:
            normalized = name.casefold()

            if not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9 .+#/&()_-]*",
                name
            ):
                raise serializers.ValidationError(
                    "Skill names must contain English characters only."
                )

            if normalized in seen:
                raise serializers.ValidationError(
                    "Duplicate skills are not allowed."
                )

            seen.add(normalized)

        return skills

    def get_or_create_skills(self, skill_names):
        result = []

        for name in skill_names:
            skill = Skill.objects.filter(
                name__iexact=name
            ).first()

            if skill is None:
                try:
                    with transaction.atomic():
                        skill = Skill.objects.create(name=name)
                except IntegrityError:
                    skill = Skill.objects.get(name__iexact=name)

            result.append(skill)

        return result

    def create(self, validated_data):
        skill_names = validated_data.pop('skills', [])

        with transaction.atomic():
            project = super().create(validated_data)

            skills = self.get_or_create_skills(skill_names)
            project.skills.set(skills)

        return project

    def update(self, instance, validated_data):
        skill_names = validated_data.pop('skills', None)

        with transaction.atomic():
            project = super().update(instance, validated_data)

            if skill_names is not None:
                skills = self.get_or_create_skills(skill_names)
                project.skills.set(skills)

        return project

    def get_accepted_count(self, obj):
        return obj.members.count()

    def get_remaining_capacity(self, obj):
        return max(obj.capacity - self.get_accepted_count(obj), 0)

    def validate(self, attrs):
        project_type = attrs.get(
            'project_type',
            getattr(self.instance, 'project_type', '')
        )

        custom_project_type = attrs.get(
            'custom_project_type',
            getattr(self.instance, 'custom_project_type', '')
        )

        if project_type == 'other' and not custom_project_type.strip():
            raise serializers.ValidationError({
                'custom_project_type': 'Please specify your project type.'
            })

        return attrs

    def validate_custom_project_type(self, value):
        value = value.strip()

        if value and not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9 .+#/&()_-]*",
            value
        ):
            raise serializers.ValidationError(
                "Project type must use English characters, numbers, and supported symbols only."
            )

        return value
class MyProjectsSerializer(ProjectSerializer):
    role = serializers.SerializerMethodField()

    class Meta(ProjectSerializer.Meta):
        fields = ProjectSerializer.Meta.fields + ['role']

    def get_role(self, obj):
        user = self.context['request'].user
        if obj.creator_id == user.id:
            return 'creator'
        return 'member'
