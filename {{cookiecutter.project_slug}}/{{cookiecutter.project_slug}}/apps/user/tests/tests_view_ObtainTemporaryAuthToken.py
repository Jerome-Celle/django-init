import json

from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from {{cookiecutter.project_slug}}.factories import UserFactory
from ..models import TemporaryToken

User = get_user_model()


class ObtainTemporaryAuthTokenTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.user.set_password('Test123!')
        self.user.save()
        self.url = reverse('token_api')

    def test_authenticate_email(self):
        """
        Ensure we can authenticate on the platform.
        """
        data = {
            'email': self.user.email,
            'password': 'Test123!'
        }

        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        token = TemporaryToken.objects.get(
            user__email=self.user.email,
        )
        self.assertContains(response, token)

    def test_authenticate(self):
        """
        Ensure we can authenticate on the platform using a email.
        """
        data = {
            'email': self.user.email,
            'password': 'Test123!'
        }

        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        token = TemporaryToken.objects.get(
            user__email=self.user.email,
        )
        self.assertContains(response, token)

    def test_authenticate_expired_token(self):
        """
        Ensure we can authenticate on the platform when token is expired.
        """
        data = {
            'email': self.user.email,
            'password': 'Test123!'
        }

        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        token_old = TemporaryToken.objects.get(
            user__email=self.user.email,
        )
        token_old.expire()

        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        token_new = TemporaryToken.objects.get(
            user__email=self.user.email,
        )

        self.assertNotContains(response, token_old)
        self.assertContains(response, token_new)

    def test_authenticate_bad_password(self):
        """
        Ensure we can't authenticate with a wrong password'
        """
        data = {
            'email': self.user.email,
            'password': 'test123!'  # No caps on the first letter
        }

        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        tokens = TemporaryToken.objects.filter(
            user__email=self.user.email
        ).count()
        self.assertEqual(0, tokens)

    def test_authenticate_bad_email(self):
        """
        Ensure we can't authenticate with a wrong email
        """
        data = {
            'email': 'Jon@john',  # Forget the `h` in `John`
            'password': 'Test123!'
        }

        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        tokens = TemporaryToken.objects.filter(
            user__email=self.user.email
        ).count()
        self.assertEqual(0, tokens)

    def test_authenticate_inactive(self):
        """
        Ensure we can't authenticate if user is inactive
        """
        data = {
            'email': self.user.email,
            'password': 'Test123!'
        }

        User.objects.filter(id=self.user.id).update(is_active=False)

        response = self.client.post(self.url, data, format='json')

        content = {
            "non_field_errors": [
                "Unable to log in with provided credentials."
            ]
        }

        self.assertEqual(json.loads(response.content), content)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        tokens = TemporaryToken.objects.filter(
            user__email=self.user.email
        ).count()
        self.assertEqual(0, tokens)

    def test_authenticate_missing_parameter(self):
        """
        Ensure we can't authenticate if "email" or "password" are not
        provided.
        """
        response = self.client.post(self.url, {}, format='json')

        content = {
            'password': ['This field is required.'],
            'email': ['This field is required.']
        }

        self.assertEqual(json.loads(response.content), content)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        tokens = TemporaryToken.objects.filter(
            user__email=self.user.email
        ).count()
        self.assertEqual(0, tokens)
