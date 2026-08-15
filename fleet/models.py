from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from core.models import Company


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Vehicle(TimestampedModel):
    class Availability(models.TextChoices):
        OWNED = "OWNED", "Propio"
        LEASED = "LEASED", "Arrendado"
        THIRD_PARTY = "THIRD_PARTY", "Tercero"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Borrador"
        OBSERVED = "OBSERVED", "Observado"
        ELIGIBLE = "ELIGIBLE", "Apto documental"
        BLOCKED = "BLOCKED", "Bloqueado"
        MAINTENANCE = "MAINTENANCE", "Mantenimiento"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="vehicles")
    plate = models.CharField(max_length=8, validators=[RegexValidator(r"^[A-Z0-9-]{6,8}$", "Placa inválida")])
    vin = models.CharField(max_length=17)
    engine_number = models.CharField(max_length=40, blank=True)
    brand = models.CharField(max_length=60)
    model = models.CharField(max_length=60)
    year = models.PositiveSmallIntegerField()
    vehicle_type = models.CharField(max_length=40, default="Volquete")
    availability = models.CharField(max_length=20, choices=Availability.choices, default=Availability.OWNED)
    owner_name = models.CharField(max_length=180)
    tare_kg = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    gross_weight_kg = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    payload_kg = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    odometer_km = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("plate",)
        constraints = [
            models.UniqueConstraint(fields=("company", "plate"), name="unique_plate_per_company"),
            models.UniqueConstraint(fields=("company", "vin"), name="unique_vin_per_company"),
        ]

    def clean(self):
        self.plate = self.plate.upper().strip()
        self.vin = self.vin.upper().strip()
        if self.gross_weight_kg < self.tare_kg:
            raise ValidationError({"gross_weight_kg": "El PBV no puede ser menor que la tara."})

    def save(self, *args, **kwargs):
        self.full_clean()
        self.payload_kg = self.gross_weight_kg - self.tare_kg
        super().save(*args, **kwargs)

    @property
    def blocking_documents(self):
        return self.documents.filter(is_blocking=True).exclude(status=VehicleDocument.Status.VALID).count()

    def __str__(self):
        return f"{self.plate} · {self.brand} {self.model}"


class VehicleDocument(TimestampedModel):
    class Type(models.TextChoices):
        PROPERTY = "PROPERTY", "Tarjeta de identificación vehicular"
        SUNARP = "SUNARP", "Consulta/partida SUNARP"
        CITV = "CITV", "CITV"
        SOAT = "SOAT", "SOAT"
        INSURANCE = "INSURANCE", "Seguro complementario"
        MODIFICATION = "MODIFICATION", "Certificado de modificación"
        OTHER = "OTHER", "Otro"

    class Verification(models.TextChoices):
        DECLARED = "DECLARED", "Declarado"
        DOCUMENTED = "DOCUMENTED", "Documentado"
        VERIFIED = "VERIFIED", "Verificado manualmente"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        VALID = "VALID", "Vigente"
        EXPIRING = "EXPIRING", "Por vencer"
        EXPIRED = "EXPIRED", "Vencido"
        REJECTED = "REJECTED", "Rechazado"

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=20, choices=Type.choices)
    number = models.CharField(max_length=80, blank=True)
    issuer = models.CharField(max_length=120, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    verification_level = models.CharField(max_length=20, choices=Verification.choices, default=Verification.DECLARED)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    is_blocking = models.BooleanField(default=True)
    file = models.FileField(upload_to="vehicle_documents/%Y/%m/", blank=True)
    source_reference = models.CharField(max_length=250, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("expiry_date", "document_type")

    def refresh_status(self, today=None):
        today = today or date.today()
        if not self.expiry_date:
            return self.Status.PENDING if self.status != self.Status.REJECTED else self.status
        if self.expiry_date < today:
            return self.Status.EXPIRED
        if self.expiry_date <= today + timedelta(days=30):
            return self.Status.EXPIRING
        return self.Status.VALID

    def save(self, *args, **kwargs):
        if self.status != self.Status.REJECTED:
            self.status = self.refresh_status()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.vehicle.plate} · {self.get_document_type_display()}"


class Driver(TimestampedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Activo"
        OBSERVED = "OBSERVED", "Observado"
        BLOCKED = "BLOCKED", "Bloqueado"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="drivers")
    document_number = models.CharField(max_length=12)
    first_names = models.CharField(max_length=100)
    last_names = models.CharField(max_length=100)
    license_number = models.CharField(max_length=20)
    license_category = models.CharField(max_length=10, default="A-IIIc")
    license_expiry = models.DateField()
    medical_expiry = models.DateField(null=True, blank=True)
    mining_experience_years = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ("last_names", "first_names")
        constraints = [
            models.UniqueConstraint(fields=("company", "document_number"), name="unique_driver_document_per_company"),
            models.UniqueConstraint(fields=("company", "license_number"), name="unique_license_per_company"),
        ]

    @property
    def full_name(self):
        return f"{self.last_names}, {self.first_names}"

    @property
    def is_authorized(self):
        today = date.today()
        return self.status == self.Status.ACTIVE and self.license_expiry >= today and (not self.medical_expiry or self.medical_expiry >= today)

    def __str__(self):
        return self.full_name


class VehicleAssignment(TimestampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    authorized_by = models.CharField(max_length=120)

    def clean(self):
        if self.vehicle.company_id != self.company_id or self.driver.company_id != self.company_id:
            raise ValidationError("Empresa, vehículo y conductor deben coincidir.")
        if self.active and not self.driver.is_authorized:
            raise ValidationError("El conductor no tiene aptitud documental vigente.")
        if self.active and self.vehicle.status in (Vehicle.Status.BLOCKED, Vehicle.Status.MAINTENANCE):
            raise ValidationError("El vehículo está bloqueado o en mantenimiento.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.vehicle.plate} → {self.driver.full_name}"

# Create your models here.
