from django import forms

from .models import Driver, Vehicle, VehicleAssignment, VehicleDocument


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
        exclude = ("company", "payload_kg")


class VehicleDocumentForm(StyledModelForm):
    class Meta:
        model = VehicleDocument
        exclude = ("vehicle", "reviewed_at")
        widgets = {"issue_date": DateInput(), "expiry_date": DateInput()}


class DriverForm(StyledModelForm):
    class Meta:
        model = Driver
        exclude = ("company",)
        widgets = {"license_expiry": DateInput(), "medical_expiry": DateInput()}


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
    file = forms.FileField(label="Archivo Excel (.xlsx)")
