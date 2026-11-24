from rest_framework import serializers
from .models import Project, Skill, ProjectMember


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
    skills = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Skill.objects.all(),
        required=False
    )

    accepted_count = serializers.SerializerMethodField()
    remaining_capacity = serializers.SerializerMethodField()

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
