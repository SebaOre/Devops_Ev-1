# Seguridad del pipeline

## Dependabot

`.github/dependabot.yml` configura revisiones semanales los lunes a las 10:00,
zona `America/Santiago`, para:

- Paquetes Python de la raiz, usuarios y estadisticas.
- Imagenes base de los dos Dockerfile y el proxy declarado en Compose.
- Acciones utilizadas en GitHub Actions.

Dependabot propondra actualizaciones mediante Pull Requests. Las actualizaciones
menores y parches de Python se agrupan. No se habilita merge automatico.
La configuracion debe estar integrada en la rama predeterminada del repositorio
para que GitHub la procese. Las alertas y actualizaciones de seguridad tambien
deben estar habilitadas en los ajustes de seguridad del repositorio.

## Auditoria de dependencias

Desde la raiz, instalar las herramientas en el entorno virtual del proyecto:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt -r requirements-security.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts/auditar_dependencias.py
```

El script usa `pip-audit` para resolver y auditar cada microservicio por separado,
ademas del entorno instalado de pruebas y herramientas. Esto incluye dependencias
transitivas propias de cada servicio, sin ocultarlas por combinar sus requisitos.
Genera `reports/pip-audit-usuarios.json`, `reports/pip-audit-estadisticas.json` y
`reports/pip-audit-entorno.json`.

`pip-audit` consulta los avisos publicados en PyPI. Devuelve un codigo de salida
distinto de cero cuando encuentra vulnerabilidades o no puede auditar. El job de
validacion falla ante ese resultado; la configuracion no usa `continue-on-error`
ni ignora identificadores de vulnerabilidades.

## SonarQube local

Con Docker Desktop iniciado y el reporte de cobertura generado:

```powershell
.\.venv\Scripts\python.exe scripts/sonarqube_local.py
```

El primer arranque descarga y prepara SonarQube Community Build y el escaner
oficial. Las imagenes usadas se fijan por digest en
`security/sonarqube-images.json`. El servidor requiere recursos de memoria:
el contenedor tiene un limite de 4 GiB y el escaner de 2 GiB, con limites de
512 MiB para el heap Java y el motor JavaScript del analisis.

El escaner recibe una copia temporal con fuentes, pruebas, Dockerfile,
configuracion y cobertura. Esa copia se monta en solo lectura y se elimina al
terminar. No incluye caches de Windows, entornos virtuales, bases de datos ni
credenciales locales.

Antes de iniciar se comprueba el espacio libre: 10 GB con las imagenes ya
descargadas, o 15 GB si falta alguna. Se usa GB decimal, es decir, 1000 millones
de bytes. Si despues de arrancar el servidor quedan menos de 3 GB, el script lo
detiene y falla. Estos limites dejan margen para archivos temporales del sistema.
En el runner Linux temporal, `--ci` exige 4 GB con las imagenes descargadas o
10 GB si falta alguna; no necesita reservar el margen de paginacion de Windows.

El script crea su propia red y un contenedor `ep2-sonarqube`, publica el panel
solo en `http://127.0.0.1:9000` y conserva sus datos en volumenes locales. Cambia
la contrasena inicial de `admin` por un valor aleatorio y guarda las credenciales
en `.sonar-local/credentials.json`, excluido de Git y del contexto de Docker.
El token de analisis se genera para el proyecto, se transmite por variable de
entorno al escaner y se revoca al terminar. No se imprime ni se guarda en el
repositorio.

Panel del proyecto: `http://127.0.0.1:9000/dashboard?id=devops-ep2`.
El usuario de acceso es `admin`; consultar la contrasena en el archivo local
de credenciales. No publicar ese archivo en las evidencias.

## Quality Gate

El proyecto usa el gate `EP2 Security`, aplicado sobre todo el codigo analizado:

| Condicion | Requisito |
| --- | --- |
| Clasificacion de seguridad | A, valor numerico 1. |
| Cobertura de codigo | Al menos 90%. |

La instancia local verificada tambien conserva condiciones de nuevo codigo:
cero observaciones nuevas y duplicacion de lineas no superior al 3%. Las
instancias nuevas del runner crean el gate con las dos condiciones explicitas
de la tabla: seguridad A y cobertura de al menos 90%.

Se analizan los dos servicios Python y el frontend. La cobertura procede de las
pruebas Python; el frontend sigue siendo analizado por seguridad y calidad, pero
no se incluye en el calculo de cobertura porque esta suite no prueba JavaScript.
Los resultados de mantenibilidad y los security hotspots se consultan en el panel;
el script no los descarta ni cambia automaticamente su estado de revision.

El escaner usa `sonar.qualitygate.wait=true`: espera a que el servidor termine
de procesar el analisis. Un gate rechazado, un error de analisis o un servidor
inaccesible produce un codigo de salida distinto de cero.
Si falla el escaner, el reporte registra `ANALYSIS_FAILED`; no presenta como
valido el Quality Gate de una ejecucion anterior.

