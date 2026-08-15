from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render

from core.models import AuditLog, Membership
from .forms import DriverForm, ImportVehiclesForm, VehicleDocumentForm, VehicleForm
from .models import Driver, Vehicle, VehicleDocument
from .services import dashboard_metrics, import_vehicles, log_action, vehicle_template


def current_membership(request):
    memberships = Membership.objects.select_related("company").filter(user=request.user, active=True, company__active=True)
    selected_company = request.session.get("minefleet_company_id")
    membership = memberships.filter(company_id=selected_company).first() if selected_company else memberships.first()
    if not membership:
        raise PermissionDenied("El usuario no está vinculado a una empresa activa.")
    request.session["minefleet_company_id"] = membership.company_id
    return membership


def can_manage_vehicles(membership):
    return membership.role in {Membership.Role.ADMIN, Membership.Role.OPERATIONS}


def can_manage_compliance(membership):
    return membership.role in {Membership.Role.ADMIN, Membership.Role.COMPLIANCE}


def can_view_sensitive_files(membership):
    return membership.role in {Membership.Role.ADMIN, Membership.Role.COMPLIANCE}


@login_required
def dashboard(request):
    membership = current_membership(request)
    context = dashboard_metrics(membership.company) | {
        "membership": membership,
        "alerts": VehicleDocument.objects.filter(vehicle__company=membership.company).exclude(status=VehicleDocument.Status.VALID).select_related("vehicle")[:8],
        "audit": AuditLog.objects.filter(company=membership.company).select_related("user")[:8],
        "memberships": Membership.objects.filter(user=request.user, active=True).select_related("company"),
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
    if not can_manage_vehicles(membership):
        raise PermissionDenied
    form = VehicleForm(request.POST or None, company=membership.company)
    if form.is_valid():
        vehicle = form.save(commit=False)
        vehicle.company = membership.company
        vehicle.save()
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
    if not can_manage_compliance(membership):
        raise PermissionDenied
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk, company=membership.company)
    form = VehicleDocumentForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        document = form.save(commit=False)
        document.vehicle = vehicle
        document.uploaded_by = request.user
        if document.file:
            document.original_filename = document.file.name
        if document.verification_level == VehicleDocument.Verification.VERIFIED:
            from django.utils import timezone
            document.reviewed_by = request.user
            document.reviewed_at = timezone.now()
        document.save()
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
    if not can_manage_vehicles(membership):
        raise PermissionDenied
    form = DriverForm(request.POST or None, company=membership.company)
    if form.is_valid():
        driver = form.save(commit=False)
        driver.company = membership.company
        driver.save()
        messages.success(request, "Conductor registrado correctamente.")
        return redirect("driver_list")
    return render(request, "fleet/form.html", {"form": form, "title": "Registrar conductor"})


@login_required
def import_vehicle_file(request):
    membership = current_membership(request)
    if not can_manage_vehicles(membership):
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


@login_required
def download_document(request, pk):
    membership = current_membership(request)
    if not can_view_sensitive_files(membership):
        raise PermissionDenied("Su rol no puede descargar evidencias documentales.")
    document = get_object_or_404(VehicleDocument, pk=pk, vehicle__company=membership.company)
    if not document.file:
        return HttpResponseBadRequest("El registro no contiene un archivo.")
    log_action(company=membership.company, user=request.user, action="DOWNLOAD", entity="VehicleDocument", object_id=document.pk, detail={"sha256": document.sha256})
    return FileResponse(document.file.open("rb"), as_attachment=True, filename=document.original_filename or document.file.name.rsplit("/", 1)[-1])


@login_required
def switch_company(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Método no permitido.")
    membership = get_object_or_404(Membership, user=request.user, company_id=request.POST.get("company_id"), active=True)
    request.session["minefleet_company_id"] = membership.company_id
    log_action(company=membership.company, user=request.user, action="SWITCH_COMPANY", entity="Company", object_id=membership.company_id)
    return redirect("dashboard")

# Create your views here.
