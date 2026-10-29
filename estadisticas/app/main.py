from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .services import UsersServiceUnavailable, fetch_user_emails, summarize_users

app = FastAPI(title="Microservicio de Estadisticas", version="1.0.0")


class UserStats(BaseModel):
    total_users: int
    unique_domains: int
    users_by_domain: dict[str, int]


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Microservicio de Estadisticas"}


@app.get("/info")
def service_info():
    return {
        "service": "Microservicio de Estadisticas",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/stats", response_model=UserStats)
def user_stats():
    try:
        return summarize_users(fetch_user_emails())
    except UsersServiceUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail="No se pudieron consultar los datos del servicio de usuarios",
        ) from exc
