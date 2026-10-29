# Progreso de la Evaluacion Parcial 2

Cada paso se marca al terminar su verificacion.

- [x] 1/10 Revisar requisitos y proyecto existente.
- [x] 2/10 Preparar dos microservicios distintos y verificar su comunicacion.
- [x] 3/10 Crear y probar los dos Dockerfile.
- [x] 4/10 Incorporar pruebas automatizadas con PyTest.
- [x] 5/10 Configurar Dependabot, analisis de seguridad y bloqueo ante fallos.
- [x] 6/10 Configurar Docker Compose, persistencia, salud, seguridad y escalabilidad.
- [x] 7/10 Integrar construccion, pruebas y analisis en GitHub Actions.
- [ ] 8/10 Automatizar el despliegue simulado y su trazabilidad.
- [ ] 9/10 Documentar funcionamiento, calidad, evidencias y uso de IA.
- [ ] 10/10 Verificar la pauta completa y preparar la entrega del enlace de GitHub.

## Servicios

- Usuarios: `backend/app`, API de creacion, consulta, actualizacion y eliminacion.
- Estadisticas: `estadisticas/app`, API de resumen que consulta usuarios por HTTP.

## Verificacion del paso 2/10

El 29 de octubre de 2026 se ejecutaron ambos servicios localmente en procesos
independientes, usando puertos temporales y una base SQLite temporal para la
validacion. Las comprobaciones finalizaron correctamente:

- Inicio de ambos servicios y respuesta de sus endpoints `/health`.
- Respuesta de `/info` y generacion del esquema OpenAPI de estadisticas.
- Resumen vacio con total cero.
- Creacion de 105 usuarios por HTTP y conteo completo de dos paginas: 53 usuarios
  de `example.com` y 52 de `example.org`.
- Actualizacion y eliminacion de un usuario, reflejadas en el resumen.
- Respuesta HTTP 503 de `/stats` al detener usuarios, mientras `/health` de
  estadisticas mantiene su respuesta HTTP 200.

Los datos temporales de esta comprobacion no forman parte de la aplicacion.
Esta verificacion local aun no sustituye las pruebas PyTest del paso 4 ni las
evidencias de GitHub Actions pendientes.

## Verificacion del paso 3/10

El 29 de octubre de 2026 se construyeron correctamente las imagenes
`ep2-usuarios:local` y `ep2-estadisticas:local` desde sus respectivos Dockerfile,
con `python:3.11-slim-bookworm` como base.

Se ejecuto `python scripts/verificar_docker.py` contra Docker Desktop con motor
Linux. La verificacion finalizo con codigo de salida 0 y comprobo:

- Estado `healthy` de ambos contenedores mediante sus `HEALTHCHECK`.
- Ejecucion con UID/GID `10001:10001` y `pip check` correcto en ambas imagenes.
- Frontend accesible desde el contenedor de usuarios.
- Base SQLite nueva en `/data`, sin copiar la base local ni el archivo `.env`.
- Comunicacion HTTP entre contenedores mediante el alias DNS `usuarios`.
- Creacion de dos usuarios y resumen correcto con dos dominios distintos.
- Persistencia de ambos registros al recrear el contenedor usando el mismo volumen.
- Respuesta HTTP 503 al detener usuarios y salud HTTP 200 de estadisticas.

El script elimino los contenedores, la red y el volumen temporales al terminar.
Las imagenes permanecen disponibles localmente. Los comandos de construccion y
ejecucion estan documentados en [DOCKER.md](DOCKER.md). La orquestacion se
documenta en el paso 6 y la construccion automatizada en GitHub Actions, en el 7.

## Verificacion del paso 4/10

El 29 de octubre de 2026 se incorporaron 49 casos PyTest para ambos microservicios,
con SQLite en memoria y respuestas HTTP simuladas para las consultas externas.
La suite se ejecuto correctamente en dos entornos:

| Entorno | Resultado | Cobertura combinada de lineas y ramas |
| --- | --- | --- |
| Windows, Python 3.13.7, entorno `.venv` | 49 aprobadas, 0 fallas | 99,60% |
| Contenedor Linux temporal, Python 3.11.18 | 49 aprobadas, 0 fallas | 99,60% |

Se midio el 100% de las lineas y el 97,22% de las ramas. La rama pendiente
corresponde a configurar un motor distinto de SQLite. El minimo global exigido
por `pytest.ini` es del 90%. Los reportes XML locales quedaron en `reports/`.
`pip check` del entorno virtual no encontro incompatibilidades.

