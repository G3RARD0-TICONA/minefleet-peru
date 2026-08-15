# MineFleet Perú

[![Pruebas](https://github.com/G3RARD0-TICONA/minefleet-peru/actions/workflows/tests.yml/badge.svg)](https://github.com/G3RARD0-TICONA/minefleet-peru/actions/workflows/tests.yml)

**Estado:** prototipo de investigación / preproducción. No usar todavía como único control de acceso, seguridad o contratación.

**Versión pública actual:** `v0.2.0-alpha`

Prototipo de investigación para organizar y demostrar el cumplimiento documental de empresas transportistas que prestan o desean prestar servicios de alquiler de volquetes al sector minero peruano.

> El sistema prepara, controla y conserva evidencias. No garantiza homologación, acceso, contratación ni aprobación por una compañía minera.

## Capacidades implementadas

- autenticación y cuatro perfiles empresariales;
- separación de información por empresa;
- maestro de vehículos y cálculo de carga útil;
- expediente vehicular y niveles declarado/documentado/verificado;
- vigencias y alertas documentarias;
- maestro de conductores y aptitud documental;
- importación de vehículos desde una plantilla Excel controlada;
- perfiles de requisitos versionables y reglas bloqueantes por cliente/operación;
- revocación automática de aptitud por vencimiento, mantenimiento o evidencia insuficiente;
- descarga privada de evidencias por rol y huella SHA-256;
- bitácora inmutable a nivel de aplicación;
- datos ficticios de demostración.

## Cómo funciona

```mermaid
flowchart TD
    A[Empresa transportista] --> B[Perfil por cliente y operación]
    B --> C[Reglas versionadas]
    C --> D[Vehículos y conductores]
    D --> E[Evidencias y vigencias]
    E --> F{Evaluación automática}
    F -->|Cumple| G[Apto documental]
    F -->|Brecha bloqueante| H[Bloqueado]
    F -->|Brecha no bloqueante| I[Observado]
```

La aptitud no se escribe manualmente: se deriva de la condición operativa, el perfil asignado, las reglas activas, la vigencia y el nivel de verificación de cada evidencia.

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

El comando crea `admin_demo` y muestra una clave aleatoria una sola vez. Puede definir previamente `MINEFLEET_DEMO_PASSWORD`, únicamente en un entorno local aislado. Para administrar perfiles y reglas cree un superusuario con `python manage.py createsuperuser`.

## Evaluación rápida

1. Ejecute `python manage.py seed_demo` e ingrese con la clave temporal mostrada.
2. Revise los cinco volquetes ficticios y sus diferentes estados.
3. Cambie una fecha de vencimiento desde la administración.
4. Confirme que una evidencia bloqueante vencida revoque automáticamente la aptitud.
5. Ejecute `python manage.py test` para reproducir los controles automatizados.

Consulte las [notas de `v0.2.0-alpha`](docs/RELEASE_NOTES_v0.2.0-alpha.md) para conocer límites y criterios de aceptación.

## Pruebas

```powershell
python manage.py test
python manage.py check
```

## Privacidad

No subir a Git datos personales, exámenes médicos, licencias, cuentas bancarias, contratos, evidencias SUNARP ni documentos de clientes. Consulte [Privacidad](docs/PRIVACY.md) y [Seguridad](SECURITY.md).

## Límites y no afiliación

MineFleet Perú no está afiliado, certificado ni aprobado por Cerro Verde, Southern Peru, Las Bambas, Antamina u otra compañía minera. Los perfiles incluidos son referenciales y deben contrastarse con bases, contrato, unidad minera y versión vigente. El software no sustituye a SUNARP, MTC, SUTRAN, MINEM, aseguradoras, médicos ocupacionales, auditores ni responsables de SST.

Vea [alcance legal](docs/LEGAL_SCOPE.md), [arquitectura](docs/ARCHITECTURE.md), [contribución](CONTRIBUTING.md) y [hoja de ruta](ROADMAP.md).

## Citar el proyecto

Este proyecto puede citarse mediante el archivo [`CITATION.cff`](CITATION.cff). La publicación del código no implica validación oficial de las matrices referenciales.

## Producción

Use PostgreSQL, almacenamiento privado, HTTPS y gestión externa de secretos. Antes de desplegar ejecute:

```bash
MINEFLEET_ENV=production MINEFLEET_SECRET_KEY='...' \
MINEFLEET_ALLOWED_HOSTS='app.example.com' \
MINEFLEET_CSRF_TRUSTED_ORIGINS='https://app.example.com' \
python manage.py check --deploy
```
