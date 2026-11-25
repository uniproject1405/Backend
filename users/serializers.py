from django.contrib.auth import get_user_model
from rest_framework import serializers
from projects.models import Skill
from .models import Profile

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
    username = serializers.CharField(required=False, allow_blank=True, max_length=150)

    def validate_email(self, value):
        normalized_email = value.strip().lower()
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized_email

    def validate_username(self, value):
        if value:
            username = value.strip()
            # Support usernames starting with @ like Instagram / Telegram
            if username.startswith('@'):
                username = username[1:].strip()
            if not username:
                raise serializers.ValidationError("Username cannot be empty or just '@'.")
            if User.objects.filter(username__iexact=username).exists():
                raise serializers.ValidationError("A user with this username already exists.")
            return username
        return value

    def create(self, validated_data):
        email = validated_data['email']
        password = validated_data['password']
        username = validated_data.get('username') or email
        if username and username.startswith('@'):
            username = username[1:].strip()

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
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


class ProfileSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name']


class PublicPartnerSerializer(serializers.ModelSerializer):
    """
    Public partner representation for explore and collaboration matching.
    Omits sensitive private data like raw email and passwords.
    """
    id = serializers.ReadOnlyField(source='user.id')
    user_id = serializers.ReadOnlyField(source='user.id')
    username = serializers.ReadOnlyField(source='user.username')
    display_name = serializers.ReadOnlyField()
    skills = ProfileSkillSerializer(many=True, read_only=True)
    skills_to_teach = ProfileSkillSerializer(source='skills', many=True, read_only=True)
    avatar_display = serializers.SerializerMethodField()
    telegram = serializers.ReadOnlyField()
    instagram = serializers.ReadOnlyField()
    github = serializers.ReadOnlyField()
    linkedin = serializers.ReadOnlyField()
    open_for_collaboration = serializers.ReadOnlyField(source='open_to_collaboration')
    open_for_mentoring = serializers.ReadOnlyField(source='open_to_mentoring')
    profile = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            'id',
            'user_id',
            'username',
            'name',
            'display_name',
            'headline',
            'bio',
            'avatar_display',
            'skills',
            'skills_to_teach',
            'contact_links',
            'telegram',
            'instagram',
            'github',
            'linkedin',
            'open_to_collaboration',
            'open_for_collaboration',
            'open_to_mentoring',
            'open_for_mentoring',
            'created_at',
            'profile',
        ]

    def get_avatar_display(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url
        if obj.avatar_url:
            return obj.avatar_url
        if hasattr(obj.user, 'google_profile') and obj.user.google_profile.picture:
            return obj.user.google_profile.picture
        return None

    def get_profile(self, obj):
        return {
            'name': obj.name,
            'display_name': obj.display_name,
            'headline': obj.headline,
            'bio': obj.bio,
            'avatar_display': self.get_avatar_display(obj),
            'skills': ProfileSkillSerializer(obj.skills.all(), many=True).data,
            'skills_to_teach': ProfileSkillSerializer(obj.skills.all(), many=True).data,
            'contact_links': obj.contact_links,
            'telegram': obj.telegram,
            'github': obj.github,
            'linkedin': obj.linkedin,
            'open_to_collaboration': obj.open_to_collaboration,
            'open_for_collaboration': obj.open_to_collaboration,
            'open_to_mentoring': obj.open_to_mentoring,
            'open_for_mentoring': obj.open_to_mentoring,
        }


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Self profile management serializer with strict validation for contact channels.
    """
    username = serializers.ReadOnlyField(source='user.username')
    email = serializers.ReadOnlyField(source='user.email')
    display_name = serializers.ReadOnlyField()
    skills = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Skill.objects.all(),
        required=False,
    )
    skills_detail = ProfileSkillSerializer(source='skills', many=True, read_only=True)
    skills_names = serializers.ListField(
        child=serializers.CharField(max_length=50),
        write_only=True,
        required=False,
    )
    skills_to_teach_names = serializers.ListField(
        child=serializers.CharField(max_length=50),
        write_only=True,
        required=False,
    )
    first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    telegram = serializers.CharField(required=False, allow_blank=True)
    instagram = serializers.CharField(required=False, allow_blank=True)
    github = serializers.CharField(required=False, allow_blank=True)
    linkedin = serializers.CharField(required=False, allow_blank=True)
    open_for_collaboration = serializers.BooleanField(source='open_to_collaboration', required=False)
    open_for_mentoring = serializers.BooleanField(source='open_to_mentoring', required=False)
    avatar_display = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'name',
            'display_name',
            'headline',
            'bio',
            'avatar',
            'avatar_url',
            'avatar_display',
            'skills',
            'skills_detail',
            'skills_names',
            'skills_to_teach_names',
            'contact_links',
            'telegram',
            'instagram',
            'github',
            'linkedin',
            'open_to_collaboration',
            'open_for_collaboration',
            'open_to_mentoring',
            'open_for_mentoring',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'username', 'email', 'avatar_display', 'created_at', 'updated_at']

    def get_avatar_display(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url
        if obj.avatar_url:
            return obj.avatar_url
        if hasattr(obj.user, 'google_profile') and obj.user.google_profile.picture:
            return obj.user.google_profile.picture
        return None

    def validate_contact_links(self, value):
        if not isinstance(value, (list, dict)):
            raise serializers.ValidationError("Contact links must be a list of objects or a dictionary.")

        if isinstance(value, dict):
            for platform, url in value.items():
                if not isinstance(url, str) or not url.strip():
                    raise serializers.ValidationError(f"Contact link for '{platform}' cannot be empty.")
                url_val = url.strip()
                if platform.lower() == 'email':
                    serializers.EmailField().run_validation(url_val)
                elif platform.lower() == 'telegram':
                    if not (url_val.startswith('@') or url_val.startswith('https://t.me/')):
                        raise serializers.ValidationError(f"Invalid Telegram handle or link: {url_val}")
                elif platform.lower() == 'instagram':
                    if not (url_val.startswith('@') or url_val.startswith('https://instagram.com/') or url_val.startswith('https://www.instagram.com/')):
                        raise serializers.ValidationError(f"Invalid Instagram handle or link: {url_val}")
                else:
                    if not (url_val.startswith('http://') or url_val.startswith('https://') or url_val.startswith('@')):
                        raise serializers.ValidationError(f"Invalid link or handle for '{platform}': {url_val}")
            return value

        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError("Each contact link entry must be a dictionary.")

            for platform, url in item.items():
                if not isinstance(url, str) or not url.strip():
                    raise serializers.ValidationError("Contact link values cannot be empty.")
                url_val = url.strip()
                if platform.lower() == 'email':
                    serializers.EmailField().run_validation(url_val)
                elif platform.lower() == 'telegram':
                    if not (url_val.startswith('@') or url_val.startswith('https://t.me/')):
                        raise serializers.ValidationError(f"Invalid Telegram handle or link: {url_val}")
                elif platform.lower() == 'instagram':
                    if not (url_val.startswith('@') or url_val.startswith('https://instagram.com/') or url_val.startswith('https://www.instagram.com/')):
                        raise serializers.ValidationError(f"Invalid Instagram handle or link: {url_val}")
                else:
                    if not (url_val.startswith('http://') or url_val.startswith('https://') or url_val.startswith('@')):
                        raise serializers.ValidationError(f"Invalid URL or handle for '{platform}': {url_val}")

        return value

    def update(self, instance, validated_data):
        skills_names = validated_data.pop('skills_names', None)
        skills_to_teach = validated_data.pop('skills_to_teach_names', None)
        skills = validated_data.pop('skills', None)
        first_name = validated_data.pop('first_name', None)
        last_name = validated_data.pop('last_name', None)
        telegram = validated_data.pop('telegram', None)
        instagram = validated_data.pop('instagram', None)
        github = validated_data.pop('github', None)
        linkedin = validated_data.pop('linkedin', None)

        # Update contact links if social handles were provided directly
        if any(x is not None for x in [telegram, instagram, github, linkedin]):
            contact_dict = {}
            if isinstance(instance.contact_links, list):
                for item in instance.contact_links:
                    if isinstance(item, dict):
                        contact_dict.update(item)
            elif isinstance(instance.contact_links, dict):
                contact_dict.update(instance.contact_links)

            if telegram is not None:
                contact_dict['telegram'] = telegram.strip()
            if instagram is not None:
                contact_dict['instagram'] = instagram.strip()
            if github is not None:
                contact_dict['github'] = github.strip()
            if linkedin is not None:
                contact_dict['linkedin'] = linkedin.strip()

            instance.contact_links = [{k: v} for k, v in contact_dict.items() if v]

        # Update User first_name/last_name if provided
        user_updated = False
        if first_name is not None:
            instance.user.first_name = first_name
            user_updated = True
        if last_name is not None:
            instance.user.last_name = last_name
            user_updated = True
        if user_updated:
            instance.user.save()
            if not validated_data.get('name') and not instance.name:
                instance.name = f"{instance.user.first_name} {instance.user.last_name}".strip()

        instance = super().update(instance, validated_data)

        # Handle skill assignments
        if skills is not None:
            instance.skills.set(skills)
        elif skills_names is not None or skills_to_teach is not None:
            target_skills = skills_names if skills_names is not None else skills_to_teach
            skill_objs = []
            for name in target_skills:
                name_clean = name.strip()
                if name_clean:
                    skill_obj, _ = Skill.objects.get_or_create(name=name_clean)
                    skill_objs.append(skill_obj)
            instance.skills.set(skill_objs)

        return instance


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
            raise serializers.ValidationError({"confirm_password": ["Passwords do not match."]})
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
            raise serializers.ValidationError({"confirm_password": ["Passwords do not match."]})
        return attrs
