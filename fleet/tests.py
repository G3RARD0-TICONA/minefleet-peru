import tempfile
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from core.models import Company, Membership
from .models import ClientProfile, Driver, DriverCredential, RequirementRule, Vehicle, VehicleDocument
from .validators import validate_evidence_file


class FleetFixtureMixin:
    def make_company_profile(self, name="Demo", ruc="20999999991"):
        company = Company.objects.create(name=name, ruc=ruc)
        profile = ClientProfile.objects.create(company=company, name="Perfil minero referencial", source="Prueba", source_version="1.0", effective_date=date.today())
        return company, profile

    def make_vehicle(self, company, profile=None, plate="V0X-001", vin="1MNFLEETD3M000001"):
        return Vehicle.objects.create(company=company, client_profile=profile, plate=plate, vin=vin, brand="Volvo", model="FMX", year=2023, owner_name="Transportista Demo", tare_kg=15000, gross_weight_kg=41000)


class FleetComplianceTests(FleetFixtureMixin, TestCase):
    def setUp(self):
        self.company, self.profile = self.make_company_profile()
        for evidence in (VehicleDocument.Type.CITV, VehicleDocument.Type.SOAT, VehicleDocument.Type.SUNARP):
            RequirementRule.objects.create(client_profile=self.profile, code=f"VEH-{evidence}", subject="VEHICLE", evidence_type=evidence, description=f"{evidence} vigente", blocking=True, minimum_verification="VERIFIED", legal_or_client_source="Matriz", source_version="1.0")
        self.vehicle = self.make_vehicle(self.company, self.profile)

    def add_document(self, kind):
        return VehicleDocument.objects.create(vehicle=self.vehicle, document_type=kind, expiry_date=date.today() + timedelta(days=90), verification_level="VERIFIED")

    def test_payload_is_calculated(self):
        self.assertEqual(self.vehicle.payload_kg, 26000)

    def test_gross_weight_cannot_be_less_than_tare(self):
        self.vehicle.gross_weight_kg = 10000
        with self.assertRaises(ValidationError):
            self.vehicle.save()

    def test_vehicle_requires_all_blocking_evidence(self):
        self.assertEqual(self.vehicle.status, Vehicle.Status.BLOCKED)
        for kind in (VehicleDocument.Type.CITV, VehicleDocument.Type.SOAT, VehicleDocument.Type.SUNARP):
            self.add_document(kind)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, Vehicle.Status.ELIGIBLE)

    def test_expired_document_revokes_eligibility(self):
        documents = [self.add_document(kind) for kind in (VehicleDocument.Type.CITV, VehicleDocument.Type.SOAT, VehicleDocument.Type.SUNARP)]
        documents[0].expiry_date = date.today() - timedelta(days=1)
        documents[0].save()
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, Vehicle.Status.BLOCKED)

    def test_driver_requires_medical_exam_and_credentials(self):
        RequirementRule.objects.create(client_profile=self.profile, code="DRV-IND", subject="DRIVER", evidence_type=DriverCredential.Type.INDUCTION, description="Inducción vigente", blocking=True, minimum_verification="VERIFIED", legal_or_client_source="Matriz", source_version="1.0")
        driver = Driver.objects.create(company=self.company, client_profile=self.profile, document_number="70000001", first_names="Ana", last_names="Prueba", license_number="Q70000001", license_expiry=date.today() + timedelta(days=90))
        self.assertFalse(driver.is_authorized)
        driver.medical_expiry = date.today() + timedelta(days=90)
        driver.save()
        DriverCredential.objects.create(driver=driver, credential_type=DriverCredential.Type.INDUCTION, expiry_date=date.today() + timedelta(days=90), verification_level="VERIFIED")
        self.assertTrue(driver.is_authorized)


class EvidenceValidationTests(TestCase):
    def test_rejects_disguised_file(self):
        with self.assertRaises(ValidationError):
            validate_evidence_file(SimpleUploadedFile("evidencia.pdf", b"MZ executable"))

    def test_accepts_pdf_signature(self):
        validate_evidence_file(SimpleUploadedFile("evidencia.pdf", b"%PDF-1.7\ncontenido"))


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class AccessTests(FleetFixtureMixin, TestCase):
    def setUp(self):
        self.company, self.profile = self.make_company_profile()
        self.other_company, _ = self.make_company_profile("Otra", "20999999992")
        self.vehicle = self.make_vehicle(self.company, self.profile)
        self.other_vehicle = self.make_vehicle(self.other_company, None, "O0X-001", "1MNFLEETD3M000002")
        self.user = get_user_model().objects.create_user("operador", password="test-pass-123")
        Membership.objects.create(user=self.user, company=self.company, role=Membership.Role.OPERATIONS)

    def test_anonymous_user_is_redirected(self):
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_member_cannot_read_other_company_vehicle(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(f"/vehiculos/{self.other_vehicle.pk}/").status_code, 404)

    def test_operations_cannot_upload_compliance_document(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(f"/vehiculos/{self.vehicle.pk}/documentos/nuevo/").status_code, 403)

    def test_viewer_cannot_download_sensitive_evidence(self):
        viewer = get_user_model().objects.create_user("visor", password="test-pass-123")
        Membership.objects.create(user=viewer, company=self.company, role=Membership.Role.VIEWER)
        document = VehicleDocument.objects.create(vehicle=self.vehicle, document_type="CITV", expiry_date=date.today() + timedelta(days=90), file=SimpleUploadedFile("citv.pdf", b"%PDF-1.7\ncontenido"))
        self.client.force_login(viewer)
        self.assertEqual(self.client.get(f"/documentos/{document.pk}/descargar/").status_code, 403)

    def test_company_switch_rejects_non_member(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.post("/empresa/cambiar/", {"company_id": self.other_company.pk}).status_code, 404)
