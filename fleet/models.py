from datetime import date, timedelta
import hashlib

from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models

from core.models import Company
from .validators import validate_evidence_file


def uploaded_file_sha256(upload):
    digest = hashlib.sha256()
    position = upload.tell()
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(position)
    return digest.hexdigest()


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ClientProfile(TimestampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="client_profiles")
    name = models.CharField(max_length=160)
    operation = models.CharField(max_length=160, blank=True)
    source = models.CharField(max_length=250, blank=True)
    source_version = models.CharField(max_length=40, blank=True)
    effective_date = models.DateField(null=True, blank=True)
    reviewed_at = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    disclaimer = models.TextField(default="Perfil referencial sujeto a validación contra bases y documentos oficiales vigentes.")

    class Meta:
        ordering = ("name",)
        constraints = [models.UniqueConstraint(fields=("company", "name", "operation"), name="unique_client_operation")]

    def __str__(self):
        return f"{self.name} · {self.operation or 'General'}"


class RequirementRule(TimestampedModel):
    class Subject(models.TextChoices):
        VEHICLE = "VEHICLE", "Vehículo"
        DRIVER = "DRIVER", "Conductor"

    class MinimumVerification(models.TextChoices):
        DECLARED = "DECLARED", "Declarado"
        DOCUMENTED = "DOCUMENTED", "Documentado"
        VERIFIED = "VERIFIED", "Verificado manualmente"

    client_profile = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name="requirements")
    code = models.CharField(max_length=40)
    subject = models.CharField(max_length=20, choices=Subject.choices)
    evidence_type = models.CharField(max_length=30)
    description = models.CharField(max_length=250)
    blocking = models.BooleanField(default=True)
    minimum_verification = models.CharField(max_length=20, choices=MinimumVerification.choices, default=MinimumVerification.DOCUMENTED)
    legal_or_client_source = models.CharField(max_length=250)
    source_version = models.CharField(max_length=40)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("subject", "code")
        constraints = [models.UniqueConstraint(fields=("client_profile", "code"), name="unique_requirement_code_per_profile")]

    def __str__(self):
        return f"{self.code} · {self.description}"

    def clean(self):
        allowed = VehicleDocument.Type.values if self.subject == self.Subject.VEHICLE else DriverCredential.Type.values
        if self.evidence_type not in allowed:
            raise ValidationError({"evidence_type": "El tipo de evidencia no corresponde al sujeto seleccionado."})


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

    class OperationalStatus(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Disponible"
        MAINTENANCE = "MAINTENANCE", "Mantenimiento"
        OUT_OF_SERVICE = "OUT_OF_SERVICE", "Fuera de servicio"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="vehicles")
    client_profile = models.ForeignKey(ClientProfile, on_delete=models.PROTECT, null=True, blank=True, related_name="vehicles")
    plate = models.CharField(max_length=8, validators=[RegexValidator(r"^[A-Z0-9]{3}-?[A-Z0-9]{3,4}$", "Placa inválida")])
    vin = models.CharField(max_length=17, validators=[RegexValidator(r"^[A-HJ-NPR-Z0-9]{17}$", "VIN inválido: debe tener 17 caracteres y no usar I, O o Q.")])
    engine_number = models.CharField(max_length=40, blank=True)
    brand = models.CharField(max_length=60)
    model = models.CharField(max_length=60)
    year = models.PositiveSmallIntegerField(validators=[MinValueValidator(1980), MaxValueValidator(2100)])
    vehicle_type = models.CharField(max_length=40, default="Volquete")
    availability = models.CharField(max_length=20, choices=Availability.choices, default=Availability.OWNED)
    owner_name = models.CharField(max_length=180)
    tare_kg = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    gross_weight_kg = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    payload_kg = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    odometer_km = models.PositiveIntegerField(default=0)
    operational_status = models.CharField(max_length=20, choices=OperationalStatus.choices, default=OperationalStatus.AVAILABLE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, editable=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("plate",)
        constraints = [
            models.UniqueConstraint(fields=("company", "plate"), name="unique_plate_per_company"),
            models.UniqueConstraint(fields=("company", "vin"), name="unique_vin_per_company"),
            models.CheckConstraint(condition=models.Q(gross_weight_kg__gte=models.F("tare_kg")), name="gross_weight_gte_tare"),
        ]

    def clean(self):
        self.plate = self.plate.upper().strip()
        self.vin = self.vin.upper().strip()
        if self.client_profile_id and self.client_profile.company_id != self.company_id:
            raise ValidationError({"client_profile": "El perfil debe pertenecer a la misma empresa."})
        if self.gross_weight_kg < self.tare_kg:
            raise ValidationError({"gross_weight_kg": "El PBV no puede ser menor que la tara."})

    def save(self, *args, **kwargs):
        self.full_clean()
        self.payload_kg = self.gross_weight_kg - self.tare_kg
        super().save(*args, **kwargs)
        self.evaluate_compliance(persist=True)

    def evaluate_compliance(self, persist=False):
        if self.operational_status == self.OperationalStatus.MAINTENANCE:
            result = self.Status.MAINTENANCE
        elif self.operational_status == self.OperationalStatus.OUT_OF_SERVICE:
            result = self.Status.BLOCKED
        elif not self.client_profile_id:
            result = self.Status.DRAFT
        else:
            verification_rank = {"DECLARED": 0, "DOCUMENTED": 1, "VERIFIED": 2}
            blocking_failure = False
            nonblocking_failure = False
            rules = self.client_profile.requirements.filter(subject=RequirementRule.Subject.VEHICLE, active=True)
            for rule in rules:
                acceptable = self.documents.filter(
                    document_type=rule.evidence_type,
                    status__in=(VehicleDocument.Status.VALID, VehicleDocument.Status.EXPIRING),
                )
                satisfied = any(
                    verification_rank.get(document.verification_level, -1) >= verification_rank[rule.minimum_verification]
                    for document in acceptable
                )
                if not satisfied and rule.blocking:
                    blocking_failure = True
                elif not satisfied:
                    nonblocking_failure = True
            if not rules.exists():
                result = self.Status.DRAFT
            elif blocking_failure:
                result = self.Status.BLOCKED
            elif nonblocking_failure:
                result = self.Status.OBSERVED
            else:
                result = self.Status.ELIGIBLE
        if persist and self.status != result:
            Vehicle.objects.filter(pk=self.pk).update(status=result)
            self.status = result
        return result

    @property
    def blocking_documents(self):
        return self.documents.filter(is_blocking=True).exclude(status__in=(VehicleDocument.Status.VALID, VehicleDocument.Status.EXPIRING)).count()

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
    file = models.FileField(upload_to="vehicle_documents/%Y/%m/", blank=True, validators=[validate_evidence_file])
    original_filename = models.CharField(max_length=255, blank=True)
    sha256 = models.CharField(max_length=64, blank=True, editable=False)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="uploaded_vehicle_documents")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_vehicle_documents")
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
        if self.file:
            self.sha256 = uploaded_file_sha256(self.file)
            self.original_filename = self.original_filename or self.file.name.rsplit("/", 1)[-1]
        super().save(*args, **kwargs)
        if self.vehicle_id:
            self.vehicle.evaluate_compliance(persist=True)

    def __str__(self):
        return f"{self.vehicle.plate} · {self.get_document_type_display()}"


