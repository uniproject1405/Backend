import re

from django.db import IntegrityError, transaction
from rest_framework import serializers

from .models import Project, Skill, ProjectMember


class SkillNamesField(serializers.ListField):
    def to_representation(self, data):
        if hasattr(data, 'all'):
            data = data.all()

        return [skill.name for skill in data]

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name']

class ProjectMemberSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMember
        fields = ['user', 'joined_at']

    def get_user(self, obj):
        return {
            'username': obj.user.username,
            'name': obj.user.profile.name,
        }        

class ProjectSerializer(serializers.ModelSerializer):
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

    class Meta:
        model = Project
        fields = [
            'id',
            'title',
            'goal',
            'description',
            'creator',
            'capacity',
            'accepted_count',
            'remaining_capacity',
            'status',
            'skills',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'creator',
            'created_at',
            'updated_at',
        ]        
    def get_accepted_count(self, obj):
        return obj.members.count()

    def get_remaining_capacity(self, obj):
        return max(obj.capacity - self.get_accepted_count(obj), 0)

class MyProjectsSerializer(ProjectSerializer):
    role = serializers.SerializerMethodField()

    class Meta(ProjectSerializer.Meta):
        fields = ProjectSerializer.Meta.fields + ['role']

    def get_role(self, obj):
        user = self.context['request'].user

        if obj.creator_id == user.id:
            return 'creator'

        return 'member'
