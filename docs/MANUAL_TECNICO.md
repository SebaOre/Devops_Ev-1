# Manual técnico de EP2

Instrucciones para ejecutar, comprobar y administrar la solución.
El informe y las evidencias para el docente están en [README.md](../README.md).
La [conclusión del trabajo](../README.md#conclusion) está en el mismo README.

- [Docker e inicio local](#docker)
- [Compose, persistencia y escalado](#compose)
- [Pruebas](#pruebas)
- [Seguridad y SonarQube](#seguridad)
- [Pipeline y artefactos](#pipeline)
- [Despliegue simulado](#despliegue)
- [Diagnóstico](#diagnostico)

Documento descriptivo con asistencia de IA; ver [declaración](../README.md#uso-de-ia).

<a id="docker"></a>

## 1. Docker e inicio local

Requisitos: Docker Desktop con motor Linux, Docker Compose y Python 3.11 o
posterior para los scripts. Ejecutar desde la raíz del repositorio:

```powershell
python devops/iniciar_compose.py
docker compose ps
```

El lanzador construye secuencialmente ambas imágenes y ejecuta Compose con
`--no-build --wait`. Esa secuencia evita el fallo de Bake observado en Windows
con los caracteres de esta ruta. Comandos equivalentes:

```powershell
docker build -f backend/Dockerfile -t ep2-usuarios:local .
docker build -f estadisticas/Dockerfile -t ep2-estadisticas:local .
docker compose up -d --no-build --wait
```

| Dirección local | Función |
| --- | --- |
| `http://localhost:18080/` | Frontend. |
| `http://localhost:18080/users/` | API de usuarios. |
| `http://localhost:18080/docs` | Swagger de usuarios. |
| `http://localhost:18080/stats` | Resumen de estadísticas. |
| `http://localhost:18080/health` | Salud de usuarios. |
| `http://localhost:18080/proxy-health` | Salud del proxy. |

Los Dockerfile usan Python 3.11 slim, instalan dependencias y ejecutan Uvicorn
con UID/GID 10001. Incluyen healthcheck y etiquetas OCI de revisión y repositorio.
`.dockerignore` excluye credenciales, bases, entornos, reportes y artefactos.

### API de estadísticas

El servicio expone `/health`, `/info`, `/stats` y `/docs` en su puerto interno
8001. `USERS_SERVICE_URL` se lee al iniciar: fuera de Docker su valor por defecto
es `http://127.0.0.1:8000`; Compose configura `http://usuarios:8000`.

Consulta páginas de 100 usuarios, con timeout de cinco segundos. Ante errores
de conexión, HTTP o datos inválidos devuelve 503 y no entrega totales parciales.
`/health` comprueba el proceso; `/stats` también comprueba su dependencia.
Ejemplo de respuesta para dos usuarios de dominios diferentes:

```json
{
  "total_users": 2,
  "unique_domains": 2,
  "users_by_domain": {"example.com": 1, "example.org": 1}
}
```

El resumen corresponde a los registros leídos durante la consulta; no es una
instantánea transaccional si ocurren cambios concurrentes.

<a id="compose"></a>

## 2. Compose, persistencia y escalado

`compose.yaml` orquesta usuarios, estadísticas y Nginx. Los servicios Python
comparten una red interna y no publican puertos del host. El proxy publica
`127.0.0.1:18080`; el frontend usa el mismo origen de la página.

Estadísticas espera la salud de usuarios y Nginx espera a ambos. El estado
`healthy` procede del healthcheck; `--wait` espera ese resultado al arrancar.
La política `unless-stopped` reinicia procesos que terminan; un healthcheck
fallido por sí solo no reinicia el contenedor.

Usuarios conserva SQLite en `/data/microservicio.db`, volumen
`devops-ep2_usuarios_data`. Detener e iniciar conservando los datos:

```powershell
docker compose down
docker compose up -d --no-build --wait
```

`down --volumes` elimina también el volumen. Los scripts automatizados usan esa
opción exclusivamente con sus proyectos temporales.

Escalar el servicio sin estado:

```powershell
docker compose up -d --no-build --scale estadisticas=3 --wait
docker compose ps
docker compose up -d --no-build --scale estadisticas=1 --wait
```

Nginx mantiene el puerto y distribuye `/stats` entre réplicas. Actualiza el DNS
interno cada cinco segundos. Al retirar una réplica puede haber errores
transitorios. Usuarios permanece en una instancia con SQLite; el escalado
horizontal demostrado corresponde a estadísticas.

| Servicio | Usuario | CPU máxima | Memoria | PIDs |
| --- | --- | --- | --- | --- |
| Usuarios | 10001:10001 | 0,50 | 256 MiB | 128 |
| Cada réplica de estadísticas | 10001:10001 | 0,50 | 128 MiB | 128 |
| Nginx | 101:101 | 0,25 | 64 MiB | 64 |

Los tres tienen raíz de solo lectura, capacidades eliminadas,
`no-new-privileges`, `/tmp` temporal y rotación de logs. No tienen swap adicional
sobre su límite de memoria. Los límites suman 448 MiB con una réplica de
estadísticas y 704 MiB con tres; no incluyen el motor Docker ni las construcciones.

La configuración admite `APP_PORT`, `USUARIOS_IMAGE` y `ESTADISTICAS_IMAGE`.
`.env.example` muestra los valores. Para cambiar el puerto en una sesión:

```powershell
$env:APP_PORT = "18765"
docker compose up -d --no-build --wait
```

<a id="pruebas"></a>

## 3. Pruebas automatizadas

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt -r requirements-security.txt
.\.venv\Scripts\python.exe -m pytest
```

En Linux, usar `.venv/bin/python`. Las pruebas usan SQLite en memoria y
respuestas HTTP simuladas; no requieren Uvicorn ni Docker. `pytest.ini` exige
cobertura combinada de líneas y ramas de al menos 90%. `.coveragerc` mide los
servicios Python y genera rutas relativas para SonarQube.

| Reporte generado | Contenido |
| --- | --- |
| `reports/pytest.xml` | Resultados JUnit. |
| `reports/coverage.xml` | Cobertura de Python. |

Comprobaciones reales con Docker, sobre imágenes locales construidas:

```powershell
python devops/verificar_docker.py
python devops/verificar_compose.py
```

Los scripts crean y retiran sus propios recursos. Comprueban comunicación,
frontend, persistencia, fallos de dependencia y recuperación. La verificación
de Compose también comprueba permisos, límites y tres réplicas mediante sus IPs.
El proyecto normal de la aplicación se conserva.

<a id="seguridad"></a>

## 4. Seguridad y SonarQube

### Instalación bloqueada de dependencias

Las imágenes y el runner instalan con `--only-binary :all:` y
`--require-hashes`. Se aceptan wheels con hashes registrados; no se ejecutan
scripts de instalación de distribuciones fuente. Los locks incluyen todas
las dependencias transitivas y se resolvieron para CPython 3.11 en Linux amd64:

| Lock | Entorno |
| --- | --- |
| `backend/requirements.lock` | Usuarios, 25 paquetes incluidos pip y setuptools. |
| `estadisticas/requirements.lock` | Estadísticas, 16 paquetes incluidos pip y setuptools. |
| `requirements-ci.lock` | Pruebas y herramientas, 59 paquetes. |

El instalador recibe también los requisitos originales. Si una actualización
modifica una versión sin regenerar el lock, la instalación falla por conflicto.
El ensayo Linux verificó rechazo de un hash alterado y de una versión
desincronizada, además de la suite y las auditorías.

Para regenerar en Linux con Python 3.11 y pip-tools:

```bash
python -m piptools compile --generate-hashes --allow-unsafe --strip-extras --output-file backend/requirements.lock backend/requirements.txt
python -m piptools compile --generate-hashes --allow-unsafe --strip-extras --output-file estadisticas/requirements.lock estadisticas/requirements.txt
python -m piptools compile --generate-hashes --allow-unsafe --strip-extras --output-file requirements-ci.lock requirements-test.txt requirements-security.txt
```

Los comandos de desarrollo en Windows usan los requisitos originales; los
locks anteriores corresponden al entorno Linux validado de contenedores y CI.

### Auditoría y análisis

Auditar las dependencias de cada servicio y el entorno instalado:

```powershell
.\.venv\Scripts\python.exe devops/auditar_dependencias.py
```

Se auditan los locks completos de ambos servicios, sin volver a resolver otras
versiones, y el entorno instalado. Se generan `reports/pip-audit-usuarios.json`,
`pip-audit-estadisticas.json` y `pip-audit-entorno.json`. Un aviso o error devuelve código distinto
de cero. Dependabot tiene configuración semanal para Python, Docker y Actions
en `.github/dependabot.yml`; debe integrarse en la rama predeterminada y tener
sus opciones habilitadas para completar su activación.

Ejecutar SonarQube local después de generar cobertura:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe devops/sonarqube_local.py
```

El script necesita Docker Linux y reserva al menos 10 GB libres si las imágenes
están descargadas o 15 GB si falta alguna. El servidor tiene límite de 4 GiB y
el escáner de 2 GiB. En el equipo utilizado se ejecutaron análisis y
construcciones por separado; WSL tiene límites de 6 GB de memoria y 1 GB de swap.

Las imágenes de SonarQube y Scanner están fijadas por digest en
`devops/sonarqube-images.json`. La copia de análisis excluye bases, caches y
credenciales. Los tokens temporales se revocan al terminar. Las credenciales
locales quedan en `.sonar-local/credentials.json`, excluido de Git y Docker.

Panel: `http://127.0.0.1:9000/dashboard?id=devops-ep2`. Para reutilizar o detener
la instancia, conservando sus datos:

```powershell
docker start ep2-sonarqube
docker stop ep2-sonarqube
```

El gate de CI exige seguridad A y cobertura de al menos 90%. Un error del
escáner o gate rechazado bloquea la entrega. Se generan
`reports/sonarqube-quality-gate.json`, `sonarqube-issues.json` y
`sonarqube-hotspots.json`. La cobertura viene de PyTest; SonarQube la recibe y
analiza el código. Si el análisis falla no se presenta un resultado antiguo
como una aprobación nueva.

<a id="pipeline"></a>

## 5. GitHub Actions y artefactos

`.github/workflows/CI.yml` define `validate`, `sonar`, `build` y `deploy`.
Los eventos y resultados están en el [informe principal](../README.md#despliegue).
`needs` impide continuar si una etapa requerida falla; no se usa
`continue-on-error`. Los jobs generan anotaciones de error y conservan reportes.

Cada construcción requiere un checkout limpio y el SHA esperado. Las imágenes
llevan ese SHA como etiqueta y revisión OCI. El paquete contiene
`artifacts/images.tar.gz` e `images-manifest.json`, con repositorio, identidades,
checksum, fecha UTC e ID/intento de ejecución. Se publica como `imagenes-<SHA>`
y tiene retención de siete días. No requiere un registro de imágenes externo.

Para comprobar cambios locales sin atribuirlos a un commit:

```powershell
.\.venv\Scripts\python.exe devops/construir_imagenes.py --local
.\.venv\Scripts\python.exe devops/verificar_artefactos.py --load --revision working-tree
```

El modo local usa una etiqueta aleatoria y revisión `working-tree`. Requiere
al menos 2 GB libres para empaquetar. El verificador comprueba checksum antes
de cargar, revisión, identificadores y etiquetas. Los directorios `reports/`,
`artifacts/` y `.sonar-local/` son resultados locales y no se entregan completos;
las copias seleccionadas están en `docs/evidencias/`.

<a id="despliegue"></a>

## 6. Despliegue simulado

`deploy` usa otro runner y descarga el paquete construido en la misma ejecución.
El script verifica repositorio, commit, checkout limpio, ID e intento, checksum,
identidades y etiquetas. Inicia un proyecto Compose único con un puerto local
aleatorio y `--no-build --pull never --wait`. Solo el proxy oficial se descarga
por digest; las dos imágenes Python provienen del paquete aprobado.

Se comprueban frontend, salud, CRUD, estadísticas y persistencia al recrear
usuarios. Antes de retirar el entorno se guardan logs y estado. Se ejecuta
`down --volumes` sobre ese proyecto y se comprueba que no queden sus recursos.

| Archivo | Contenido |
| --- | --- |
| `reports/despliegue-simulado.json` | Manifiesto, revisión, identidades, pruebas, fechas y limpieza. |
| `reports/despliegue-simulado.log` | Logs de los servicios. |
| `reports/despliegue-simulado.containers.json` | Salida de Compose en NDJSON. |

El artefacto `despliegue-<SHA>` conserva estos archivos durante siete días. La
simulación es temporal y su URL deja de existir al finalizar. Para reintentar
en GitHub, usar **Re-run all jobs**: se exige paquete del mismo intento.

Con el paquete local generado en el punto anterior:

```powershell
.\.venv\Scripts\python.exe devops/desplegar_simulado.py --revision working-tree
.\.venv\Scripts\python.exe devops/desplegar_simulado.py --revision working-tree --simulate-failure
```

El primer comando debe aprobar y limpiar sus recursos. El segundo es un ensayo
intencional que debe devolver código 1, guardar diagnóstico y completar la
limpieza; escribe reportes con sufijo `-fallo`. Esa opción solo se permite
localmente. Para un paquete de GitHub se debe indicar su SHA completo.

<a id="diagnostico"></a>

## 7. Diagnóstico y estructura

```powershell
docker compose ps
docker compose logs --tail 50 usuarios estadisticas gateway
docker compose config --quiet
```

Si `/stats` devuelve 503, consultar la salud y los logs de usuarios. El proxy
saludable solo confirma su propio proceso; `/stats` comprueba además la
comunicación entre los servicios. El puerto 18080 se eligió porque 8080 estaba
ocupado por otro servicio del equipo.

| Carpeta | Contenido |
| --- | --- |
| `backend/` | Usuarios, interfaz en `backend/frontend/` y su Dockerfile. |
| `estadisticas/` | Segundo microservicio y su Dockerfile. |
| `tests/` | Pruebas automatizadas. |
| `.github/` | Pipeline y Dependabot. |
| `devops/` | Scripts de automatización, `nginx.conf` y `sonarqube-images.json`. |
| `docs/` | Manual y evidencias. |

Referencias: [Compose y salud](https://docs.docker.com/compose/how-tos/startup-order/),
[Dependabot](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference),
[cobertura Python en SonarQube](https://docs.sonarsource.com/sonarqube-community-build/analyzing-source-code/test-coverage/python-test-coverage).
