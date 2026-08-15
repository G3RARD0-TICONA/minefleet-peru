from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.models import AuditLog, Membership
from .forms import DriverForm, ImportVehiclesForm, VehicleDocumentForm, VehicleForm
from .models import Driver, Vehicle, VehicleDocument
from .services import dashboard_metrics, import_vehicles, log_action, vehicle_template


def current_membership(request):
    membership = Membership.objects.select_related("company").filter(user=request.user, active=True).first()
    if not membership:
        raise PermissionDenied("El usuario no está vinculado a una empresa activa.")
    return membership


def can_edit(membership):
    return membership.role in {Membership.Role.ADMIN, Membership.Role.COMPLIANCE, Membership.Role.OPERATIONS}


@login_required
def dashboard(request):
    membership = current_membership(request)
    context = dashboard_metrics(membership.company) | {
        "membership": membership,
        "alerts": VehicleDocument.objects.filter(vehicle__company=membership.company).exclude(status=VehicleDocument.Status.VALID).select_related("vehicle")[:8],
        "audit": AuditLog.objects.filter(company=membership.company).select_related("user")[:8],
    }
    return render(request, "fleet/dashboard.html", context)


@login_required
def vehicle_list(request):
    membership = current_membership(request)
    vehicles = Vehicle.objects.filter(company=membership.company)
    query = request.GET.get("q", "").strip()
    if query:
        vehicles = vehicles.filter(plate__icontains=query)
    return render(request, "fleet/vehicle_list.html", {"vehicles": vehicles, "membership": membership, "query": query})


@login_required
def vehicle_create(request):
    membership = current_membership(request)
    if not can_edit(membership):
        raise PermissionDenied
    form = VehicleForm(request.POST or None)
    if form.is_valid():
        vehicle = form.save(commit=False)
        vehicle.company = membership.company
        vehicle.save()
        log_action(company=membership.company, user=request.user, action="CREATE", entity="Vehicle", object_id=vehicle.pk, detail={"plate": vehicle.plate})
        messages.success(request, "Vehículo registrado correctamente.")
        return redirect("vehicle_detail", pk=vehicle.pk)
    return render(request, "fleet/form.html", {"form": form, "title": "Registrar vehículo"})


@login_required
def vehicle_detail(request, pk):
    membership = current_membership(request)
    vehicle = get_object_or_404(Vehicle.objects.prefetch_related("documents"), pk=pk, company=membership.company)
    return render(request, "fleet/vehicle_detail.html", {"vehicle": vehicle, "membership": membership})


@login_required
def document_create(request, vehicle_pk):
    membership = current_membership(request)
    if not can_edit(membership):
        raise PermissionDenied
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk, company=membership.company)
    form = VehicleDocumentForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        document = form.save(commit=False)
        document.vehicle = vehicle
        document.save()
        log_action(company=membership.company, user=request.user, action="CREATE", entity="VehicleDocument", object_id=document.pk, detail={"vehicle": vehicle.plate, "type": document.document_type})
        messages.success(request, "Documento incorporado al expediente.")
        return redirect("vehicle_detail", pk=vehicle.pk)
    return render(request, "fleet/form.html", {"form": form, "title": f"Documento de {vehicle.plate}"})


@login_required
def driver_list(request):
    membership = current_membership(request)
    return render(request, "fleet/driver_list.html", {"drivers": Driver.objects.filter(company=membership.company), "membership": membership})


@login_required
def driver_create(request):
    membership = current_membership(request)
    if not can_edit(membership):
        raise PermissionDenied
    form = DriverForm(request.POST or None)
    if form.is_valid():
        driver = form.save(commit=False)
        driver.company = membership.company
        driver.save()
        log_action(company=membership.company, user=request.user, action="CREATE", entity="Driver", object_id=driver.pk)
        messages.success(request, "Conductor registrado correctamente.")
        return redirect("driver_list")
    return render(request, "fleet/form.html", {"form": form, "title": "Registrar conductor"})


@login_required
def import_vehicle_file(request):
    membership = current_membership(request)
    if not can_edit(membership):
        raise PermissionDenied
    form = ImportVehiclesForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        try:
            result = import_vehicles(workbook_file=form.cleaned_data["file"], company=membership.company, user=request.user)
            messages.success(request, f"Importación finalizada: {result['created']} creados y {result['updated']} actualizados.")
            for error in result["errors"][:10]:
                messages.warning(request, error)
            return redirect("vehicle_list")
        except Exception as exc:
            messages.error(request, str(exc))
    return render(request, "fleet/form.html", {"form": form, "title": "Importar vehículos desde Excel", "help_text": "Descarga primero la plantilla oficial. Los errores de una fila no anulan las filas válidas."})


@login_required
def download_vehicle_template(request):
    current_membership(request)
    response = HttpResponse(vehicle_template(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="plantilla_vehiculos_minefleet.xlsx"'
    return response

# Create your views here.
