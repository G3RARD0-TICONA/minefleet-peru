from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import Company, Membership
from fleet.models import Driver, Vehicle, VehicleDocument


class Command(BaseCommand):
    help = "Crea una empresa y datos ficticios seguros para demostración."

    def handle(self, *args, **options):
        company, _ = Company.objects.get_or_create(
            ruc="20999999991",
            defaults={"name": "Transportes Demo Arequipa S.A.C.", "trade_name": "Flota Demo Sur", "region": "Arequipa"},
        )
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(username="admin_demo", defaults={"email": "demo@example.invalid", "is_staff": True, "is_superuser": True})
        if created:
            user.set_password("MineFleet-Demo-2026")
            user.save()
        Membership.objects.update_or_create(user=user, company=company, defaults={"role": Membership.Role.ADMIN, "active": True})

        specs = [
            ("V0X-001", "1MNFLEETDEMO0001", "Volvo", "FMX", Vehicle.Status.ELIGIBLE),
            ("V0X-002", "1MNFLEETDEMO0002", "Scania", "P 460", Vehicle.Status.OBSERVED),
            ("V0X-003", "1MNFLEETDEMO0003", "Mercedes-Benz", "Arocs", Vehicle.Status.BLOCKED),
            ("V0X-004", "1MNFLEETDEMO0004", "Volvo", "FMX", Vehicle.Status.DRAFT),
            ("V0X-005", "1MNFLEETDEMO0005", "Scania", "G 500", Vehicle.Status.MAINTENANCE),
        ]
        vehicles = []
        for index, (plate, vin, brand, model, status) in enumerate(specs, 1):
            vehicle, _ = Vehicle.objects.update_or_create(company=company, plate=plate, defaults={
                "vin": vin, "engine_number": f"MTR-DEMO-{index:02d}", "brand": brand, "model": model,
                "year": 2021 + (index % 3), "vehicle_type": "Volquete", "availability": Vehicle.Availability.OWNED,
                "owner_name": company.name, "tare_kg": 15000 + index * 100, "gross_weight_kg": 41000,
                "odometer_km": 35000 + index * 10000, "status": status,
            })
            vehicles.append(vehicle)

        expiries = [date.today() + timedelta(days=180), date.today() + timedelta(days=18), date.today() - timedelta(days=4), None, date.today() + timedelta(days=60)]
        for vehicle, expiry in zip(vehicles, expiries):
            VehicleDocument.objects.update_or_create(vehicle=vehicle, document_type=VehicleDocument.Type.CITV, defaults={
                "number": f"CITV-DEMO-{vehicle.plate}", "issuer": "Entidad de prueba", "issue_date": date.today() - timedelta(days=180),
                "expiry_date": expiry, "verification_level": VehicleDocument.Verification.DOCUMENTED, "is_blocking": True,
                "source_reference": "Evidencia ficticia; no consultar como documento real.",
            })

        for index in range(1, 6):
            Driver.objects.update_or_create(company=company, document_number=f"9000000{index}", defaults={
                "first_names": f"Conductor {index}", "last_names": "Demostración", "license_number": f"Q9000000{index}",
                "license_category": "A-IIIc", "license_expiry": date.today() + timedelta(days=365-index*20),
                "medical_expiry": date.today() + timedelta(days=150-index*10), "mining_experience_years": index,
            })
        self.stdout.write(self.style.SUCCESS("Datos demo creados. Usuario: admin_demo | clave: MineFleet-Demo-2026"))
