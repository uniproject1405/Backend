from rest_framework import serializers
from .models import Project, Skill, ProjectMember
import re
from django.db import transaction, IntegrityError

SKILL_NAME_PATTERN = re.compile(
    r"(?=.*[A-Za-z])[A-Za-z0-9.+#][A-Za-z0-9 .+#&()/_-]*"
)

class SkillNameField(serializers.SlugRelatedField):

    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError(
                "Skill name must be a string."
            )

        skill_name = data.strip()

        if not SKILL_NAME_PATTERN.fullmatch(skill_name):
            raise serializers.ValidationError(
                "Skill names must use English characters, numbers, and supported symbols only."
            )

        try:
            return self.get_queryset().get(name__iexact=skill_name)
        except Skill.DoesNotExist:
            raise serializers.ValidationError(
                f"Skill '{skill_name}' does not exist. Use custom_skills to add a new skill."
            )

    def to_representation(self, value):
        return value.name

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['name']
        

class ProjectSerializer(serializers.ModelSerializer):
    skills = SkillNameField(
    many=True,
    slug_field='name',
    queryset=Skill.objects.all(),
    required=False,
    allow_empty=True
)
    custom_skills = serializers.ListField(
    child=serializers.CharField(max_length=100),
    required=False,
    write_only=True,
    allow_empty=True
    )

    accepted_count = serializers.SerializerMethodField()
    
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
            'status',
            'project_type',
            'custom_project_type',
            'skills',
            'custom_skills',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'public_id',
            'creator',
            'created_at',
            'updated_at',
        ]        
    def get_accepted_count(self, obj):
        return obj.members.count()

    def validate_custom_skills(self, value):
        cleaned_skills = []
        seen = set()

        for skill_name in value:
            skill_name = skill_name.strip()

            if not skill_name:
                raise serializers.ValidationError(
                    "Skill names cannot be empty."
                )

            if not SKILL_NAME_PATTERN.fullmatch(skill_name):
                raise serializers.ValidationError(
                    "Skill names must use English characters, numbers, and supported symbols only."
                )

            normalized_name = skill_name.casefold()

            if normalized_name not in seen:
                cleaned_skills.append(skill_name)
                seen.add(normalized_name)

        return cleaned_skills

    def get_or_create_skills(self, custom_skills):
        skills = []

        for skill_name in custom_skills:
            try:
                with transaction.atomic():
                    skill, created = Skill.objects.get_or_create(
                        name__iexact=skill_name,
                        defaults={'name': skill_name}
                    )
            except IntegrityError:
                skill = Skill.objects.get(name__iexact=skill_name)

            skills.append(skill)

        return skills

    def validate_skills(self, value):
        for skill in value:
            if not SKILL_NAME_PATTERN.fullmatch(skill.name):
                raise serializers.ValidationError(
                    "All selected skills must use English names."
                )

        return value

    def create(self, validated_data):
        custom_skills = validated_data.pop('custom_skills', [])
        selected_skills = validated_data.pop('skills', [])

        with transaction.atomic():
            new_skills = self.get_or_create_skills(custom_skills)

            project = Project.objects.create(**validated_data)

            all_skills = list({skill.id: skill for skill in selected_skills + new_skills}.values())

            project.skills.set(all_skills)

        return project


    def update(self, instance, validated_data):
        custom_skills = validated_data.pop('custom_skills', [])
        selected_skills = validated_data.pop('skills', None)

        with transaction.atomic():
            new_skills = self.get_or_create_skills(custom_skills)

            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            instance.save()

            if selected_skills is not None or custom_skills:
                current_skills = list(instance.skills.all())

                skills_to_add = selected_skills or []

                all_skills = list({
                    skill.id: skill
                    for skill in current_skills + skills_to_add + new_skills
                }.values())

                instance.skills.set(all_skills)

        return instance
    
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

        # Existing skills are retained during updates.
        current_skills = (
            list(self.instance.skills.all())
            if self.instance else []
        )

        selected_skills = attrs.get('skills', [])
        custom_skills = attrs.get('custom_skills', [])

        # Count all unique skills that the project will have.
        all_skill_ids = {skill.id for skill in current_skills}
        all_skill_ids.update(skill.id for skill in selected_skills)

        for skill_name in custom_skills:
            existing_skill = Skill.objects.filter(
                name__iexact=skill_name
            ).first()

            if existing_skill:
                all_skill_ids.add(existing_skill.id)
            else:
                all_skill_ids.add(skill_name.casefold())

        if not all_skill_ids:
            raise serializers.ValidationError({
                'skills': 'At least one skill is required.'
            })

        if len(all_skill_ids) > 15:
            raise serializers.ValidationError({
                'skills': 'You can select a maximum of 15 unique skills in total.'
            })

        return attrs

    def validate_custom_project_type(self, value):
        value = value.strip()

        if value and not SKILL_NAME_PATTERN.fullmatch(value):
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
