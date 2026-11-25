import urllib.parse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponseRedirect
from rest_framework import status, generics, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed, ValidationError

from .models import Profile
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    GoogleAuthSerializer,
    PublicPartnerSerializer,
    UserProfileSerializer,
    PasswordResetRequestSerializer,
    PasswordResetValidateSerializer,
    PasswordResetConfirmSerializer,
    PasswordChangeSerializer,
)
from .services import (
    authenticate_google,
    get_google_auth_url,
    verify_password_reset_token,
    send_password_reset_email,
    reset_user_password,
)

User = get_user_model()



def users_api(request):
    """
    Baseline test endpoint created by team.
    Preserved for backward compatibility with existing tests.
    """
    if request.method != "GET":
        return JsonResponse(
            {
                "message": "Method not allowed",
                "status": "error",
            },
            status=405,
        )

    return JsonResponse({
        "message": "API is working!",
        "status": "success",
    })


class RegisterView(APIView):
    """
    Register a new user with email and password.
    Returns authentication token and safe user details upon success.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response(
                {
                    "token": token.key,
                    "user": UserSerializer(user).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    Authenticate user by email and password.
    Returns authentication token upon success without revealing account existence on failure.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, _ = Token.objects.get_or_create(user=user)
            return Response(
                {
                    "token": token.key,
                    "user": UserSerializer(user).data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CurrentUserView(APIView):
    """
    Retrieve or update profile details for the currently authenticated user.
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        user_data = UserSerializer(request.user).data
        user_data['profile'] = UserProfileSerializer(profile, context={'request': request}).data
        return Response(user_data, status=status.HTTP_200_OK)

    def patch(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(
            profile,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    Invalidate the active authentication token for the current user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if hasattr(request, 'auth') and isinstance(request.auth, Token):
            request.auth.delete()
        elif hasattr(request.user, 'auth_token'):
            request.user.auth_token.delete()

        return Response(
            {"message": "Successfully logged out."},
            status=status.HTTP_200_OK,
        )


class GoogleAuthView(APIView):
    """
    Authenticate or register a user using Google credentials (id_token, access_token, or code).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            user, token, is_new = authenticate_google(
                id_token=serializer.validated_data.get('id_token'),
                access_token=serializer.validated_data.get('access_token'),
                code=serializer.validated_data.get('code'),
                redirect_uri=serializer.validated_data.get('redirect_uri'),
            )
            return Response(
                {
                    "token": token.key,
                    "user": UserSerializer(user).data,
                    "is_new_user": is_new,
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
        except AuthenticationFailed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(
                {"detail": "Authentication failed. Please verify your Google credentials."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class GoogleLoginRedirectView(APIView):
    """
    Generate Google OAuth consent URL or redirect user to Google.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        state = request.GET.get('state')
        auth_url = get_google_auth_url(state=state)

        if request.GET.get('format') == 'json':
            return Response({"auth_url": auth_url}, status=status.HTTP_200_OK)

        return HttpResponseRedirect(auth_url)


class GoogleCallbackView(APIView):
    """
    Handle OAuth callback redirect from Google.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')
        error = request.GET.get('error')
        if error:
            redirect_target = f"{frontend_url}/login?error={urllib.parse.quote(error)}"
            return HttpResponseRedirect(redirect_target)

        code = request.GET.get('code')
        if not code:
            redirect_target = f"{frontend_url}/login?error={urllib.parse.quote('Authorization code was not provided')}"
            return HttpResponseRedirect(redirect_target)

        try:
            user, token, _ = authenticate_google(code=code)
            redirect_target = (
                f"{frontend_url}/login?token={token.key}"
                f"&email={urllib.parse.quote(user.email)}"
                f"&username={urllib.parse.quote(user.username)}"
            )
            return HttpResponseRedirect(redirect_target)
        except Exception as exc:
            redirect_target = f"{frontend_url}/login?error={urllib.parse.quote(str(exc))}"
            return HttpResponseRedirect(redirect_target)


class PartnerExploreView(generics.ListAPIView):
    """
    Explore and filter users/partners open for collaboration and mentoring.
    Supports query parameters:
      - search: text search across username, name, headline, bio, skills
      - skill: filter by skill ID or skill name
      - collaboration: filter by open_to_collaboration (true/false)
      - mentoring: filter by open_to_mentoring (true/false)
      - ordering: created_at, name, updated_at
    """
    permission_classes = [AllowAny]
    serializer_class = PublicPartnerSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'headline', 'bio', 'user__username', 'skills__name']
    ordering_fields = ['created_at', 'name', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = (
            Profile.objects
            .select_related('user')
            .prefetch_related('skills')
            .filter(user__is_active=True)
        )

        # Skill filtering (by id or name substring)
        skill_param = self.request.query_params.get('skill')
        if skill_param:
            skill_clean = skill_param.strip()
            if skill_clean.isdigit():
                queryset = queryset.filter(skills__id=int(skill_clean))
            else:
                queryset = queryset.filter(skills__name__icontains=skill_clean)

        # Collaboration filter
        collab_param = (
            self.request.query_params.get('collaboration') or
            self.request.query_params.get('open_to_collaboration')
        )
        if collab_param is not None:
            is_collab = str(collab_param).lower() in ['true', '1', 'yes']
            queryset = queryset.filter(open_to_collaboration=is_collab)

        # Mentoring filter
        mentor_param = (
            self.request.query_params.get('mentoring') or
            self.request.query_params.get('open_to_mentoring')
        )
        if mentor_param is not None:
            is_mentor = str(mentor_param).lower() in ['true', '1', 'yes']
            queryset = queryset.filter(open_to_mentoring=is_mentor)

        return queryset.distinct()

    def filter_queryset(self, queryset):
        search = self.request.query_params.get('search')
        if search and search.strip().startswith('@'):
            cleaned_search = search.strip().lstrip('@')
            if cleaned_search:
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(user__username__icontains=cleaned_search) |
                    Q(name__icontains=cleaned_search) |
                    Q(headline__icontains=cleaned_search) |
                    Q(bio__icontains=cleaned_search) |
                    Q(skills__name__icontains=cleaned_search)
                )
                ordering_filter = filters.OrderingFilter()
                return ordering_filter.filter_queryset(self.request, queryset, self)
        return super().filter_queryset(queryset)


class PublicProfileDetailView(generics.RetrieveAPIView):
    """
    Retrieve public profile information for a user by their user ID.
    Omit sensitive private data (email, password).
    """
    permission_classes = [AllowAny]
    serializer_class = PublicPartnerSerializer

    def get_object(self):
        pk = self.kwargs.get('pk')
        user = generics.get_object_or_404(User, id=pk, is_active=True)
        profile, _ = Profile.objects.get_or_create(user=user)
        return profile


class UserDetailView(generics.RetrieveAPIView):
    """
    Retrieve public details and profile for a specific user ID.
    Supports frontend client profile lookups (/api/users/<id>/).
    """
    permission_classes = [AllowAny]
    serializer_class = PublicPartnerSerializer

    def get_object(self):
        pk = self.kwargs.get('pk')
        user = generics.get_object_or_404(User, id=pk, is_active=True)
        profile, _ = Profile.objects.get_or_create(user=user)
        return profile


class MyProfileView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update the authenticated user's own profile.
    Supports GET, PUT, and PATCH.
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile


class ProfileCompletionView(APIView):
    """
    Calculates profile completion percentage and highlights missing fields.
    Weighted criteria (20% each):
      1. Name
      2. Headline
      3. Bio
      4. Avatar (uploaded or Google OAuth profile picture)
      5. Skills (at least one assigned)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)

        has_name = bool(profile.name and profile.name.strip())
        has_headline = bool(profile.headline and profile.headline.strip())
        has_bio = bool(profile.bio and profile.bio.strip())
        has_avatar = bool(
            profile.avatar or
            profile.avatar_url or
            (hasattr(request.user, 'google_profile') and request.user.google_profile.picture)
        )
        has_skills = profile.skills.exists()

        breakdown = {
            'name': has_name,
            'headline': has_headline,
            'bio': has_bio,
            'avatar': has_avatar,
            'skills': has_skills,
        }

        score = sum(20 for val in breakdown.values() if val)
        missing_fields = [field for field, completed in breakdown.items() if not completed]

        return Response(
            {
                'completion_percentage': score,
                'is_complete': score == 100,
                'missing_fields': missing_fields,
                'breakdown': breakdown,
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    """
    Request password reset link sent to user's registered email.
    Always returns 200 OK to prevent account enumeration.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        redirect_url = serializer.validated_data.get('redirect_url')

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            send_password_reset_email(user, redirect_url=redirect_url)

        return Response(
            {
                "message": "If an account with this email exists, a password reset link has been sent.",
                "status": "success",
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetValidateView(APIView):
    """
    Validate password reset token and UID before presenting reset password form.
    Supports GET (query parameters) and POST (JSON body).
    """
    permission_classes = [AllowAny]

    def _validate_token(self, data):
        serializer = PasswordResetValidateSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']

        user, is_valid = verify_password_reset_token(uid, token)
        if not is_valid:
            return Response(
                {
                    "valid": False,
                    "message": "The password reset link is invalid or has expired.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "valid": True,
                "uid": uid,
                "username": user.username,
                "message": "Token is valid.",
            },
            status=status.HTTP_200_OK,
        )

    def get(self, request):
        return self._validate_token(request.query_params)

    def post(self, request):
        return self._validate_token(request.data)


class PasswordResetConfirmView(APIView):
    """
    Reset user password using valid token and UID.
    Invalidates prior sessions and provides a new authentication token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        user, is_valid = verify_password_reset_token(uid, token)
        if not is_valid:
            return Response(
                {"detail": "The password reset link is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reset_user_password(user, new_password)
        token_obj, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "message": "Password has been successfully reset. You can now log in with your new password.",
                "token": token_obj.key,
                "status": "success",
            },
            status=status.HTTP_200_OK,
        )


class PasswordChangeView(APIView):
    """
    Change password for currently authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        if not request.user.check_password(old_password):
            return Response(
                {"old_password": ["Current password is incorrect."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(new_password)
        request.user.save()

        return Response(
            {
                "message": "Password changed successfully.",
                "status": "success",
            },
            status=status.HTTP_200_OK,
        )
