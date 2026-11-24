from django.contrib.auth import get_user_model
from rest_framework import serializers

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
    username = serializers.CharField(required=True, allow_blank=False, max_length=150,)

    def validate_email(self, value):
        normalized_email = value.strip().lower()
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized_email

    def validate_username(self, value):
        username = value.strip()

        if not username:
            raise serializers.ValidationError("Username is required.")

        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("A user with this username already exists.")

        return username

    def create(self, validated_data):
        email = validated_data['email']
        password = validated_data['password']
        username = validated_data['username']

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    username = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=150
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
    )

    def validate(self, attrs):
        email = attrs.get('email')
        username = attrs.get('username')
        password = attrs.get('password', '')

        if not email and not username:
            raise serializers.ValidationError(
                "Email or username is required."
            )

        if email and username:
            raise serializers.ValidationError(
                "Enter either email or username, not both."
            )

        if email:
            user = User.objects.filter(
                email__iexact=email.strip()
            ).first()
            login_field = "email"
        else:
            user = User.objects.filter(
                username__iexact=username.strip()
            ).first()
            login_field = "username"

        if (
            user is None
            or not user.check_password(password)
            or not user.is_active
        ):
            raise serializers.ValidationError(
                f"Invalid {login_field} or password."
            )

        attrs['user'] = user
        return attrs
