from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("vehiculos/", views.vehicle_list, name="vehicle_list"),
    path("vehiculos/nuevo/", views.vehicle_create, name="vehicle_create"),
    path("vehiculos/importar/", views.import_vehicle_file, name="vehicle_import"),
    path("vehiculos/plantilla/", views.download_vehicle_template, name="vehicle_template"),
    path("vehiculos/<int:pk>/", views.vehicle_detail, name="vehicle_detail"),
    path("vehiculos/<int:vehicle_pk>/documentos/nuevo/", views.document_create, name="document_create"),
    path("documentos/<int:pk>/descargar/", views.download_document, name="document_download"),
    path("conductores/", views.driver_list, name="driver_list"),
    path("conductores/nuevo/", views.driver_create, name="driver_create"),
    path("empresa/cambiar/", views.switch_company, name="switch_company"),
]
