# Pruebas automatizadas

## Ejecutar localmente

Desde la raiz del repositorio, con Python 3.11 o posterior:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
.\.venv\Scripts\python.exe -m pytest
```

En Linux, usar `.venv/bin/python` en lugar de `.\.venv\Scripts\python.exe`.

No es necesario iniciar Uvicorn ni Docker para esta suite. `TestClient` ejecuta
las aplicaciones en el proceso de pruebas. SQLite funciona en memoria y cada
prueba de usuarios tiene una base independiente. Las solicitudes HTTP externas
de estadisticas se reemplazan por respuestas controladas para comprobar los
resultados y las fallas sin depender de otros procesos.

## Casos cubiertos

| Area | Comprobaciones |
| --- | --- |
| Usuarios | Crear, listar, consultar, actualizar y eliminar; paginacion; actualizaciones parciales y vacias. |
| Validacion | Campos requeridos, correo invalido, ID invalido, valores nulos y preservacion de registros ante cambios rechazados. |
| Integridad | Correos duplicados en creacion y actualizacion; actualizacion conservando el propio correo; usuarios inexistentes. |
| Disponibilidad | Endpoints de salud e informacion; HTML y recursos estaticos de usuarios. |
| Estadisticas | Totales, dominios sin distinguir mayusculas, resumen vacio y respuesta sin correos individuales. |
| Paginacion remota | Conjuntos de 0, 2, 100, 105 y 200 usuarios, incluyendo la pagina vacia final. |
| Fallos remotos | Timeout, conexion rechazada, error HTTP, JSON invalido, respuesta mal formada y fallo en paginas posteriores sin devolver totales parciales. |
| Artefactos | Checksum, revision, servicios requeridos, checkout limpio e identidad y etiquetas OCI de las imagenes. |

La suite combina pruebas unitarias de los calculos y del cliente de usuarios con
pruebas de API que ejercitan rutas, validacion y operaciones reales en SQLite.
La comunicacion entre procesos y la persistencia de los contenedores se
verifican por separado con `python scripts/verificar_docker.py`.

## Criterio de calidad y reportes

`pytest.ini` configura un minimo de cobertura global del 90%, incluyendo ramas.
`.coveragerc` limita los reportes a `backend/app` y `estadisticas/app` y utiliza
rutas relativas para que SonarQube pueda leerlos dentro de Linux.
Es un criterio definido para este
proyecto; la pauta de la evaluacion no exige un porcentaje concreto. Una prueba
fallida o una cobertura inferior al minimo produce un codigo de salida distinto
de cero.

Cada ejecucion completa genera:

- `reports/coverage.xml`: cobertura en formato XML, apta para herramientas de analisis.
- `reports/pytest.xml`: resultados JUnit XML.
- Resumen de cobertura y lineas pendientes en la terminal.

Los reportes, caches y el entorno virtual estan excluidos de Git. Estos archivos
son resultados de ejecucion y deben regenerarse al cambiar el codigo.

## Resultado verificado

El 29 de octubre de 2026 pasaron 49 casos tanto en Windows con Python 3.13.7
como en un contenedor Linux temporal con Python 3.11.18. La cobertura combinada
de lineas y ramas fue de 99,60%: 100% de lineas y 97,22% de ramas. La rama no
ejecutada corresponde a configurar una base de datos distinta de SQLite.

La suite detecto y permitio corregir las actualizaciones de `name` o `email`
con `null`: ahora reciben HTTP 422 y conservan los datos originales. Una
actualizacion parcial puede seguir omitiendo esos campos.

Ambas ejecuciones emitieron dos avisos de deprecacion de las APIs usadas por
SQLAlchemy y Starlette/AnyIO; no hubo fallas de pruebas.

En el paso 7 se agregaron ocho casos para la integridad de los artefactos. La
suite de Windows paso los 57 casos y mantuvo la cobertura de servicios en 99,60%.

## Integracion continua

El workflow `.github/workflows/CI.yml` instala `requirements-test.txt` y ejecuta
`python -m pytest` con Python 3.11. Se activa con pushes a `main`, `develop`,
`feature/**` y `codex/**`, y Pull Requests dirigidos a `main` o `develop`.
Si las pruebas o la cobertura fallan,
el job falla. La proteccion de ramas para exigir este check antes de integrar
cambios se configurara al completar el pipeline.

Las etapas de SonarQube y construccion dependen de estas pruebas. El flujo y los
artefactos se describen en [PIPELINE.md](PIPELINE.md). El despliegue automatico
corresponde al paso 8.

## Referencias tecnicas

- [Pruebas con FastAPI y TestClient](https://fastapi.tiangolo.com/tutorial/testing/).
- [Respuestas simuladas con monkeypatch](https://docs.pytest.org/en/stable/how-to/monkeypatch.html).
- [Configuracion y umbral de cobertura de pytest-cov](https://pytest-cov.readthedocs.io/en/latest/config.html).
