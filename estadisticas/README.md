# Microservicio de estadisticas

Consulta el microservicio de usuarios mediante HTTP y calcula el total de usuarios,
el numero de dominios de correo distintos y la cantidad de usuarios por dominio.
Tiene una API propia y no accede directamente a la base de datos de usuarios.

## Ejecucion local

Ejecutar desde la raiz del repositorio, con las dependencias instaladas en el
entorno Python activo:

```powershell
python -m pip install -r backend/requirements.txt -r estadisticas/requirements.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Abrir otra terminal en la raiz del repositorio y ejecutar:

```powershell
$env:USERS_SERVICE_URL = "http://127.0.0.1:8000"
python -m uvicorn estadisticas.app.main:app --host 127.0.0.1 --port 8001
```

La variable `USERS_SERVICE_URL` se lee al iniciar el proceso. Su valor por defecto
es `http://127.0.0.1:8000`. En Docker Compose se configurara con el nombre DNS del
contenedor de usuarios.

## Endpoints

| Ruta | Funcion |
| --- | --- |
| `GET /health` | Comprueba que el proceso de estadisticas responde. |
| `GET /info` | Informa el nombre y la version del servicio. |
| `GET /stats` | Consulta usuarios y devuelve el resumen agregado. |
| `GET /docs` | Abre la documentacion interactiva de la API. |

Ejemplo de respuesta de `/stats` para tres usuarios:

```json
{
  "total_users": 3,
  "unique_domains": 2,
  "users_by_domain": {
    "example.com": 2,
    "example.org": 1
  }
}
```

La consulta recorre paginas de 100 usuarios. Si no hay usuarios, devuelve totales
en cero y un objeto `users_by_domain` vacio. Cada solicitud al servicio de usuarios
tiene un tiempo de espera de cinco segundos. Si falla o entrega una respuesta
invalida, `/stats` responde con HTTP 503, sin entregar un resumen parcial.

`/health` mide la disponibilidad de este proceso. La comunicacion con usuarios se
comprueba mediante `/stats`. El resumen refleja los registros leidos durante las
consultas; no representa una instantanea transaccional si hay cambios concurrentes.
