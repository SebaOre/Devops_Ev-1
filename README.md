# Evaluación Parcial N°1 - Tu primer pipeline de despliegue

## 1. Introducción

Este repositorio corresponde a la Evaluación Parcial N°1 de la asignatura
Ingeniería DevOps

El objetivo del proyecto es utilizar un microservicio para implementar prácticas de control de versiones, ramificación,
trabajo colaborativo, revisión de código y automatización.

El trabajo utiliza Git y GitHub como herramientas principales para administrar
el código fuente y simular un flujo de trabajo colaborativo propio de un
entorno DevOps.

El proyecto busca establecer una base de trabajo que permita posteriormente
incorporar procesos de Integración Continua y Entrega Continua (CI/CD).

---

# 2. Objetivos del proyecto

Los principales objetivos son:

- Aplicar estrategias de ramificación mediante Git.
- Mantener trazabilidad sobre los cambios realizados en el código.
- Simular un entorno de desarrollo colaborativo utilizando GitHub.
- Implementar Pull Requests para revisión e integración de cambios.
- Aplicar convenciones para nombres de ramas y mensajes de commits.
- Utilizar GitHub Actions para automatizar verificaciones.
- Documentar buenas prácticas de trabajo colaborativo.
- Establecer una estructura de repositorio clara y mantenible.

---

# 3. Indicadores abordados

El proyecto aborda los siguientes indicadores:

### IL1.1

Definir estrategias de ramificación y control de versiones utilizando Git
en escenarios colaborativos de desarrollo en la nube, asegurando la
trazabilidad del código.

### IL1.2

Configurar flujos de trabajo DevOps que integren repositorios,
automatización y colaboración en un entorno Cloud simulado, considerando
estándares de CI/CD.

### IL1.3

Especificar convenciones y buenas prácticas de uso de repositorios mediante
documentación técnica para facilitar la colaboración y la calidad del código.

---

# 4. Tecnologías utilizadas

| Tecnología | Utilización |
|---|---|
| Git | Control de versiones |
| GitHub | Repositorio remoto y colaboración |
| GitHub Pull Requests | Revisión e integración de cambios |
| GitHub Actions | Automatización |
| Python | Lenguaje utilizado por el microservicio |
| FastAPI | Framework utilizado para la API |
| SQLAlchemy | Acceso y gestión de datos |

---

# 5. Control de versiones

## 5.1 ¿Qué es el control de versiones?

El control de versiones permite registrar y administrar los diferentes
cambios realizados sobre un proyecto durante su desarrollo.

En este proyecto Git permite mantener un historial de modificaciones,
identificar los cambios realizados, conocer quién los realizó y recuperar
versiones anteriores cuando sea necesario.

Esto resulta especialmente importante en un contexto colaborativo, debido a
que dos o más integrantes pueden trabajar sobre diferentes partes del
proyecto sin perder el historial de modificaciones.

---

## 5.2 Aplicación en el proyecto

Git se utiliza para:

- Registrar cada modificación mediante commits.
- Crear ramas independientes para desarrollar funcionalidades.
- Separar nuevas funcionalidades de la versión estable.
- Registrar quién realizó cada cambio.
- Integrar modificaciones mediante merge.
- Resolver conflictos entre diferentes versiones.
- Mantener trazabilidad del código.
- Permitir recuperar estados anteriores del proyecto.

---

## 5.3 Ventajas en un equipo colaborativo

El uso de control de versiones permite:

### Trazabilidad

Cada commit registra información sobre un cambio realizado.

Esto permite conocer:

- Qué se modificó.
- Cuándo se modificó.
- Quién realizó el cambio.
- Qué propósito tenía el cambio.

### Trabajo simultáneo

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