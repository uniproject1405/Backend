import re
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from .models import Profile, ProfileSkill, GoogleProfile
from .utils import is_profile_complete
from .permissions import IsProfileComplete
from .services import get_or_create_google_user

User = get_user_model()


class UsersAPITest(TestCase):
    def test_users_api_returns_success(self):
        response = self.client.get("/api/users/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "message": "API is working!",
                "status": "success",
            },
        )


class GoogleAuthAndProfileViewerTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.skill = ProfileSkill.objects.create(name="Python")

    def test_google_login_generates_random_unique_username(self):
        """When logging in with Google, assign a temporary random unique username."""
        profile_data = {
            "email": "testuser@gmail.com",
            "email_verified": True,
            "sub": "google-123456",
            "name": "Ali Rezaei",
            "picture": "https://example.com/photo.jpg",
        }
        user, token, is_new = get_or_create_google_user(profile_data)

        self.assertTrue(is_new)
        # Username must be random and unique like user_xxxxxxxx (not based on Google name)
        self.assertTrue(re.fullmatch(r"user_[0-9a-f]{8}", user.username))
        self.assertNotEqual(user.username, "ali_rezaei")
        self.assertEqual(user.email, "testuser@gmail.com")

        # GoogleProfile must save initial_username
        self.assertTrue(hasattr(user, "google_profile"))
        self.assertEqual(user.google_profile.initial_username, user.username)

    def test_google_user_is_viewer_mode_initially(self):
        """A user registered via Google stays in Viewer mode if username is not customized."""
        profile_data = {
            "email": "google_new@gmail.com",
            "email_verified": True,
            "sub": "google-99999",
            "name": "Sarah Rad",
        }
        user, token, _ = get_or_create_google_user(profile_data)
        profile = user.profile

        # Profile has name from Google, but skills are not selected yet and username is still random
        self.assertFalse(is_profile_complete(profile))

        # Even if skills are added, if username is still the random initial username -> remains Viewer (False)
        profile.skills.add(self.skill)
        self.assertFalse(is_profile_complete(profile))

    def test_google_user_exits_viewer_mode_when_username_changed_and_profile_complete(self):
        """Once the user changes their username AND fills name and skills, they exit viewer mode."""
        profile_data = {
            "email": "sarah.dev@gmail.com",
            "email_verified": True,
            "sub": "google-88888",
            "name": "Sarah Rad",
        }
        user, token, _ = get_or_create_google_user(profile_data)
        profile = user.profile
        profile.skills.add(self.skill)

        # Still random username -> False
        self.assertFalse(is_profile_complete(profile))

        # User changes username to custom handle
        user.username = "sarah_rad"
        user.save()

        # Refresh profile
        profile.refresh_from_db()

        # Now username is customized AND name and skills are present -> Exits viewer mode (True)
        self.assertTrue(is_profile_complete(profile))

    def test_is_profile_complete_permission_viewer_access(self):
        """IsProfileComplete permission allows GET (viewer) but rejects unsafe methods if incomplete."""
        profile_data = {
            "email": "viewer_user@gmail.com",
            "email_verified": True,
            "sub": "google-77777",
            "name": "Viewer Only",
        }
        user, token, _ = get_or_create_google_user(profile_data)
        permission = IsProfileComplete()

        # SAFE_METHODS (GET) -> Allowed (Viewer access)
        get_request = self.factory.get("/api/projects/")
        get_request.user = user
        self.assertTrue(permission.has_permission(get_request, None))

        # Unsafe methods (POST) -> Denied until profile is complete and username customized
        post_request = self.factory.post("/api/projects/")
        post_request.user = user
        self.assertFalse(permission.has_permission(post_request, None))

        # Complete profile: change username and add skills
        user.username = "viewer_custom"
        user.save()
        user.profile.skills.add(self.skill)

        # Now POST is permitted!
        self.assertTrue(permission.has_permission(post_request, None))
