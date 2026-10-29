# Ejecucion de los microservicios con Docker

La orquestacion habitual se realiza con [Docker Compose](COMPOSE.md). Esta guia
conserva los comandos individuales utilizados para verificar las imagenes.

## Construir las imagenes

Ejecutar desde la raiz del repositorio. Los dos Dockerfile usan la raiz como
contexto de construccion; el punto final de cada comando es necesario.

```powershell
docker build --pull -f backend/Dockerfile -t ep2-usuarios:local .
docker build --pull -f estadisticas/Dockerfile -t ep2-estadisticas:local .
```

El contenedor de usuarios tambien incluye `frontend/`, porque su aplicacion sirve
el archivo HTML y los recursos estaticos. La base de datos local y los archivos
de entorno se excluyen mediante `.dockerignore`.

## Ejecutar y conectar los servicios

Estos comandos manuales permiten comprobar las imagenes antes de incorporar
Docker Compose en el paso 6.

```powershell
docker network create ep2-red
docker volume create ep2-usuarios-data
docker run -d --name ep2-usuarios --network ep2-red --network-alias usuarios --mount type=volume,source=ep2-usuarios-data,target=/data -p 127.0.0.1:8000:8000 ep2-usuarios:local
docker run -d --name ep2-estadisticas --network ep2-red -e USERS_SERVICE_URL=http://usuarios:8000 -p 127.0.0.1:8001:8001 ep2-estadisticas:local
docker ps
```

| Servicio | Interfaz | Salud | Documentacion |
| --- | --- | --- | --- |
| Usuarios | `http://localhost:8000/` | `http://localhost:8000/health` | `http://localhost:8000/docs` |
| Estadisticas | `http://localhost:8001/stats` | `http://localhost:8001/health` | `http://localhost:8001/docs` |

Dentro de Docker, estadisticas consulta `http://usuarios:8000`. El nombre
`usuarios` es un alias de red del contenedor de usuarios. La URL se puede cambiar
con la variable `USERS_SERVICE_URL`.

Usuarios guarda SQLite en `/data/microservicio.db`. El volumen conserva los
registros al reemplazar el contenedor. Cada imagen ejecuta Uvicorn con UID/GID
10001 y tiene un `HEALTHCHECK` que consulta su propio endpoint `/health`.

## Comprobacion manual

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8001/health
Invoke-RestMethod http://localhost:8001/stats
docker inspect --format '{{.State.Health.Status}}' ep2-usuarios ep2-estadisticas
docker exec ep2-usuarios id
docker exec ep2-estadisticas id
```

La pagina `/docs` de usuarios permite crear un registro mediante `POST /users/`.
Luego consultar `/stats` para comprobar que el resumen refleja el registro.

## Verificacion reproducible de las imagenes

Una vez construidas ambas imagenes, ejecutar desde la raiz:

```powershell
python scripts/verificar_docker.py
```

El script usa solamente la biblioteca estandar de Python y la CLI de Docker.
Crea una red, un volumen y dos contenedores temporales con nombres unicos y
puertos libres. Comprueba salud, usuario sin privilegios, dependencias, frontend,
comunicacion entre servicios, persistencia al recrear usuarios y respuesta 503 al
detenerlo. Al terminar elimina sus propios contenedores, volumen y red.

## Puertos locales

Los contenedores usan sus puertos habituales internamente y publican los puertos
del equipo solo en `127.0.0.1`. Si estos ya estan ocupados, cambiar el primer
numero del mapeo `-p`, por ejemplo `127.0.0.1:18000:8000`.

## Detener la demostracion

```powershell
docker stop ep2-estadisticas ep2-usuarios
docker rm ep2-estadisticas ep2-usuarios
docker network rm ep2-red
```

El volumen `ep2-usuarios-data` se conserva para reutilizar los registros.

## Referencias tecnicas

- [Buenas practicas de construccion de imagenes](https://docs.docker.com/build/building/best-practices/).
- [Referencia de Dockerfile: USER, COPY, CMD y HEALTHCHECK](https://docs.docker.com/reference/dockerfile/).
