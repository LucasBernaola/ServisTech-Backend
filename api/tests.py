from django.urls import reverse
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from usuarios.models import UserProfile


class RegisterViewTests(APITestCase):
    def test_user_registration(self):
        url = reverse('register')
        data = {
            'username': 'newuser',
            'password': 'pass1234',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new@example.com',
            'userprofile': {
                'dni': '99999999',
                'direccion': 'Street 1',
                'celular': '555'
            }
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username='newuser').exists())
        profile = UserProfile.objects.get(user__username='newuser')
        self.assertEqual(profile.dni, '99999999')


class AuthenticationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='authuser', password='pass1234')
        UserProfile.objects.create(user=self.user, rol='cliente')

    def test_obtain_token_and_use_cookie(self):
        url = reverse('token_obtain_pair')
        response = self.client.post(
            url,
            {'username': 'authuser', 'password': 'pass1234'},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.cookies)
        self.assertEqual(response.data['message'], 'Login exitoso')

        profile_url = reverse('profile')
        response = self.client.put(
            profile_url,
            {
                'username': 'authuser',
                'userprofile': {'direccion': 'Updated'}
            },
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.userprofile.direccion, 'Updated')