Las pruebas detectaron que actualizar `name` o `email` con `null` generaba un
error de integridad en la base de datos. Se corrigio `UserUpdate` para rechazar
esos valores con HTTP 422 y preservar el registro. Los campos omitidos siguen
permitiendo actualizaciones parciales. La imagen `ep2-usuarios:local` se
reconstruyo para incluir la correccion.

El workflow existente ahora instala las dependencias de pruebas y ejecuta la
suite en pushes a `develop` y Pull Requests hacia `main` o `develop`. El cambio
esta preparado localmente; aun falta subirlo y verificar una ejecucion real en
GitHub Actions. La proteccion de ramas y el resto del pipeline se completaran
en los pasos siguientes. Las instrucciones estan en [PRUEBAS.md](PRUEBAS.md).

## Verificacion del paso 5/10

El 29 de octubre de 2026 se configuro Dependabot para Python, Docker y GitHub
Actions, con revision semanal. Se preparo el workflow para auditar dependencias
y ejecutar SonarQube en una instancia temporal del runner. El job `sonar`
depende del resultado correcto de `validate`; los fallos generan anotaciones de
error y no se usa `continue-on-error`.

La auditoria inicial del entorno devolvio codigo 1 y 28 registros de avisos,
correspondientes a 14 identificadores distintos en tres paquetes: pip,
python-dotenv y Starlette. Se actualizaron esas dependencias y FastAPI para
mantener compatibilidad. Las versiones utilizadas son pip 26.2.2,
python-dotenv 1.2.4, Starlette 1.10.0 y FastAPI 0.162.0.

La auditoria final, ejecutada con `scripts/auditar_dependencias.py`, termino con
codigo 0:

| Alcance | Paquetes auditados | Vulnerabilidades conocidas |
| --- | --- | --- |
| Usuarios, resolucion independiente | 23 | 0 |
| Estadisticas, resolucion independiente | 14 | 0 |
| Entorno de pruebas y herramientas | 59 | 0 |

Se ejecuto SonarQube Community Build 26.10.0.133078 con SonarScanner CLI
8.1.0.6389. El analisis final termino con codigo 0 y Quality Gate `OK`:

- Clasificacion de seguridad A, valor 1.
- Cobertura 99,6%, superior al minimo de 90%.
- Cero observaciones abiertas y cero security hotspots.
- Tres observaciones iniciales de accesibilidad corregidas y cerradas.
- Condiciones de nuevo codigo aprobadas: cero observaciones nuevas y 0% de
  duplicacion, con limite de 3%.

Se corrigio tambien la insercion de datos de usuarios en HTML: ahora se usan
`textContent` y eventos asociados a los botones. Una comprobacion DOM con jsdom
y una API temporal verifico nombres con etiquetas y comillas, edicion y borrado
sin interpretar el nombre como HTML. La API del frontend usa el mismo origen
y puerto de la pagina.

Las 49 pruebas PyTest siguieron aprobando tras actualizar las dependencias.
Se reconstruyeron ambas imagenes y se repitio `scripts/verificar_docker.py` con
salud `healthy`, UID 10001, `pip check` correcto, comunicacion HTTP interna,
frontend, persistencia al recrear usuarios y HTTP 503 ante su detencion.

Durante estas comprobaciones hubo un incidente de espacio y paginacion de
Windows. Se recupero Docker, se limitaron los recursos de WSL y el estudiante
libero espacio adicional. SonarQube se detuvo despues del analisis aprobado
para liberar memoria, conservando sus volumenes y evidencias. Los detalles y
comandos estan en [SEGURIDAD.md](SEGURIDAD.md).

La configuracion de Dependabot y los jobs de GitHub Actions estan preparados
localmente. Aun falta subir los cambios, verificar su ejecucion real y exigir
los checks mediante proteccion de ramas al completar la integracion remota.

## Verificacion del paso 6/10

El 29 de octubre de 2026 se incorporo `compose.yaml` con usuarios, estadisticas
y un proxy Nginx oficial fijado por version y digest. Solo el proxy publica un
puerto del equipo: `127.0.0.1:18080`. Los servicios Python se comunican por una
red interna y usuarios conserva SQLite en un volumen propio.

Se configuraron dependencias con `service_healthy`, usuarios sin privilegios,
raiz de solo lectura, eliminacion de capacidades, `no-new-privileges`, limites
de CPU, memoria y PIDs, ausencia de swap adicional por contenedor y rotacion de
logs. El limite de memoria combinado es 448 MiB con una replica de estadisticas
y 704 MiB con tres.

`python scripts/verificar_compose.py` termino con codigo 0 usando un proyecto
temporal y comprobo:

