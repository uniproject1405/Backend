from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authtoken.models import Token
from projects.models import Skill
from users.models import GoogleProfile, Profile
from users.services import generate_password_reset_token

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


class UserRegistrationTests(TestCase):
    def test_register_user_with_at_symbol_username(self):
        payload = {
            "username": "@ninacoder",
            "email": "nina@example.com",
            "password": "strongPassword123",
        }
        response = self.client.post("/api/users/register/", payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["user"]["username"], "ninacoder")

    def test_register_user_invalid_only_at_username(self):
        payload = {
            "username": "@",
            "email": "atonly@example.com",
            "password": "strongPassword123",
        }
        response = self.client.post("/api/users/register/", payload, content_type="application/json")
        self.assertEqual(response.status_code, 400)


class GoogleAuthTests(TestCase):
    def setUp(self):
        self.endpoint = "/api/users/google/"

    @patch("users.services.verify_id_token")
    def test_signup_new_user_via_id_token(self, mock_verify):
        mock_verify.return_value = {
            "email": "alex.doe@example.com",
            "email_verified": True,
            "name": "Alex Doe",
            "sub": "google-uid-1001",
            "picture": "https://example.com/avatar.jpg",
        }

        response = self.client.post(self.endpoint, {"id_token": "valid_mock_token"}, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)
        self.assertTrue(data["is_new_user"])
        self.assertEqual(data["user"]["email"], "alex.doe@example.com")
        self.assertEqual(data["user"]["username"], "alex_doe")

        user = User.objects.get(email="alex.doe@example.com")
        self.assertFalse(user.has_usable_password())

        profile = GoogleProfile.objects.get(user=user)
        self.assertEqual(profile.google_id, "google-uid-1001")
        self.assertEqual(profile.picture, "https://example.com/avatar.jpg")

    @patch("users.services.verify_id_token")
    def test_login_existing_user_via_id_token(self, mock_verify):
        user = User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password="securePassword123",
        )
        existing_token = Token.objects.create(user=user)

        mock_verify.return_value = {
            "email": "existing@example.com",
            "email_verified": True,
            "sub": "google-uid-1002",
        }

        response = self.client.post(self.endpoint, {"id_token": "valid_mock_token"}, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["is_new_user"])
        self.assertEqual(data["token"], existing_token.key)
        self.assertEqual(data["user"]["email"], "existing@example.com")
        self.assertEqual(data["user"]["username"], "existinguser")

    @patch("users.services.verify_access_token")
    def test_auth_via_access_token(self, mock_verify):
        mock_verify.return_value = {
            "email": "access.user@example.com",
            "email_verified": True,
            "name": "Access User",
            "sub": "google-uid-1003",
        }

        response = self.client.post(
            self.endpoint,
            {"access_token": "mock_access_token"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["is_new_user"])
        self.assertEqual(data["user"]["email"], "access.user@example.com")

    @patch("users.services.exchange_auth_code")
    def test_auth_via_authorization_code(self, mock_exchange):
        mock_exchange.return_value = {
            "email": "code.user@example.com",
            "email_verified": True,
            "name": "Code User",
            "sub": "google-uid-1004",
        }

        response = self.client.post(
            self.endpoint,
            {"code": "auth_code_sample", "redirect_uri": "http://localhost:5173/auth/callback"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["is_new_user"])
        self.assertEqual(data["user"]["email"], "code.user@example.com")

    def test_missing_credentials_fails(self):
        response = self.client.post(self.endpoint, {}, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    @patch("users.services.verify_id_token")
    def test_unverified_email_fails(self, mock_verify):
        mock_verify.return_value = {
            "email": "unverified@example.com",
            "email_verified": False,
            "sub": "google-uid-1005",
        }

        response = self.client.post(self.endpoint, {"id_token": "token"}, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    @patch("users.services.verify_id_token")
    def test_invalid_token_fails(self, mock_verify):
        mock_verify.side_effect = AuthenticationFailed("Invalid Google ID token.")

        response = self.client.post(self.endpoint, {"id_token": "bad_token"}, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    @patch("users.services.verify_id_token")
    def test_inactive_user_fails(self, mock_verify):
        User.objects.create_user(
            username="disableduser",
            email="disabled@example.com",
            password="password123",
            is_active=False,
        )

        mock_verify.return_value = {
            "email": "disabled@example.com",
            "email_verified": True,
            "sub": "google-uid-1006",
        }

        response = self.client.post(self.endpoint, {"id_token": "valid_token"}, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_google_login_redirect_url_generation(self):
        response = self.client.get("/api/users/google/login/?format=json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("auth_url", response.json())
        self.assertIn("accounts.google.com", response.json()["auth_url"])

    @patch("users.views.authenticate_google")
    def test_google_callback_success(self, mock_auth):
        user = User.objects.create_user(
            username="callbackuser",
            email="callback@example.com",
            password="password123",
        )
        token = Token.objects.create(user=user)
        mock_auth.return_value = (user, token, False)

        response = self.client.get("/api/users/google/callback/?code=mock_code")
        self.assertEqual(response.status_code, 302)
        self.assertIn(token.key, response.url)

    def test_google_callback_error(self):
        response = self.client.get("/api/users/google/callback/?error=access_denied")
        self.assertEqual(response.status_code, 302)
        self.assertIn("error=access_denied", response.url)


class PartnerExploreTests(TestCase):
    def setUp(self):
        self.skill_python = Skill.objects.create(name="Python")
        self.skill_react = Skill.objects.create(name="React")
        self.skill_django = Skill.objects.create(name="Django")

        # User 1: Python mentor and collaborator
        self.user1 = User.objects.create_user(
            username="user_mentor",
            email="mentor@example.com",
            password="password123",
        )
        self.profile1, _ = Profile.objects.get_or_create(user=self.user1)
        self.profile1.name = "John Mentor"
        self.profile1.headline = "Senior Python Architect"
        self.profile1.bio = "Passionate about backend architectures and mentoring."
        self.profile1.open_to_collaboration = True
        self.profile1.open_to_mentoring = True
        self.profile1.contact_links = [{"telegram": "@johnmentor"}]
        self.profile1.save()
        self.profile1.skills.set([self.skill_python, self.skill_django])

        # User 2: React frontend collaborator, not a mentor
        self.user2 = User.objects.create_user(
            username="user_dev",
            email="dev@example.com",
            password="password123",
        )
        self.profile2, _ = Profile.objects.get_or_create(user=self.user2)
        self.profile2.name = "Sara Developer"
        self.profile2.headline = "Frontend React Specialist"
        self.profile2.bio = "Building responsive interfaces."
        self.profile2.open_to_collaboration = True
        self.profile2.open_to_mentoring = False
        self.profile2.save()
        self.profile2.skills.set([self.skill_react])

        # User 3: Inactive user
        self.user_inactive = User.objects.create_user(
            username="inactive_user",
            email="inactive@example.com",
            password="password123",
            is_active=False,
        )
        self.profile_inactive, _ = Profile.objects.get_or_create(user=self.user_inactive)
        self.profile_inactive.name = "Inactive Person"
        self.profile_inactive.save()

    def test_explore_list_returns_active_users(self):
        response = self.client.get("/api/users/explore/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        usernames = [item["username"] for item in data]
        self.assertIn("user_mentor", usernames)
        self.assertIn("user_dev", usernames)
        self.assertNotIn("inactive_user", usernames)

    def test_explore_filter_by_skill_name(self):
        response = self.client.get("/api/users/explore/?skill=Python")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["username"], "user_mentor")

    def test_explore_filter_by_skill_id(self):
        response = self.client.get(f"/api/users/explore/?skill={self.skill_react.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["username"], "user_dev")

    def test_explore_filter_collaboration(self):
        self.profile2.open_to_collaboration = False
        self.profile2.save()

        response = self.client.get("/api/users/explore/?collaboration=true")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["username"], "user_mentor")

    def test_explore_filter_mentoring(self):
        response = self.client.get("/api/users/explore/?mentoring=true")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["username"], "user_mentor")

    def test_explore_search_filter(self):
        response = self.client.get("/api/users/explore/?search=Senior")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["username"], "user_mentor")

    def test_explore_search_by_username_with_at(self):
        response = self.client.get("/api/users/explore/?search=@user_dev")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data), 1)
        self.assertEqual(data[0]["username"], "user_dev")

    def test_explore_discover_alias(self):
        response = self.client.get("/api/users/discover/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)

    def test_explore_privacy_no_private_email_exposed(self):
        response = self.client.get("/api/users/explore/")
        self.assertEqual(response.status_code, 200)
        for user_data in response.json():
            self.assertNotIn("email", user_data)
            self.assertIn("user_id", user_data)
            self.assertIn("username", user_data)


class PublicProfileDetailTests(TestCase):
    def setUp(self):
        self.skill = Skill.objects.create(name="Go")
        self.user = User.objects.create_user(
            username="public_test_user",
            email="secret@example.com",
            password="password123",
        )
        self.profile, _ = Profile.objects.get_or_create(user=self.user)
        self.profile.name = "Public Person"
        self.profile.headline = "Cloud Engineer"
        self.profile.bio = "Building high-performance cloud applications."
        self.profile.contact_links = [{"github": "https://github.com/publicperson"}]
        self.profile.save()
        self.profile.skills.set([self.skill])

    def test_public_profile_detail_success(self):
        response = self.client.get(f"/api/users/{self.user.id}/profile/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["username"], "public_test_user")
        self.assertEqual(data["name"], "Public Person")
        self.assertEqual(data["headline"], "Cloud Engineer")
        self.assertEqual(data["github"], "https://github.com/publicperson")
        self.assertEqual(len(data["skills"]), 1)
        self.assertEqual(data["skills"][0]["name"], "Go")
        self.assertNotIn("email", data)

    def test_user_detail_endpoint_success(self):
        response = self.client.get(f"/api/users/{self.user.id}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["username"], "public_test_user")
        self.assertIn("profile", data)
        self.assertEqual(data["profile"]["name"], "Public Person")

    def test_public_profile_inactive_user_404(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.get(f"/api/users/{self.user.id}/profile/")
        self.assertEqual(response.status_code, 404)

    def test_public_profile_nonexistent_user_404(self):
        response = self.client.get("/api/users/999999/profile/")
        self.assertEqual(response.status_code, 404)


class MyProfileManageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="myprofile_user",
            email="myprofile@example.com",
            password="securePassword123",
        )
        self.token = Token.objects.create(user=self.user)
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Token {self.token.key}"}
        self.skill1 = Skill.objects.create(name="Django")
        self.skill2 = Skill.objects.create(name="PostgreSQL")

    def test_get_own_profile_authenticated(self):
        response = self.client.get("/api/users/profile/", **self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["username"], "myprofile_user")
        self.assertEqual(data["email"], "myprofile@example.com")

    def test_get_own_profile_unauthenticated_fails(self):
        response = self.client.get("/api/users/profile/")
        self.assertEqual(response.status_code, 401)

    def test_patch_own_profile_fields(self):
        payload = {
            "name": "Updated Name",
            "headline": "Full-Stack Web Dev",
            "bio": "Extensive experience in Django REST framework.",
            "open_to_collaboration": True,
            "open_to_mentoring": True,
        }
        response = self.client.patch(
            "/api/users/profile/",
            payload,
            content_type="application/json",
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Updated Name")
        self.assertEqual(data["headline"], "Full-Stack Web Dev")
        self.assertTrue(data["open_to_collaboration"])
        self.assertTrue(data["open_to_mentoring"])

        # Verify DB persistence
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.name, "Updated Name")

    def test_update_profile_skills_by_id(self):
        payload = {
            "skills": [self.skill1.id, self.skill2.id],
        }
        response = self.client.patch(
            "/api/users/profile/",
            payload,
            content_type="application/json",
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.skills.count(), 2)

    def test_update_profile_skills_by_name(self):
        payload = {
            "skills_names": ["Kubernetes", "Docker"],
        }
        response = self.client.patch(
            "/api/users/profile/",
            payload,
            content_type="application/json",
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        profile = Profile.objects.get(user=self.user)
        skill_names = list(profile.skills.values_list("name", flat=True))
        self.assertIn("Kubernetes", skill_names)
        self.assertIn("Docker", skill_names)

    def test_update_profile_valid_contact_links(self):
        payload = {
            "contact_links": [
                {"github": "https://github.com/myprofile"},
                {"telegram": "@myhandle"},
                {"email": "reachme@example.com"},
            ]
        }
        response = self.client.patch(
            "/api/users/profile/",
            payload,
            content_type="application/json",
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["contact_links"]), 3)

    def test_update_profile_invalid_contact_links(self):
        payload = {
            "contact_links": [
                {"invalid_platform": "not-a-valid-url-or-handle"},
            ]
        }
        response = self.client.patch(
            "/api/users/profile/",
            payload,
            content_type="application/json",
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_update_profile_valid_instagram_contact_links(self):
        payload = {
            "contact_links": [
                {"instagram": "@my_insta_handle"},
                {"instagram": "https://instagram.com/my_insta_handle"},
            ]
        }
        response = self.client.patch(
            "/api/users/profile/",
            payload,
            content_type="application/json",
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)

    def test_update_profile_invalid_instagram_contact_links(self):
        payload = {
            "contact_links": [
                {"instagram": "invalid-insta-without-at-or-url"},
            ]
        }
        response = self.client.patch(
            "/api/users/profile/",
            payload,
            content_type="application/json",
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 400)


class CurrentUserAndCompletionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="current_test_user",
            email="current@example.com",
            password="password123",
        )
        self.token = Token.objects.create(user=self.user)
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Token {self.token.key}"}

    def test_current_user_me_get_includes_profile(self):
        response = self.client.get("/api/users/me/", **self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["username"], "current_test_user")
        self.assertEqual(data["email"], "current@example.com")
        self.assertIn("profile", data)

    def test_current_user_me_patch(self):
        payload = {
            "first_name": "Modern",
            "last_name": "Dev",
            "bio": "Working with React and Django.",
            "telegram": "@moderndev",
        }
        response = self.client.patch(
            "/api/users/me/",
            payload,
            content_type="application/json",
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Modern")
        self.assertEqual(self.user.last_name, "Dev")

        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.bio, "Working with React and Django.")
        self.assertEqual(profile.telegram, "@moderndev")

    def test_current_user_me_patch_with_instagram(self):
        payload = {
            "first_name": "Modern",
            "last_name": "Dev",
            "bio": "Working with React and Django.",
            "telegram": "@moderndev",
            "instagram": "@modern_insta",
        }
        response = self.client.patch(
            "/api/users/me/",
            payload,
            content_type="application/json",
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)

        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.telegram, "@moderndev")
        self.assertEqual(profile.instagram, "@modern_insta")

    def test_profile_completion_unauthenticated_401(self):
        response = self.client.get("/api/users/profile/completion/")
        self.assertEqual(response.status_code, 401)

    def test_profile_completion_calculation(self):
        # Initial empty profile: completion should be 0%
        response = self.client.get("/api/users/profile/completion/", **self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["completion_percentage"], 0)
        self.assertFalse(data["is_complete"])
        self.assertEqual(len(data["missing_fields"]), 5)

        # Update name and headline (+40%)
        profile = Profile.objects.get(user=self.user)
        profile.name = "My Full Name"
        profile.headline = "Software Engineer"
        profile.save()

        response = self.client.get("/api/users/profile/completion/", **self.auth_headers)
        self.assertEqual(response.json()["completion_percentage"], 40)

        # Update bio and avatar_url (+40% => 80%)
        profile.bio = "Detailed bio description."
        profile.avatar_url = "https://example.com/pic.png"
        profile.save()

        response = self.client.get("/api/users/profile/completion/", **self.auth_headers)
        self.assertEqual(response.json()["completion_percentage"], 80)

        # Add skill (+20% => 100%)
        skill = Skill.objects.create(name="FastAPI")
        profile.skills.add(skill)

        response = self.client.get("/api/users/profile/completion/", **self.auth_headers)
        data = response.json()
        self.assertEqual(data["completion_percentage"], 100)
        self.assertTrue(data["is_complete"])
        self.assertEqual(data["missing_fields"], [])


class PasswordResetRequestTests(TestCase):
    def setUp(self):
        self.endpoint = "/api/users/password-reset/"
        self.user = User.objects.create_user(
            username="resetuser",
            email="reset.user@example.com",
            password="originalPassword123",
        )

    def test_request_reset_valid_active_user(self):
        response = self.client.post(
            self.endpoint,
            {"email": "reset.user@example.com"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

        # Verify email was dispatched to outbox
        self.assertEqual(len(mail.outbox), 1)
        email_msg = mail.outbox[0]
        self.assertEqual(email_msg.to, ["reset.user@example.com"])
        self.assertIn("بازیابی رمز عبور", email_msg.subject)
        self.assertIn("uid=", email_msg.body)
        self.assertIn("token=", email_msg.body)

    def test_request_reset_case_insensitive_email(self):
        response = self.client.post(
            self.endpoint,
            {"email": "RESET.USER@EXAMPLE.COM"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["reset.user@example.com"])

    def test_request_reset_nonexistent_email_does_not_leak_enumeration(self):
        response = self.client.post(
            self.endpoint,
            {"email": "nonexistent@example.com"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(len(mail.outbox), 0)

    def test_request_reset_inactive_user(self):
        self.user.is_active = False
        self.user.save()

        response = self.client.post(
            self.endpoint,
            {"email": "reset.user@example.com"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_request_reset_invalid_email_format(self):
        response = self.client.post(
            self.endpoint,
            {"email": "not-a-valid-email"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())

    def test_request_reset_custom_redirect_url(self):
        custom_url = "https://myapp.com/auth/new-password"
        response = self.client.post(
            self.endpoint,
            {
                "email": "reset.user@example.com",
                "redirect_url": custom_url,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(custom_url, mail.outbox[0].body)


class PasswordResetValidateTests(TestCase):
    def setUp(self):
        self.endpoint = "/api/users/password-reset/validate/"
        self.user = User.objects.create_user(
            username="validatetest",
            email="validate@example.com",
            password="securePassword123",
        )
        self.uid, self.token = generate_password_reset_token(self.user)

    def test_validate_token_success_post(self):
        response = self.client.post(
            self.endpoint,
            {"uid": self.uid, "token": self.token},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["valid"])
        self.assertEqual(data["username"], "validatetest")

    def test_validate_token_success_get(self):
        response = self.client.get(
            f"{self.endpoint}?uid={self.uid}&token={self.token}",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["valid"])

    def test_validate_token_invalid_token(self):
        response = self.client.post(
            self.endpoint,
            {"uid": self.uid, "token": "invalid-tampered-token"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["valid"])

    def test_validate_token_invalid_uid(self):
        response = self.client.post(
            self.endpoint,
            {"uid": "invalid-uid-b64", "token": self.token},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["valid"])

    def test_validate_token_inactive_user(self):
        self.user.is_active = False
        self.user.save()

        response = self.client.post(
            self.endpoint,
            {"uid": self.uid, "token": self.token},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["valid"])


class PasswordResetConfirmTests(TestCase):
    def setUp(self):
        self.endpoint = "/api/users/password-reset/confirm/"
        self.user = User.objects.create_user(
            username="confirmuser",
            email="confirm@example.com",
            password="initialPassword123",
        )
        self.token_initial = Token.objects.create(user=self.user)
        self.uid, self.reset_token = generate_password_reset_token(self.user)

    def test_confirm_password_reset_success(self):
        payload = {
            "uid": self.uid,
            "token": self.reset_token,
            "new_password": "brandNewPassword999",
            "confirm_password": "brandNewPassword999",
        }
        response = self.client.post(
            self.endpoint,
            payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("token", data)

        # Check DB that password was updated
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("brandNewPassword999"))
        self.assertFalse(self.user.check_password("initialPassword123"))

        # Verify old token was revoked/replaced
        self.assertNotEqual(data["token"], self.token_initial.key)

        # Token cannot be reused a second time (one-time usage!)
        second_attempt = self.client.post(
            self.endpoint,
            payload,
            content_type="application/json",
        )
        self.assertEqual(second_attempt.status_code, 400)

    def test_confirm_password_reset_mismatched_passwords(self):
        payload = {
            "uid": self.uid,
            "token": self.reset_token,
            "new_password": "passwordA123",
            "confirm_password": "passwordB123",
        }
        response = self.client.post(
            self.endpoint,
            payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("confirm_password", response.json())

    def test_confirm_password_reset_short_password(self):
        payload = {
            "uid": self.uid,
            "token": self.reset_token,
            "new_password": "short",
            "confirm_password": "short",
        }
        response = self.client.post(
            self.endpoint,
            payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_confirm_password_reset_invalid_or_expired_token(self):
        payload = {
            "uid": self.uid,
            "token": "expired-or-tampered-token",
            "new_password": "validNewPassword123",
            "confirm_password": "validNewPassword123",
        }
        response = self.client.post(
            self.endpoint,
            payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


class PasswordChangeTests(TestCase):
    def setUp(self):
        self.endpoint = "/api/users/password-change/"
        self.user = User.objects.create_user(
            username="changepassworduser",
            email="change@example.com",
            password="currentPassword123",
        )
        self.token = Token.objects.create(user=self.user)
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Token {self.token.key}"}

    def test_change_password_authenticated_success(self):
        payload = {
            "old_password": "currentPassword123",
            "new_password": "updatedPassword456",
            "confirm_password": "updatedPassword456",
        }
        response = self.client.post(
            self.endpoint,
            payload,
            content_type="application/json",
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("updatedPassword456"))

    def test_change_password_wrong_old_password(self):
        payload = {
            "old_password": "wrongPassword123",
            "new_password": "updatedPassword456",
            "confirm_password": "updatedPassword456",
        }
        response = self.client.post(
            self.endpoint,
            payload,
            content_type="application/json",
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("old_password", response.json())

    def test_change_password_mismatched_confirmation(self):
        payload = {
            "old_password": "currentPassword123",
            "new_password": "updatedPassword456",
            "confirm_password": "differentPassword789",
        }
        response = self.client.post(
            self.endpoint,
            payload,
            content_type="application/json",
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("confirm_password", response.json())

    def test_change_password_unauthenticated_fails(self):
        payload = {
            "old_password": "currentPassword123",
            "new_password": "updatedPassword456",
            "confirm_password": "updatedPassword456",
        }
        response = self.client.post(
            self.endpoint,
            payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

