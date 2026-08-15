from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import Company, Membership
from .models import Driver, Vehicle, VehicleDocument


class FleetModelTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Demo", ruc="20999999991")
        self.vehicle = Vehicle.objects.create(company=self.company, plate="V0X-001", vin="1MNFLEETDEMO0001", brand="Volvo", model="FMX", year=2023, owner_name="Demo", tare_kg=15000, gross_weight_kg=41000)

    def test_payload_is_calculated(self):
        self.assertEqual(self.vehicle.payload_kg, 26000)

    def test_gross_weight_cannot_be_less_than_tare(self):
        self.vehicle.gross_weight_kg = 10000
        with self.assertRaises(ValidationError):
            self.vehicle.save()

    def test_document_expiry_states(self):
        expired = VehicleDocument(vehicle=self.vehicle, document_type=VehicleDocument.Type.CITV, expiry_date=date.today()-timedelta(days=1))
        self.assertEqual(expired.refresh_status(), VehicleDocument.Status.EXPIRED)
        expiring = VehicleDocument(vehicle=self.vehicle, document_type=VehicleDocument.Type.SOAT, expiry_date=date.today()+timedelta(days=10))
        self.assertEqual(expiring.refresh_status(), VehicleDocument.Status.EXPIRING)


class AccessTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Demo", ruc="20999999991")
        self.user = get_user_model().objects.create_user("operador", password="test-pass-123")
        Membership.objects.create(user=self.user, company=self.company, role=Membership.Role.OPERATIONS)

    def test_authenticated_member_can_open_dashboard(self):
        self.client.login(username="operador", password="test-pass-123")
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_anonymous_user_is_redirected(self):
        self.assertEqual(self.client.get("/").status_code, 302)

# Create your tests here.
