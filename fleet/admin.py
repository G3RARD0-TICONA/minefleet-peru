from django.contrib import admin

from .models import Driver, Vehicle, VehicleAssignment, VehicleDocument


class VehicleDocumentInline(admin.TabularInline):
    model = VehicleDocument
    extra = 0


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("plate", "company", "brand", "model", "vehicle_type", "payload_kg", "status")
    list_filter = ("company", "vehicle_type", "status", "availability")
    search_fields = ("plate", "vin", "brand", "model")
    inlines = (VehicleDocumentInline,)


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("document_number", "full_name", "company", "license_category", "license_expiry", "status")
    list_filter = ("company", "license_category", "status")
    search_fields = ("document_number", "first_names", "last_names", "license_number")


admin.site.register(VehicleDocument)
admin.site.register(VehicleAssignment)

# Register your models here.