- Inicio saludable, frontend, rutas de API y redireccion conservando el puerto.
- Aplicacion efectiva de los limites y opciones de seguridad en Docker.
- Tres replicas de estadisticas atendiendo consultas por el mismo proxy,
  sin recrearlo. Los logs registraron solicitudes a las tres IPs.
- Trafico estable al retirar una replica; cero errores transitorios en la
  ejecucion final de esta prueba.
- Persistencia de dos usuarios despues de `down` y `up`.
- HTTP 503 al detener usuarios y recuperacion al volver a iniciarlo.

El reporte quedo en `reports/compose-verificacion.json`. La prueba elimino solo
sus recursos temporales.

La construccion de Compose mediante Bake fallo en esta ruta de Windows con un
error gRPC por caracteres no ASCII. Se agrego `scripts/iniciar_compose.py`, que
construye las dos imagenes directamente con Docker y levanta Compose con
`--no-build --wait`. El lanzador completo se ejecuto correctamente.

El puerto 8080 ya estaba ocupado por otro servicio de Windows. Se uso el 18080,
comprobado como disponible. El proyecto normal quedo funcionando con sus tres
servicios `healthy`, y las rutas `/`, `/health`, `/stats` y `/users` respondieron
correctamente. SonarQube permanece detenido para liberar memoria.

Los comandos de inicio, escalado y detencion estan en [COMPOSE.md](COMPOSE.md).

## Verificacion del paso 7/10

Se integraron los jobs `validate`, `sonar` y `build` en GitHub Actions, con
dependencias que impiden construir si las pruebas, la auditoria o el Quality
Gate fallan. Las imagenes se identifican por el SHA completo del commit y se
empaquetan junto con un manifiesto de identidad y checksum.

La comprobacion local construyo y cargo ambas imagenes desde el archivo
comprimido y verifico su integridad, identificadores y etiquetas OCI. Se
agregaron ocho casos de integridad: la suite completa paso 57 pruebas con
99,60% de cobertura de los servicios. El workflow paso actionlint 1.7.12.

La rama `feature/evaluacion-2` se subio al repositorio configurado. La
[primera ejecucion real](https://github.com/SebaOre/Devops_Ev-1/actions/runs/40920411784)
aprobo las 57 pruebas, pero detecto tres registros de avisos en `setuptools`
79.0.1, preinstalado en el runner. Los servicios no presentaron dependencias
vulnerables; SonarQube y la construccion quedaron bloqueados como correspondia.

Se actualizo `setuptools` a 84.1.0 en las herramientas y en ambos Dockerfile,
despues de confirmar que la imagen base tambien incluia 79.0.1. La auditoria
local posterior aprobo usuarios (23 paquetes), estadisticas (14) y el entorno
(60), todos con cero vulnerabilidades conocidas.

La segunda ejecucion, sobre el commit
`7d0cb705fd9c719104b7e7b295dc535b602d02fa`, termino correctamente:

| Etapa remota | Resultado |
| --- | --- |
| PyTest, Python 3.11.17 | 57 aprobadas, cobertura 99,60%. |
| Auditoria de dependencias | Usuarios: 23 paquetes; estadisticas: 14; entorno: 59; cero avisos. |
| SonarQube | Quality Gate OK, seguridad A, cobertura 99,6%, cero observaciones y hotspots. |
| Construccion | Dos imagenes identificadas por el SHA completo del commit. |
| Verificacion del paquete | Carga correcta, checksum e identidad y etiquetas OCI coincidentes. |
| Publicacion | Artefactos de pruebas/dependencias, SonarQube e imagenes disponibles durante siete dias. |

Evidencia: [ejecucion completa aprobada en GitHub Actions](https://github.com/SebaOre/Devops_Ev-1/actions/runs/40921001795).
El artefacto de imagenes tiene ID `12918576874` y un tamano publicado de
81.842.820 bytes. Los reportes remotos se descargaron tambien en
`reports/github-run-40921001795/`, excluido de Git.

El despliegue automatico todavia no forma parte del workflow: corresponde al
paso 8. Dependabot debe integrarse en la rama predeterminada y la proteccion de
ramas aun debe configurarse al preparar la entrega.

Los detalles del flujo y los comandos locales estan en [PIPELINE.md](PIPELINE.md).

## Documentacion pendiente para la entrega

Registrar evidencias de ejecucion real, aportes de cada integrante y herramientas
de IA utilizadas con sus usos y referencias. Cada integrante debe escribir su
reflexion personal segun las condiciones de la pauta. Aun falta incorporar esas
reflexiones y los demas documentos finales.
