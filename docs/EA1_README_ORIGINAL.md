## Evidencias del trabajo colaborativo

Durante el desarrollo se realizaron los siguientes cambios mediante ramas y Pull Requests:

- Feature 1: desarrollo de una primera funcionalidad mediante una rama `feature/*`.
- Feature 2: incorporacion de una seccion de genero mediante la rama `feature/Segundo-cambio`.
- Feature 3: incorporacion del endpoint `/info` mediante la rama `feature/tercer-cambio`.
- Hotfix: correccion del endpoint `/health` mediante la rama `hotfix/correccion-health`.
- Sincronizacion de `main` hacia `develop`, resolviendo un conflicto de integracion en `backend/app/main.py`.
- Pull Requests utilizados para revision y posterior integracion de cambios.

## Modelo de ramificacion utilizado

## ¿Que es un modelo de ramificacion?

Un modelo de ramificacion define la forma en que un equipo organiza y administra las diferentes versiones del código dentro de un repositorio Git.

Las ramas permiten que diferentes desarrolladores trabajen en funcionalidades o correcciones de manera independiente, evitando modificar directamente una version estable mientras se realizan cambios.

En un proyecto colaborativo, el modelo de ramificacion establece:

- Queramas existen.
- Para que se utiliza cada rama.
- Desde que  rama se crean nuevas ramas.
- Hacia que rama se integran los cambios.
- Como se revisan los cambios.
- Como se incorporan nuevas funcionalidades.
- Como se realizan correcciones urgentes.

## Modelo de ramificacion considerado

### GitFlow

GitFlow organiza el desarrollo mediante diferentes tipos de ramas, cada una con un proposito definido.

Las ramas principales son:

- `main`: contiene las versiones estables.
- `develop`: concentra la integración del desarrollo.
- `feature/*`: permite desarrollar nuevas funcionalidades.
- `hotfix/*`: permite realizar correcciones sobre versiones estables.

Su estructura permite separar claramente el desarrollo de nuevas funcionalidades de las versiones consideradas estables.


## Integración continua con GitHub Actions

El proyecto incorpora un workflow ubicado en:

`.github/workflows/CI.yml`

El workflow se ejecuta automaticamente en:

- Cada `push` hacia `develop`.
- Cada Pull Request dirigido hacia `main`.

Las validaciones realizadas son:

1. Descarga del repositorio.
2. Configuracion de Python 3.11.
3. Instalacion de dependencias.
4. Validacion de sintaxis Python mediante `compileall`.
5. Verificacion de la estructura básica del proyecto.

El resultado exitoso de estas validaciones permite comprobar automaticamente que los cambios mantienen una estructura y sintaxis valida antes de continuar con el flujo de integración.

## Entorno Cloud simulado

Para esta evaluacion se utilizo GitHub como plataforma colaborativa y GitHub Actions como entorno de ejecucion automatizada en la nube.

El flujo implementado es:

Git - GitHub - Pull Request / Push - GitHub Actions - Validaciones automaticas - Resultado de ejecucion

No se realizo un despliegue hacia infraestructura productiva, ya que la evaluacion solicita un entorno Cloud simulado.

## Buenas practicas utilizadas

- Uso de ramas separadas para funcionalidades y correcciones.
- Uso de Pull Requests para integrar cambios.
- Revision de cambios antes del merge.
- Mensajes de commit descriptivos.
- Separacion entre `main` y `develop`.
- Uso de nombres de ramas descriptivos.
- Validacion automoatica mediante GitHub Actions.
- Resolucion documentada de conflictos de integracion.
- No almacenar credenciales o informacion sensible en el repositorio.

## Reflexiones

En esta evaluacion aprendimos como trabajar colaborativamente entre desarrolladores utilizando diferentes modelos de ramificacion. El modelo escogido por nuestro grupo fue GitFlow, el cual nos ayudo a entender como separar las ramas y que funcion cumple cada una dentro del proyecto.

Tambien aprendimos como crear y trabajar con Pull Requests, realizar revisiones y posteriormente hacer el merge de los cambios para integrarlos al proyecto principal. Esto nos permitio comprender mejor como se puede trabajar en equipo sin modificar directamente la rama principal.

Otro aprendizaje importante fue conocer los archivos YML y su utilizacion para la automatizacion. En nuestro caso, utilizamos GitHub Actions para crear un flujo que permitiera validar automaticamente el proyecto. Pudimos comprobar que las validaciones se ejecutaran correctamente tanto al realizar cambios en develop como mediante un Pull Request hacia main.

Finalmente, vimos la importancia de utilizar buenas practicas en un proyecto, como mantener una estructura ordenada, utilizar nombres adecuados para las ramas y commits, y dejar documentado el trabajo realizado. Esto nos permitio comprender que DevOps no solamente consiste en programar, sino tambien en organizar, colaborar y automatizar parte del proceso de desarrollo.

## Uso de Inteligencia Artificial

Durante el desarrollo del proyecto se utilizaron herramientas de Inteligencia Artificial como apoyo para:

- Revisar y mejorar la redaccion de documentacion.
- Comprender conceptos relacionados con Git, GitFlow y CI/CD.
- Apoyar la identificacion de errores durante el desarrollo.
- Organizar la documentacion tecnica del proyecto.


Los integrantes pueden trabajar en ramas independientes sin modificar
directamente la versión estable.

### Recuperación

Si una modificación genera un problema, Git permite revisar el historial
y recuperar una versión anterior.

### Integración controlada

Los cambios no tienen que incorporarse inmediatamente a la rama principal.
Pueden ser revisados antes de realizar el merge.

# 6. Modelos de ramificación

Existen diferentes estrategias para organizar el trabajo mediante ramas.

En este proyecto se consideran tres modelos principales:

1. GitFlow.
2. GitHub Flow.
3. Trunk-Based Development.

# 7. GitFlow

GitFlow organiza el desarrollo utilizando diferentes tipos de ramas según
la función que cumplen dentro del proyecto.

La estructura utilizada en este proyecto es:

```text
main
develop
feature/<nombre>
hotfix/<nombre>

## Prueba de integración CI/CD

Esta modificación se utiliza para verificar la ejecución automática del workflow de GitHub Actions mediante un Pull Request.
