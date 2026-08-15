from datetime import date, timedelta
import os
import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import Company, Membership
from fleet.models import ClientProfile, Driver, DriverCredential, RequirementRule, Vehicle, VehicleDocument


class Command(BaseCommand):
    help = "Crea una empresa y datos ficticios seguros para demostración."

    def handle(self, *args, **options):
        company, _ = Company.objects.get_or_create(
            ruc="20999999991",
            defaults={"name": "Transportes Demo Arequipa S.A.C.", "trade_name": "Flota Demo Sur", "region": "Arequipa"},
        )
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(username="admin_demo", defaults={"email": "demo@example.invalid"})
        if created:
            demo_password = os.environ.get("MINEFLEET_DEMO_PASSWORD") or secrets.token_urlsafe(16)
            user.set_password(demo_password)
            user.save()
        Membership.objects.update_or_create(user=user, company=company, defaults={"role": Membership.Role.ADMIN, "active": True})

        profile, _ = ClientProfile.objects.get_or_create(
            company=company, name="Perfil Minero Referencial", operation="Piloto de investigación",
            defaults={"source":"MINEM, Reglamento de Seguridad y Salud Ocupacional en Minería, edición 2026", "source_version":"2026", "effective_date":date(2026, 3, 27), "reviewed_at":date.today()},
        )
        requirement_specs = [
            ("VEH-CITV", "VEHICLE", "CITV", "CITV vigente", "DOCUMENTED"),
            ("VEH-SOAT", "VEHICLE", "SOAT", "SOAT vigente", "DOCUMENTED"),
            ("VEH-SUNARP", "VEHICLE", "SUNARP", "Propiedad o consulta SUNARP verificada", "VERIFIED"),
            ("DRV-IND", "DRIVER", "INDUCTION", "Inducción minera vigente", "DOCUMENTED"),
            ("DRV-DEF", "DRIVER", "DEFENSIVE", "Manejo defensivo vigente", "DOCUMENTED"),
            ("DRV-AUT", "DRIVER", "INTERNAL_AUTH", "Autorización interna vigente", "VERIFIED"),
        ]
        for code, subject, evidence, description, verification in requirement_specs:
            RequirementRule.objects.update_or_create(client_profile=profile, code=code, defaults={
                "subject": subject, "evidence_type": evidence, "description": description, "blocking": True,
                "minimum_verification": verification, "legal_or_client_source": profile.source, "source_version": profile.source_version,
            })

        specs = [
            ("V0X-001", "1MNFLEETD3M000001", "Volvo", "FMX", Vehicle.OperationalStatus.AVAILABLE),
            ("V0X-002", "1MNFLEETD3M000002", "Scania", "P 460", Vehicle.OperationalStatus.AVAILABLE),
            ("V0X-003", "1MNFLEETD3M000003", "Mercedes-Benz", "Arocs", Vehicle.OperationalStatus.OUT_OF_SERVICE),
            ("V0X-004", "1MNFLEETD3M000004", "Volvo", "FMX", Vehicle.OperationalStatus.AVAILABLE),
            ("V0X-005", "1MNFLEETD3M000005", "Scania", "G 500", Vehicle.OperationalStatus.MAINTENANCE),
        ]
        vehicles = []
        for index, (plate, vin, brand, model, status) in enumerate(specs, 1):
            vehicle, _ = Vehicle.objects.update_or_create(company=company, plate=plate, defaults={
                "vin": vin, "engine_number": f"MTR-DEMO-{index:02d}", "brand": brand, "model": model,
                "year": 2021 + (index % 3), "vehicle_type": "Volquete", "availability": Vehicle.Availability.OWNED,
                "owner_name": company.name, "tare_kg": 15000 + index * 100, "gross_weight_kg": 41000,
                "odometer_km": 35000 + index * 10000, "operational_status": status, "client_profile": profile,
            })
            vehicles.append(vehicle)

        expiries = [date.today() + timedelta(days=180), date.today() + timedelta(days=18), date.today() - timedelta(days=4), None, date.today() + timedelta(days=60)]
        for vehicle, expiry in zip(vehicles, expiries):
            for document_type, verification in (("CITV", "DOCUMENTED"), ("SOAT", "DOCUMENTED"), ("SUNARP", "VERIFIED")):
                VehicleDocument.objects.update_or_create(vehicle=vehicle, document_type=document_type, defaults={
                    "number": f"{document_type}-DEMO-{vehicle.plate}", "issuer": "Entidad ficticia de prueba", "issue_date": date.today() - timedelta(days=180),
                    "expiry_date": expiry if document_type != "SUNARP" else date.today() + timedelta(days=60), "verification_level": verification, "is_blocking": True,
                    "source_reference": "Evidencia ficticia; no usar como documento real.",
                })

        for index in range(1, 6):
            Driver.objects.update_or_create(company=company, document_number=f"9000000{index}", defaults={
                "first_names": f"Conductor {index}", "last_names": "Demostración", "license_number": f"Q9000000{index}",
                "license_category": "A-IIIc", "license_expiry": date.today() + timedelta(days=365-index*20),
                "medical_expiry": date.today() + timedelta(days=150-index*10), "mining_experience_years": index, "client_profile": profile,
            })
            driver = Driver.objects.get(company=company, document_number=f"9000000{index}")
            for credential_type, verification in (("INDUCTION", "DOCUMENTED"), ("DEFENSIVE", "DOCUMENTED"), ("INTERNAL_AUTH", "VERIFIED")):
                DriverCredential.objects.update_or_create(driver=driver, credential_type=credential_type, defaults={
                    "number": f"{credential_type}-DEMO-{index}", "issue_date": date.today(),
                    "expiry_date": date.today() + timedelta(days=180), "verification_level": verification,
                })
        if created:
            self.stdout.write(self.style.SUCCESS(f"Datos demo creados. Usuario: admin_demo | clave temporal: {demo_password}"))
        else:
            self.stdout.write(self.style.SUCCESS("Datos demo actualizados. La contraseña existente no fue modificada."))
