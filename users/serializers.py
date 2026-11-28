import re

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework import serializers

from .models import Profile, ProfileSkill

User = get_user_model()

class SkillNamesField(serializers.ListField):
    def to_representation(self, data):
        if hasattr(data, 'all'):
            data = data.all()

        return [skill.name for skill in data]

class UserSerializer(serializers.ModelSerializer):
    profile_public_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'profile_public_id',
            'email',
            'username',
        ]
        read_only_fields = fields

    def get_profile_public_id(self, obj):
        profile = getattr(obj, 'profile', None)

        if profile is None:
            return None

        return str(profile.public_id)


class UserRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        min_length=8,
    )
    username = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
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

            # Support usernames starting with @ like Instagram / Telegram
            if username.startswith('@'):
                username = username[1:].strip()

            if not username:
                raise serializers.ValidationError(
                    "Username cannot be empty or just '@'."
                )

            if User.objects.filter(username__iexact=username).exists():
                raise serializers.ValidationError(
                    "A user with this username already exists."
                )

            return username

        return value

    def create(self, validated_data):
        email = validated_data['email']
        password = validated_data['password']
        username = validated_data['username']

        if username.startswith('@'):
            username = username[1:].strip()

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
        allow_blank=False,
        trim_whitespace=True,
        max_length=150,
    )

    name = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=100,
    )

    job_title = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=150,
    )

    skills = serializers.ListField(
        child=serializers.CharField(
            max_length=100,
            trim_whitespace=True,
        ),
        required=False,
        allow_empty=False,
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

        if self.instance:
            existing_users = existing_users.exclude(
                pk=self.instance.user_id
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

        existing = {}
        if self.instance and isinstance(self.instance.contact_links, dict):
            existing = self.instance.contact_links.copy()

        result = {
            "email": "",
            "linkedin": "",
            "github": "",
        }

        result.update(existing)
        result.update(value)

        for field, link in result.items():
            if not isinstance(link, str):
                raise serializers.ValidationError({
                    field: "This field must be a string."
                })

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
        skills = attrs.get('skills')

        if skills is None:
            if self.instance:
                skills = list(
                    self.instance.skills.values_list(
                        'name',
                        flat=True
                    )
                )
            else:
                skills = []

        if not skills:
            raise serializers.ValidationError({
                "skills": "At least one skill is required."
            })

        if len(skills) > 20:
            raise serializers.ValidationError({
                "skills": "You can have up to 20 skills."
            })

        seen = set()

        for name in skills:
            normalized = name.casefold()

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

        name = attrs.get(
            'name',
            self.instance.name if self.instance else None
        )

        job_title = attrs.get(
            'job_title',
            self.instance.job_title if self.instance else None
        )

        if not name or not name.strip():
            raise serializers.ValidationError({
                "name": "Name is required."
            })

        if not job_title or not job_title.strip():
            raise serializers.ValidationError({
                "job_title": "Job title is required."
            })

        return attrs

    def get_or_create_profile_skills(self, skill_names):
        result = []

        for name in skill_names:
            name = name.strip()

            skill = ProfileSkill.objects.filter(
                name__iexact=name
            ).first()

            if skill is None:
                try:
                    with transaction.atomic():
                        skill = ProfileSkill.objects.create(
                            name=name
                        )
                except IntegrityError:
                    skill = ProfileSkill.objects.get(
                        name__iexact=name
                    )

            result.append(skill)

        return result

    def create(self, validated_data):
        user_data = validated_data.pop('user', {})
        username = user_data.get('username')
        skill_names = validated_data.pop('skills', [])

        with transaction.atomic():
            user = self.context['request'].user

            if username is not None:
                user.username = username
                user.save(update_fields=['username'])

            profile = super().create({
                **validated_data,
                'user': user,
            })

            skills = self.get_or_create_profile_skills(skill_names)
            profile.skills.set(skills)

        return profile

    def update(self, instance, validated_data):
        skill_names = validated_data.pop('skills', None)
        user_data = validated_data.pop('user', {})
        username = user_data.get('username')

        with transaction.atomic():
            if username is not None:
                instance.user.username = username
                instance.user.save(update_fields=['username'])

            profile = super().update(instance, validated_data)

            if skill_names is not None:
                skills = self.get_or_create_profile_skills(skill_names)
                profile.skills.set(skills)

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
            'avatar',
            'contact_links',
            'open_to_collaboration',
            'open_to_mentoring',
        ]

class PublicPartnerSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        source='user.username',
        read_only=True,
    )

    skills = SkillNamesField(read_only=True)

    class Meta:
        model = Profile
        fields = [
            'public_id',
            'username',
            'name',
            'bio',
            'job_title',
            'skills',
            'avatar',
            'open_to_collaboration',
            'open_to_mentoring',
        ]

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    redirect_url = serializers.URLField(required=False, allow_blank=True)

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetValidateSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True, allow_blank=False)
    token = serializers.CharField(required=True, allow_blank=False)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True, allow_blank=False)
    token = serializers.CharField(required=True, allow_blank=False)
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        min_length=8,
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        min_length=8,
    )

    def validate(self, attrs):
        if attrs.get('new_password') != attrs.get('confirm_password'):
            raise serializers.ValidationError({
                "confirm_password": ["Passwords do not match."]
            })
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        min_length=8,
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        min_length=8,
    )

    def validate(self, attrs):
        if attrs.get('new_password') != attrs.get('confirm_password'):
            raise serializers.ValidationError({
                "confirm_password": ["Passwords do not match."]
            })
        return attrs
