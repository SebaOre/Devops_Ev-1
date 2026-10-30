# Evidencias de la Evaluación Parcial 2

Documentación preparada el 30 de octubre de 2026. Los resultados de ejecución
indicados corresponden al 29 de octubre de 2026.

## Relación con la pauta

| Indicador | Implementación observable | Evidencia |
| --- | --- | --- |
| IE1, contenedores | Dos servicios distintos, Dockerfile independientes, Python slim y ejecución sin root. | [Usuarios](../backend/Dockerfile), [estadísticas](../estadisticas/Dockerfile), job `build` y manifiesto. |
| IE2, pruebas | CRUD, validación, duplicados, fallos HTTP, paginación e integridad. | [Suite](../tests), [JUnit](evidencias/run-40929310543/pytest.xml), [cobertura](evidencias/run-40929310543/coverage.xml). |
| IE3, seguridad y escalabilidad | Auditorías, SonarQube, bloqueos entre jobs, límites y tres réplicas. | [Workflow](../.github/workflows/CI.yml), [gate](evidencias/run-40929310543/sonarqube-quality-gate.json), [Compose](evidencias/comprobaciones-locales/compose-verificacion.json). |
| IE4, despliegue y trazabilidad | SHA, etiquetas OCI, checksum, manifiesto y paquete cargado en otro runner. | [Reporte](evidencias/run-40929310543/despliegue-simulado.json), [ejecución](evidencias/run-40929310543/execution.json), [logs](evidencias/run-40929310543/despliegue-simulado.log). |
| IE5, orquestación | Redes, volumen, salud, proxy, balanceo y recuperación. | [Compose](../compose.yaml), [Nginx](../infra/nginx.conf), [prueba local](evidencias/comprobaciones-locales/compose-verificacion.json), [despliegue](DESPLIEGUE.md). |

[Dependabot](../.github/dependabot.yml) está configurado; su activación en la
rama predeterminada y los ajustes de protección siguen pendientes de revisión
final. Esta tabla registra evidencias y pendientes, sin asignar una nota.

## Ejecución completa aprobada

- [GitHub Actions, ejecución 40929310543](https://github.com/SebaOre/Devops_Ev-1/actions/runs/40929310543).
- Commit: `0243f603d69c777e197463febb7ded705f8c59f7`.
- Cuatro jobs aprobados: `validate`, `sonar`, `build` y `deploy`.
- PyTest: 57 aprobadas; cobertura combinada de líneas y ramas de 99,60%.
- Auditorías: usuarios, 23 paquetes; estadísticas, 14; entorno, 59; cero avisos.
- SonarQube: gate `OK`, seguridad A, cobertura 99,6%, cero observaciones y hotspots.
- Despliegue: salud, CRUD, estadísticas, persistencia al recrear usuarios y
  retiro completo de recursos aprobados.

| Artefacto de Actions | ID |
| --- | --- |
| Pruebas y dependencias | `12920984285` |
| SonarQube | `12922087285` |
| Imágenes del commit | `12922521537` |
| Despliegue del commit | `12921823648` |

Las copias están en [evidencias/run-40929310543](evidencias/run-40929310543).
[SHA256SUMS.txt](evidencias/run-40929310543/SHA256SUMS.txt) registra sus checksums
para detectar cambios posteriores. Verifica las copias conservadas y no
constituye una firma del proveedor de CI. Los originales están sujetos a la
retención de siete días. No se incluye el archivo binario de imágenes en Git.
El archivo `despliegue-simulado.containers.json` conserva la salida original
de Compose en formato NDJSON: un objeto JSON por contenedor y por línea.

## Bloqueos y fallos comprobados

La [ejecución 40920411784](https://github.com/SebaOre/Devops_Ev-1/actions/runs/40920411784)
aprobó pruebas y bloqueó las etapas siguientes al encontrar avisos en
`setuptools` 79.0.1 preinstalado en el runner. La corrección a 84.1.0 se aplicó
a herramientas y Dockerfile. La
[ejecución 40921001795](https://github.com/SebaOre/Devops_Ev-1/actions/runs/40921001795)
aprobó auditorías, SonarQube y construcción. No se ignoraron esos avisos.

El ensayo local de fallo intencional de despliegue devolvió código 1, guardó el
error y limpió sus recursos. Se conservan su
[reporte](evidencias/comprobaciones-locales/despliegue-simulado-fallo.json) y
[log](evidencias/comprobaciones-locales/despliegue-simulado-fallo.log).
Este ensayo no se presenta como una ejecución remota fallida.

## Orquestación y escalado

La [verificación local de Compose](evidencias/comprobaciones-locales/compose-verificacion.json)
registró tres IPs atendiendo `/stats` y recuperación al retirar una réplica.
La ejecución final registró cero errores transitorios. También comprobó
persistencia después de `down/up`, HTTP 503 al detener usuarios y recuperación.
Son resultados de esa ejecución, no un ensayo de carga ni una garantía de
ausencia de interrupciones en todos los escenarios.

## Alcance

Las evidencias corresponden al commit indicado. Los resultados de seguridad
dependen de la fecha y de la base de avisos consultada. La cobertura mide los
servicios Python; el frontend tiene análisis estático y una comprobación DOM
local documentada en [SEGURIDAD.md](SEGURIDAD.md). La simulación es temporal y
no representa un servicio productivo publicado permanentemente.
