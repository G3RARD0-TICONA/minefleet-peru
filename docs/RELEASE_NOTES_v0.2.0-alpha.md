# MineFleet Perú v0.2.0-alpha

Primera versión pública de investigación con reglas configurables de aptitud documental para transportistas mineros del Perú.

## Incluye

- Perfiles por empresa, cliente referencial y operación.
- Reglas bloqueantes para vehículos y conductores.
- Revocación de aptitud por vencimiento, mantenimiento o evidencia insuficiente.
- Validación de archivos, huella SHA-256 y descarga privada por rol.
- Aislamiento multiempresa, auditoría, importación Excel y datos ficticios.
- 13 pruebas automatizadas, cobertura mínima del 70 % y CI de GitHub.

## Criterios comprobados

- Un vehículo no queda apto sin todas las evidencias bloqueantes vigentes.
- Un vencimiento bloqueante revoca la aptitud existente.
- Un conductor requiere licencia, examen médico y credenciales aplicables.
- Un usuario no puede consultar expedientes de otra empresa.
- Operaciones no puede verificar documentos y Consulta no puede descargarlos.

## Límites de esta alpha

- No integra automáticamente SUNARP, MTC, SUTRAN ni sistemas de empresas mineras.
- Los requisitos particulares deben cargarse desde fuentes autorizadas y vigentes.
- SQLite y el almacenamiento local son únicamente para desarrollo.
- Aún no incorpora mantenimiento completo, IPERC, rutas, combustible, órdenes de compra ni conciliación.
- No constituye homologación, certificación ISO, autorización de ingreso o garantía de contratación.

## Uso recomendado

Evaluación académica, demostración con datos ficticios y validación del modelo de información. Un piloto real exige revisión legal, protección de datos, infraestructura productiva y aprobación formal de los responsables de SST, operaciones y cumplimiento.
