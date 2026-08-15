from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .audit import get_current_user
from .models import AuditLog, Company, Membership


def company_for(instance):
    if isinstance(instance, Company):
        return instance
    if isinstance(instance, Membership):
        return instance.company
    if hasattr(instance, "company"):
        return instance.company
    if hasattr(instance, "vehicle"):
        return instance.vehicle.company
    if hasattr(instance, "driver"):
        return instance.driver.company
    return None


@receiver(post_save)
def audit_model_save(sender, instance, created, **kwargs):
    if sender is AuditLog or sender._meta.app_label not in {"core", "fleet"}:
        return
    AuditLog.objects.create(
        company=company_for(instance), user=get_current_user(),
        action="CREATE" if created else "UPDATE", entity=sender.__name__, object_id=str(instance.pk),
    )


@receiver(pre_delete)
def audit_model_delete(sender, instance, **kwargs):
    if sender is AuditLog or sender._meta.app_label not in {"core", "fleet"}:
        return
    AuditLog.objects.create(
        company=company_for(instance), user=get_current_user(), action="DELETE",
        entity=sender.__name__, object_id=str(instance.pk),
    )


@receiver(user_logged_in)
def audit_login(sender, request, user, **kwargs):
    membership = Membership.objects.filter(user=user, active=True).select_related("company").first()
    AuditLog.objects.create(company=membership.company if membership else None, user=user, action="LOGIN", entity="Session")


@receiver(user_logged_out)
def audit_logout(sender, request, user, **kwargs):
    if not user:
        return
    membership = Membership.objects.filter(user=user, active=True).select_related("company").first()
    AuditLog.objects.create(company=membership.company if membership else None, user=user, action="LOGOUT", entity="Session")
