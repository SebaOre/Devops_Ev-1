import json
import os
from collections import Counter
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL", "http://127.0.0.1:8000").rstrip("/")
PAGE_SIZE = 100
REQUEST_TIMEOUT = 5


class UsersServiceUnavailable(Exception):
    """El servicio de usuarios no responde o entrega datos invalidos."""


def fetch_user_emails() -> list[str]:
    """Recorre todas las paginas del servicio de usuarios por HTTP."""
    emails = []
    skip = 0

    while True:
        query = urlencode({"skip": skip, "limit": PAGE_SIZE})
        request = Request(
            f"{USERS_SERVICE_URL}/users/?{query}",
            headers={"Accept": "application/json"},
        )
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                users = json.load(response)
        except (URLError, OSError, ValueError) as exc:
            raise UsersServiceUnavailable from exc

        if not isinstance(users, list) or len(users) > PAGE_SIZE:
            raise UsersServiceUnavailable

        for user in users:
            email = user.get("email") if isinstance(user, dict) else None
            if not isinstance(email, str) or email.count("@") != 1:
                raise UsersServiceUnavailable
            local, domain = email.split("@")
            if not local.strip() or not domain.strip():
                raise UsersServiceUnavailable
            emails.append(email)

        if len(users) < PAGE_SIZE:
            return emails
        skip += len(users)


def summarize_users(emails: list[str]) -> dict:
    """Calcula un resumen sin exponer nombres ni correos individuales."""
    domains = Counter(email.rsplit("@", 1)[1].lower() for email in emails)
    return {
        "total_users": len(emails),
        "unique_domains": len(domains),
        "users_by_domain": dict(sorted(domains.items())),
    }
