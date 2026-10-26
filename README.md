# Prueba técnica full stack: backoffice + API cliente

Starter repo para evaluar criterio full stack con foco principal en Django.

## Stack

- Django 5.2
- Django templates para backoffice
- Django Ninja para API cliente
- Pydantic v2 para contratos y errores del API
- React 18 + TypeScript + Vite para la mini app cliente (`client-app/`)
- PostgreSQL 17 (en Docker) / SQLite (fallback local)
- pytest + factory_boy

## Dominio

El dominio es ficticio y está basado en reservas:

- `Customer`
- `Room`
- `Reservation` (`requested`, `confirmed`, `on_hold`, `cancelled`)

## Documentación del proyecto

- Consigna: [ASSESSMENT.md](./ASSESSMENT.md)
- Contrato del API: [API_CONTRACT.md](./API_CONTRACT.md)
- Guía de Docker: [DOCKER.md](./DOCKER.md)
- Decisiones técnicas: [DECISIONS.md](./DECISIONS.md)
- Mini app cliente: [client-app/README.md](./client-app/README.md)

## Correr todo con Docker (recomendado)

```bash
docker compose up --build
```

Servicios expuestos:

- **Mini app cliente**: [http://localhost:5173](http://localhost:5173)
- **Backoffice login**: [http://localhost:8000/accounts/login/](http://localhost:8000/accounts/login/)
- **Backoffice reservas**: [http://localhost:8000/backoffice/reservations/](http://localhost:8000/backoffice/reservations/)
- **API base**: [http://localhost:8000/api/v1/](http://localhost:8000/api/v1/)

Consulta [DOCKER.md](./DOCKER.md) para variables de entorno, ejecución de tests en contenedor y limpieza de volúmenes.

## Setup local (sin Docker)

Backend (usa SQLite automáticamente cuando `POSTGRES_HOST` no está definido):

```bash
uv sync
uv run python src/manage.py migrate
uv run python src/manage.py seed_assessment_data
uv run python src/manage.py runserver
```

Mini app cliente (en otra terminal):

```bash
cd client-app
npm install
npm run dev
```

## Checks de calidad

```bash
PYTHONPATH=src uv run pytest
uv run ruff check .
```

## Credenciales semilla

Se crean automáticamente con `seed_assessment_data`:

- Staff manager (incluye permiso `reservations.hold_reservation`)
  - username: `manager`
  - password: `demo1234`
- Staff operator (puede ver y editar, pero **no** poner en espera)
  - username: `operator`
  - password: `demo1234`
- Cliente Alice
  - email: `alice@example.com`
  - password: `demo1234`
- Cliente Bob
  - email: `bob@example.com`
  - password: `demo1234`
