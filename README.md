# MineFleet Perú

Prototipo de investigación para organizar y demostrar el cumplimiento documental de empresas transportistas que prestan o desean prestar servicios de alquiler de volquetes al sector minero peruano.

> El sistema prepara, controla y conserva evidencias. No garantiza homologación, acceso, contratación ni aprobación por una compañía minera.

## Alcance del MVP 0.1

- autenticación y cuatro perfiles empresariales;
- separación de información por empresa;
- maestro de vehículos y cálculo de carga útil;
- expediente vehicular y niveles declarado/documentado/verificado;
- vigencias y alertas documentarias;
- maestro de conductores y aptitud documental;
- importación de vehículos desde una plantilla Excel controlada;
- bitácora básica de creación e importación;
- datos ficticios de demostración.

## Instalación en Windows

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Abrir `http://127.0.0.1:8000/`.

Usuario de demostración: `admin_demo`  
Clave temporal: `MineFleet-Demo-2026`

La clave es solamente para ejecución local con datos ficticios y debe cambiarse antes de cualquier piloto real.

## Pruebas

```powershell
python manage.py test
python manage.py check
```

## Privacidad

No subir a Git datos personales, exámenes médicos, licencias, cuentas bancarias, contratos, evidencias SUNARP ni documentos de clientes. El directorio `media/`, la base SQLite y los secretos están excluidos.

## Próxima línea base

MVP 0.2: asignaciones, matriz por cliente minero, reglas bloqueantes configurables, mantenimiento, seguridad y generación del expediente de licitación.
