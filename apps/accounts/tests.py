from django.test import TestCase
from django.urls import reverse
from .models import User


class AccountFlowTests(TestCase):
    def test_patient_registration(self):
        response = self.client.post(
            reverse("accounts:register_patient"),
            {
                "full_name": "Pat One",
                "email": "pat@example.com",
                "phone": "12345",
                "password": "StrongPass123!",
                "dob": "1999-01-01",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email="pat@example.com", role=User.Role.PATIENT).exists())
