from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


class Company(models.Model):
    ruc_validator = RegexValidator(r"^\d{11}$", "El RUC debe contener 11 dígitos.")
    name = models.CharField("razón social", max_length=180)
    trade_name = models.CharField("nombre comercial", max_length=120, blank=True)
    ruc = models.CharField(max_length=11, unique=True, validators=[ruc_validator])
    region = models.CharField(max_length=80, default="Arequipa")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "empresa"
        verbose_name_plural = "empresas"
        ordering = ("name",)

    def __str__(self):
        return self.trade_name or self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        COMPLIANCE = "COMPLIANCE", "Cumplimiento"
        OPERATIONS = "OPERATIONS", "Operaciones"
        VIEWER = "VIEWER", "Consulta"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user", "company"), name="unique_company_membership")]

    def __str__(self):
        return f"{self.user} · {self.company} · {self.get_role_display()}"


class AuditLog(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=30)
    entity = models.CharField(max_length=80)
    object_id = models.CharField(max_length=60, blank=True)
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} {self.entity}"

# Create your models here.
