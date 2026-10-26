# Guía de Docker (`DOCKER.md`)

Esta solución empaqueta tres servicios orquestados con Docker Compose:

1. **`db`** (`postgres:17-alpine`): base de datos PostgreSQL 17 con volumen persistente (`postgres_data`) y healthcheck (`pg_isready`). No expone puerto al host por defecto (solo red interna de Docker).
2. **`backend`** ([`Dockerfile`](./Dockerfile)): imagen multi-stage con Python 3.13 + `uv`, usuario sin privilegios (`app`, UID `10001`), archivos estáticos recolectados con WhiteNoise y servida por **Gunicorn** (sin `runserver`). Al iniciar aplica migraciones y datos semilla de forma idempotente (`entrypoint.sh`).
3. **`client`** ([`client-app/Dockerfile`](./client-app/Dockerfile)): build estático de React + Vite servido por `nginxinc/nginx-unprivileged:1.27-alpine` (no root, puerto `8080` interno), con reverse proxy de `/api/*` hacia `http://backend:8000/api/`.

## Levantar toda la solución con un comando

```bash
docker compose up --build
```

O en segundo plano:

```bash
docker compose up -d --build
```

## URLs una vez levantado

- **Mini app cliente (Portal Cliente)**: [http://localhost:5173](http://localhost:5173)
- **Backoffice Django (Login)**: [http://localhost:8000/accounts/login/](http://localhost:8000/accounts/login/)
- **Backoffice Reservas**: [http://localhost:8000/backoffice/reservations/](http://localhost:8000/backoffice/reservations/)
- **API OpenAPI / Docs**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)

## Variables de entorno

`docker-compose.yml` incluye valores por defecto listos para probar sin pasos manuales adicionales. Si deseas personalizar secretos o puertos, copia `.env.example` a `.env`:

```bash
cp .env.example .env
```

Variables principales:

| Variable | Descripción | Default en Compose |
|---|---|---|
| `DJANGO_SECRET_KEY` | Clave secreta de Django | `django-insecure-docker-secret-key-change-me` |
| `DJANGO_DEBUG` | Modo debug (`true`/`false`) | `false` |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos separados por coma | `localhost,127.0.0.1,backend` |
| `API_JWT_SECRET` | Secreto para firmar tokens JWT HS256 | `django-insecure-docker-jwt-secret-change-me` |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Credenciales de PostgreSQL | `assessment` |
| `RUN_MIGRATIONS` | Ejecuta `migrate --noinput` al iniciar | `true` |
| `SEED_DEMO_DATA` | Ejecuta `seed_assessment_data` al iniciar | `true` |
| `BACKEND_PORT` / `CLIENT_PORT` | Puertos publicados en el host | `8000` / `5173` |

> **Nota sobre base de datos fuera de Docker**: si `POSTGRES_HOST` no está definido, `settings.py` utiliza automáticamente SQLite (`src/db.sqlite3`), manteniendo el flujo local con `uv run` sin requerir un servidor PostgreSQL local.

## Ejecutar tests y linter dentro de Docker

El `Dockerfile` del backend incluye un stage `test` con las dependencias de desarrollo (`pytest`, `factory_boy`, `ruff`):

```bash
docker build --target test -t assessment-backend-test .
docker run --rm assessment-backend-test pytest
docker run --rm assessment-backend-test ruff check .
```

## Reiniciar datos desde cero

Para detener los contenedores y eliminar el volumen de PostgreSQL:

```bash
docker compose down -v
```
