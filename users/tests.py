
from django.test import TestCase


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

