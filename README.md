# Microservicio CRUD de Usuarios

Microservicio básico en Python con FastAPI y SQLAlchemy. Frontend y backend separados en carpetas.

## Estructura del proyecto

```
microservicio/
├── backend/                 # API (FastAPI + SQLAlchemy)
│   ├── app/
│   │   ├── main.py          # Punto de entrada
│   │   ├── config.py        # Configuración BD
│   │   ├── database.py      # Conexión SQLAlchemy
│   │   ├── models/user.py   # Modelo User
│   │   ├── schemas/user.py  # Schemas Pydantic
│   │   ├── routers/users.py # Endpoints
│   │   └── crud/user.py     # Operaciones BD
│   ├── requirements.txt
│   ├── .env
│   └── run.bat
└── frontend/                # Interfaz web
    └── index.html
```

## Requisitos

- Python 3.10+

## Instalación (backend)

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

## Configuración

Copia `.env` en `backend/` y ajusta `DATABASE_URL` si lo necesitas.

- **SQLite** (por defecto, no requiere servidor): `sqlite:///./microservicio.db`
- **PostgreSQL**: `postgresql://usuario:pass@localhost:5432/nombre_db`
- **MySQL**: `mysql+pymysql://usuario:pass@localhost:3306/nombre_db`

## Ejecución

Desde la carpeta `backend`:

```bash
venv\Scripts\activate
uvicorn app.main:app --reload
```

O doble clic en `backend\run.bat`.

## Frontend

Interfaz web básica para gestionar usuarios (crear, listar, editar, eliminar).

- Interfaz: http://localhost:8000/

## Documentación

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

## Endpoints

| Método | Ruta          | Descripción       |
|--------|---------------|-------------------|
| GET    | /users        | Listar todos      |
| GET    | /users/{id}   | Obtener por ID    |
| POST   | /users        | Crear usuario     |
| PUT    | /users/{id}   | Actualizar        |
| DELETE | /users/{id}   | Eliminar          |