Los archivos `reports/sonarqube-quality-gate.json`,
`reports/sonarqube-issues.json` y `reports/sonarqube-hotspots.json` guardan los
resultados de cada analisis.

## GitHub Actions

El workflow enlaza las comprobaciones de seguridad con la construccion:

1. `validate`: instala dependencias, ejecuta PyTest, exige cobertura minima y
   audita las dependencias. Guarda los reportes como artefactos.
2. `sonar`: necesita que `validate` termine correctamente. Recupera la cobertura
   y ejecuta `python scripts/sonarqube_local.py --ci` en Linux.
3. `build`: necesita la aprobacion de ambos y construye y verifica las imagenes
   identificadas por commit; los detalles estan en [PIPELINE.md](PIPELINE.md).

Con `--ci`, SonarQube se crea dentro del runner con un nombre y puerto temporales.
Las credenciales se mantienen en memoria y la instancia se elimina al terminar.
No se necesita exponer el computador del estudiante ni configurar un token de
un servidor externo. Cada ejecucion analiza su copia del proyecto en una
instancia independiente, sin usar la funcion de multiples ramas de la edicion
Community.

Ambos jobs generan anotaciones `::error::` si fallan. Los reportes quedan como
artefactos durante siete dias. La construccion ya depende de estos jobs y el
despliegue se incorporara en el paso 8. Para bloquear
tambien el merge, se deben exigir los checks de validacion y SonarQube mediante
proteccion de ramas en GitHub. La configuracion local por si sola no activa esa
proteccion ni acredita una ejecucion remota.

## Detener y reutilizar el servidor local

```powershell
docker stop ep2-sonarqube
docker start ep2-sonarqube
```

El script tambien inicia el contenedor existente si esta detenido. Los volumenes
y el archivo de credenciales deben conservarse juntos para reutilizar la
instancia. Esta instalacion con la base integrada de SonarQube es para el entorno
simulado de la evaluacion.

## Recursos del equipo Windows utilizado

Durante la verificacion local, C: llego a cero bytes libres. Docker registro
errores de escritura y su sistema de archivos paso a solo lectura. Tras detener
WSL se recupero espacio; tambien se observo crecimiento del archivo de paginacion
de Windows al iniciar SonarQube.

Se creo `%USERPROFILE%\.wslconfig`, fuera del repositorio, con:

```ini
[wsl2]
memory=6GB
swap=1GB
```

Estos limites se aplican globalmente a WSL 2, incluyendo Docker y Ubuntu. Se
reinicio WSL y se verifico una escritura real en un contenedor temporal. Las
imagenes y volumenes existentes siguieron disponibles. El estudiante libero
espacio adicional en C: antes de retomar la verificacion.

Para esta maquina se ejecutan el analisis y las construcciones de imagenes por
separado. Al terminar de consultar las evidencias, se puede detener SonarQube con
`docker stop ep2-sonarqube` para liberar memoria.

## Referencias

- [Configuracion de Dependabot](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference).
- [pip-audit y base de avisos de Python](https://pypi.org/project/pip-audit/).
- [Cobertura Python en SonarQube](https://docs.sonarsource.com/sonarqube-community-build/analyzing-source-code/test-coverage/python-test-coverage).
- [SonarScanner CLI](https://docs.sonarsource.com/sonarqube-community-build/analyzing-source-code/scanners/sonarscanner).
- [Memoria e intercambio de WSL](https://learn.microsoft.com/en-us/windows/wsl/wsl-config).

## Resultado local verificado

El 29 de octubre de 2026, el analisis final termino con codigo 0 y Quality Gate
`OK`: seguridad A y cobertura 99,6%. No quedaron observaciones abiertas ni
security hotspots. Las tres observaciones iniciales de accesibilidad del
formulario quedaron cerradas como corregidas.

Las auditorias independientes de usuarios (23 paquetes), estadisticas
(14 paquetes) y el entorno instalado (59 paquetes) terminaron sin
vulnerabilidades conocidas. Estos resultados corresponden a la fecha de
ejecucion y se vuelven a calcular en cada pipeline.

Ambas imagenes actualizadas pasaron la comprobacion de contenedores. SonarQube
quedo detenido para liberar memoria; su panel se puede recuperar con
`docker start ep2-sonarqube`.

La [ejecucion remota del paso 7](https://github.com/SebaOre/Devops_Ev-1/actions/runs/40921001795)
aprobo pruebas, auditorias, SonarQube y construccion de imagenes. La auditoria
remota reviso 23 paquetes de usuarios, 14 de estadisticas y 59 del entorno,
sin vulnerabilidades conocidas. SonarQube informo seguridad A, cobertura
99,6%, cero observaciones y cero hotspots. Se actualizo tambien `setuptools`
a 84.1.0 en las herramientas y los Dockerfile tras detectar una version
vulnerable preinstalada en el runner y la imagen base. La activacion de
Dependabot en la rama predeterminada y la proteccion de ramas siguen pendientes.
