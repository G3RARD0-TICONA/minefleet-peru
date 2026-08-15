# Arquitectura

Aplicación web Django 5.2 con separación lógica por empresa, motor de reglas por perfil, expedientes documentales privados y bitácora. SQLite es solo para desarrollo; el objetivo de producción es PostgreSQL y almacenamiento de objetos privado.

El estado de aptitud es derivado: condición operativa + perfil vigente + reglas activas + evidencia con vigencia y nivel de verificación. Los vencimientos bloqueantes revocan la aptitud. La auditoría de aplicación es evidencia auxiliar; para garantías fuertes se requiere almacenamiento inmutable externo, monitoreo y copias verificadas.
