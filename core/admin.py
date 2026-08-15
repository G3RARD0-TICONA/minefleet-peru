from django.contrib import admin

from .models import AuditLog, Company, Membership


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("ruc", "name", "region", "active")
    search_fields = ("ruc", "name", "trade_name")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "role", "active")
    list_filter = ("role", "active")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "company", "user", "action", "entity", "object_id")
    list_filter = ("action", "entity")
    readonly_fields = ("company", "user", "action", "entity", "object_id", "detail", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

# Register your models here.
