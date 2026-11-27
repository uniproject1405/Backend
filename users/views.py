import urllib.parse
from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    ProfileSerializer,
    GoogleAuthSerializer,
)
from .models import Profile
from .services import authenticate_google, get_google_auth_url

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
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return Response({
                "email": request.user.email,
                "username": request.user.username,
                "profile": None,
                "message": "Please complete your profile."
            }, status=status.HTTP_200_OK)

        profile_data = ProfileSerializer(profile).data

        return Response({
            "email": request.user.email,
            "username": request.user.username,
            "profile": profile_data
        }, status=status.HTTP_200_OK)
    
    def patch(self, request):
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return Response({
                "message": "Please create your profile first."
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = ProfileSerializer(
            profile,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()

            return Response({
                "email": request.user.email,
                "username": request.user.username,
                "profile": serializer.data
            }, status=status.HTTP_200_OK)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

class ProfileCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        if Profile.objects.filter(user=request.user).exists():
            return Response(
                {"message": "You already have a profile."},
                status=status.HTTP_409_CONFLICT
            )

        serializer = ProfileSerializer(data=request.data)

        if serializer.is_valid():
            profile = serializer.save()

            return Response({
                "email": request.user.email,
                "username": request.user.username,
                "profile": ProfileSerializer(profile).data,
                "message": "Profile created successfully."
            }, status=status.HTTP_201_CREATED)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )    

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
        except (AuthenticationFailed, ValidationError) as e:
            detail = e.detail if hasattr(e, "detail") else str(e)
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(
                {"detail": "Google authentication failed. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class GoogleLoginRedirectView(APIView):
    """
    Redirect users directly to Google's OAuth 2.0 consent screen.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        state = request.query_params.get("state")
        auth_url = get_google_auth_url(state=state)
        if request.query_params.get("format") == "json":
            return Response({"auth_url": auth_url}, status=status.HTTP_200_OK)
        return HttpResponseRedirect(auth_url)


class GoogleCallbackView(APIView):
    """
    Handles Google OAuth redirect callbacks and forwards token to the frontend.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        code = request.query_params.get("code")
        if not code:
            error = request.query_params.get("error", "No code provided")
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

        try:
            redirect_uri = getattr(settings, "GOOGLE_REDIRECT_URI", "")
            user, token, _ = authenticate_google(code=code, redirect_uri=redirect_uri)
            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
            target_url = (
                f"{frontend_url}/login?"
                f"token={token.key}&email={urllib.parse.quote(user.email)}&username={urllib.parse.quote(user.username)}"
            )
            return HttpResponseRedirect(target_url)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
