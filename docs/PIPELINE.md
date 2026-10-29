# Integracion continua e imagenes

El workflow `.github/workflows/CI.yml` se activa con pushes a `main`, `develop`,
`feature/**` y `codex/**`, con Pull Requests hacia `main` o `develop`, y manualmente
desde GitHub Actions. Utiliza runners `ubuntu-24.04` y Python 3.11.

## Orden y bloqueo

1. `validate`: valida sintaxis, ejecuta PyTest, exige cobertura del 90% y audita
   por separado las dependencias de ambos servicios y del entorno de pruebas.
2. `sonar`: recupera la cobertura y ejecuta SonarQube en una instancia temporal.
   Necesita que `validate` apruebe y exige un Quality Gate correcto.
3. `build`: necesita que ambos jobs anteriores aprueben. Valida Compose,
   construye los dos Dockerfile y verifica el paquete de imagenes.

Los fallos detienen las etapas dependientes y generan una anotacion de error.
No se utiliza `continue-on-error`. La proteccion de ramas para exigir checks al
integrar cambios debe configurarse en GitHub; `needs` bloquea el pipeline.

## Artefactos y trazabilidad

Cada construccion usa el SHA completo de `github.sha` como etiqueta de las dos
imagenes y como etiqueta OCI `org.opencontainers.image.revision`. El script
comprueba que el checkout este limpio y que su HEAD coincida con ese SHA.
Tambien registra el repositorio en `org.opencontainers.image.source`.

`scripts/construir_imagenes.py` genera:

- `artifacts/images.tar.gz`: ambas imagenes mediante `docker image save` y gzip.
- `artifacts/images-manifest.json`: revision, referencias, identificadores de
  imagen, repositorio, fecha UTC, ID e intento del workflow y checksum SHA-256
  del archivo comprimido.

`scripts/verificar_artefactos.py --load` comprueba el checksum antes de cargar,
la revision esperada, los identificadores reales y las etiquetas OCI. El job
publica los dos archivos como `imagenes-<SHA>`, con retencion de siete dias y sin
compresion adicional del servicio de artefactos. No requiere una cuenta de
registro de contenedores. Los reportes de pruebas/auditoria y SonarQube se
guardan en artefactos separados, tambien durante siete dias.

La etapa siguiente de despliegue debe recuperar este paquete y verificarlo,
para ejecutar las mismas imagenes aprobadas sin reconstruirlas.

## Comprobacion local

Con Docker disponible y al menos 2 GB libres:

```powershell
.\.venv\Scripts\python.exe scripts/construir_imagenes.py --local
.\.venv\Scripts\python.exe scripts/verificar_artefactos.py --load --revision working-tree
```

El modo local usa una etiqueta aleatoria `local-<identificador>` y revision
`working-tree`: permite comprobar cambios sin atribuirlos al ultimo commit.
No sustituye la evidencia de GitHub Actions. `artifacts/` queda excluido de Git
y del contexto de construccion Docker.

El 29 de octubre de 2026 se verifico localmente la construccion, compresion,
carga e identidad de ambas imagenes. El archivo generado midio 78.792.551 bytes.
La suite completa paso 57 casos con cobertura de servicios de 99,60%, incluyendo
ocho casos que comprueban el rechazo de paquetes alterados, commits incorrectos,
servicios ausentes e identidad o etiquetas incompatibles. El workflow tambien
paso la validacion estatica con actionlint 1.7.12.

La primera ejecucion remota aprobo las 57 pruebas y bloqueo la entrega al
detectar avisos de seguridad en `setuptools` 79.0.1, preinstalado en el runner.
Se incorporo `setuptools==84.1.0` a las herramientas de seguridad para actualizar
esa dependencia al preparar el entorno. La imagen base Python tambien incluia
79.0.1, por lo que ambos Dockerfile actualizan esta herramienta a 84.1.0.
No se ignoraron avisos de la auditoria.
El resultado completo se registrara despues de repetir el pipeline.
