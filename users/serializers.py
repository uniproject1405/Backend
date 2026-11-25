import re

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework import serializers

from .models import Profile, ProfileSkill

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username']
        read_only_fields = ['id', 'email', 'username']


class UserRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        min_length=8,
    )
    username = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=150
    )

    def validate_email(self, value):
        normalized_email = value.strip().lower()

        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )

        return normalized_email

    def validate_username(self, value):
        if value:
            username = value.strip()

            if User.objects.filter(username__iexact=username).exists():
                raise serializers.ValidationError(
                    "A user with this username already exists."
                )

            return username

        return value

    def create(self, validated_data):
        email = validated_data['email']
        password = validated_data['password']
        username = validated_data.get('username') or email

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
    )

    def validate(self, attrs):
        email = attrs.get('email', '').strip().lower()
        password = attrs.get('password', '')

        user = User.objects.filter(email__iexact=email).first()

        # Generic authentication failure message to prevent account enumeration
        if user is None or not user.check_password(password) or not user.is_active:
            raise serializers.ValidationError("Invalid email or password.")

        attrs['user'] = user
        return attrs


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=False, allow_blank=False)
    access_token = serializers.CharField(required=False, allow_blank=False)
    code = serializers.CharField(required=False, allow_blank=False)
    redirect_uri = serializers.CharField(required=False, allow_blank=False)

    def validate(self, attrs):
        if not any([attrs.get('id_token'), attrs.get('access_token'), attrs.get('code')]):
            raise serializers.ValidationError(
                "Either id_token, access_token, or code must be provided."
            )
        return attrs


class ProfileSerializer(serializers.ModelSerializer):
    public_id = serializers.UUIDField(read_only=True)
    username = serializers.CharField(
        source='user.username',
        required=False,
        max_length=150,
        validators=User._meta.get_field('username').validators
    )
    skills = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        queryset=ProfileSkill.objects.all(),
        required=False,
        allow_empty=True
    )

    other_skills = serializers.ListField(
        child=serializers.CharField(
            max_length=100,
            trim_whitespace=True
        ),
        required=False,
        write_only=True
    )

    def validate_username(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Username cannot be empty."
            )

        existing_users = User.objects.filter(
            username__iexact=value
        )

        request = self.context.get('request')

        if self.instance:
            existing_users = existing_users.exclude(
                pk=self.instance.user_id
            )
        elif request and request.user.is_authenticated:
            existing_users = existing_users.exclude(
                pk=request.user.pk
            )

        if existing_users.exists():
            raise serializers.ValidationError(
                "This username is already taken."
            )

        return value

    def validate_contact_links(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "Contact links must be an object."
            )

        allowed_fields = {"email", "linkedin", "github"}

        unknown_fields = set(value.keys()) - allowed_fields
        if unknown_fields:
            raise serializers.ValidationError(
                "Only email, linkedin and github are allowed."
            )

        if self.instance:
            existing = self.instance.contact_links or {}
            if not isinstance(existing, dict):
                existing = {}
        else:
            existing = {}

        result = {
            "email": "",
            "linkedin": "",
            "github": "",
        }

        result.update(existing)
        result.update(value)

        for field, link in result.items():
            if not isinstance(link, str):
                raise serializers.ValidationError(
                    {field: "This field must be a string."}
                )

            link = link.strip()
            result[field] = link

            if not link:
                continue

            if field == "email":
                serializers.EmailField().run_validation(link)
            else:
                serializers.URLField().run_validation(link)

        return result

    
    def validate(self, attrs):
        selected_skills = attrs.get("skills")

        if selected_skills is None:
            if self.instance:
                selected_skills = list(self.instance.skills.all())
            else:
                selected_skills = []

        other_skills = attrs.get("other_skills", [])

        all_names = (
            [skill.name for skill in selected_skills]
            + other_skills
        )

        # A new profile must have at least one skill.
        if not self.instance and not all_names:
            raise serializers.ValidationError({
                "skills": "At least one skill is required."
            })

        if len(all_names) > 20:
            raise serializers.ValidationError({
                "skills": "You can have up to 20 skills in total."
            })

        seen = set()

        for name in all_names:
            normalized = name.strip().casefold()

            if not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9 .+#/&()_-]*",
                name
            ):
                raise serializers.ValidationError({
                    "skills": "Skill names must contain English characters only."
                })

            if normalized in seen:
                raise serializers.ValidationError({
                    "skills": "Duplicate skills are not allowed."
                })

            seen.add(normalized)

        if self.instance:
            name = attrs.get("name", self.instance.name)

            if not name or not name.strip():
                raise serializers.ValidationError({
                    "name": "This field cannot be empty."
                })

            if not all_names:
                raise serializers.ValidationError({
                    "skills": "At least one skill is required."
                })

        return attrs


    def get_or_create_profile_skills(self, skill_names):
        result = []

        for name in skill_names:
            try:
                with transaction.atomic():
                    skill, created = ProfileSkill.objects.get_or_create(
                        name=name
                    )
            except IntegrityError:
                skill = ProfileSkill.objects.get(name__iexact=name)

            result.append(skill)

        return result
    
    def create(self, validated_data):
        selected_skills = validated_data.pop('skills', [])
        other_skills = validated_data.pop('other_skills', [])

        user_data = validated_data.pop('user', {})
        username = user_data.get('username')

        with transaction.atomic():
            user = self.context['request'].user

            if username is not None:
                user.username = username
                user.save(update_fields=['username'])

            profile = super().create({
                **validated_data,
                'user': user
            })

            new_skills = self.get_or_create_profile_skills(
                other_skills
            )

            profile.skills.set(selected_skills + new_skills)

        return profile

    def update(self, instance, validated_data):
        selected_skills = validated_data.pop('skills', None)
        other_skills = validated_data.pop('other_skills', [])

        user_data = validated_data.pop('user', {})
        username = user_data.get('username')

        with transaction.atomic():

            if username is not None:
                instance.user.username = username
                instance.user.save(update_fields=['username'])

            profile = super().update(instance, validated_data)

            if selected_skills is not None or other_skills:
                if selected_skills is None:
                    selected_skills = list(profile.skills.all())

                new_skills = self.get_or_create_profile_skills(
                    other_skills
                )

                profile.skills.set(selected_skills + new_skills)

        return profile

    class Meta:
        model = Profile
        fields = [
            'public_id',
            'username',
            'name',
            'bio',
            'job_title',
            'skills',
            'other_skills',
            'avatar',
            'contact_links',
            'open_to_collaboration',
            'open_to_mentoring',
        ]