class Driver(TimestampedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Activo"
        OBSERVED = "OBSERVED", "Observado"
        BLOCKED = "BLOCKED", "Bloqueado"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="drivers")
    client_profile = models.ForeignKey(ClientProfile, on_delete=models.PROTECT, null=True, blank=True, related_name="drivers")
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

    def clean(self):
        if self.client_profile_id and self.client_profile.company_id != self.company_id:
            raise ValidationError({"client_profile": "El perfil debe pertenecer a la misma empresa."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_authorized(self):
        today = date.today()
        if self.status != self.Status.ACTIVE or self.license_expiry < today or not self.medical_expiry or self.medical_expiry < today:
            return False
        if not self.client_profile_id:
            return False
        verification_rank = {"DECLARED": 0, "DOCUMENTED": 1, "VERIFIED": 2}
        rules = self.client_profile.requirements.filter(subject=RequirementRule.Subject.DRIVER, active=True)
        if not rules.exists():
            return False
        for rule in rules.filter(blocking=True):
            credentials = self.credentials.filter(
                credential_type=rule.evidence_type,
                status=DriverCredential.Status.VALID,
            )
            if not any(verification_rank.get(item.verification_level, -1) >= verification_rank[rule.minimum_verification] for item in credentials):
                return False
        return True

    def __str__(self):
        return self.full_name


class DriverCredential(TimestampedModel):
    class Type(models.TextChoices):
        INDUCTION = "INDUCTION", "Inducción minera"
        DEFENSIVE = "DEFENSIVE", "Manejo defensivo"
        FIRST_AID = "FIRST_AID", "Primeros auxilios"
        INTERNAL_AUTH = "INTERNAL_AUTH", "Autorización interna"
        COMPETENCY = "COMPETENCY", "Competencia por equipo"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        VALID = "VALID", "Vigente"
        EXPIRED = "EXPIRED", "Vencido"
        REJECTED = "REJECTED", "Rechazado"

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name="credentials")
    credential_type = models.CharField(max_length=30, choices=Type.choices)
    number = models.CharField(max_length=80, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    verification_level = models.CharField(max_length=20, choices=RequirementRule.MinimumVerification.choices, default=RequirementRule.MinimumVerification.DECLARED)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    file = models.FileField(upload_to="driver_credentials/%Y/%m/", blank=True, validators=[validate_evidence_file])
    sha256 = models.CharField(max_length=64, blank=True, editable=False)

    def save(self, *args, **kwargs):
        if self.status != self.Status.REJECTED:
            if not self.expiry_date:
                self.status = self.Status.PENDING
            elif self.expiry_date < date.today():
                self.status = self.Status.EXPIRED
            else:
                self.status = self.Status.VALID
        if self.file:
            self.sha256 = uploaded_file_sha256(self.file)
        super().save(*args, **kwargs)


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
        if self.active and self.vehicle.evaluate_compliance() != Vehicle.Status.ELIGIBLE:
            raise ValidationError("El vehículo no cumple todas las reglas bloqueantes vigentes del perfil asignado.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.vehicle.plate} → {self.driver.full_name}"

# Create your models here.
