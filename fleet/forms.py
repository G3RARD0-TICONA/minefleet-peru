from django import forms

from .models import Driver, Vehicle, VehicleAssignment, VehicleDocument
from .validators import validate_excel_import


class DateInput(forms.DateInput):
    input_type = "date"


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class VehicleForm(StyledModelForm):
    class Meta:
        model = Vehicle
        exclude = ("company", "payload_kg", "status")

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields["client_profile"].queryset = company.client_profiles.filter(active=True)


class VehicleDocumentForm(StyledModelForm):
    class Meta:
        model = VehicleDocument
        exclude = ("vehicle", "reviewed_at", "reviewed_by", "uploaded_by", "sha256", "original_filename", "status", "is_blocking")
        widgets = {"issue_date": DateInput(), "expiry_date": DateInput()}


class DriverForm(StyledModelForm):
    class Meta:
        model = Driver
        exclude = ("company",)
        widgets = {"license_expiry": DateInput(), "medical_expiry": DateInput()}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields["client_profile"].queryset = company.client_profiles.filter(active=True)


class AssignmentForm(StyledModelForm):
    class Meta:
        model = VehicleAssignment
        exclude = ("company",)
        widgets = {"start_date": DateInput(), "end_date": DateInput()}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields["vehicle"].queryset = Vehicle.objects.filter(company=company)
            self.fields["driver"].queryset = Driver.objects.filter(company=company)


class ImportVehiclesForm(forms.Form):
    file = forms.FileField(label="Archivo Excel (.xlsx)", validators=[validate_excel_import])
