# Contrato base del API cliente

Base URL local:

- `http://127.0.0.1:8000/api/v1`

## Auth

### `POST /auth/login`

Request:

```json
{
  "email": "alice@example.com",
  "password": "demo1234"
}
```

Response `200`:

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer"
}
```

### `GET /auth/me`

Header:

```text
Authorization: Bearer <token>
```

Response `200`:

```json
{
  "id": "uuid",
  "email": "alice@example.com",
  "display_name": "Alice Stone"
}
```

## Reservations

### `GET /reservations/`

Header:

```text
Authorization: Bearer <token>
```

Response `200`:

```json
[
  {
    "id": "uuid",
    "room_name": "Room A",
    "status": "requested",
    "starts_at": "2026-04-20T15:00:00-05:00",
    "ends_at": "2026-04-20T17:00:00-05:00",
    "cancel_reason": null
  }
]
```

### `POST /reservations/{reservation_id}/cancel`

Header:

```text
Authorization: Bearer <token>
```

Request:

```json
{
  "reason": "Change of schedule"
}
```

Response `200`:

```json
{
  "id": "uuid",
  "room_name": "Room A",
  "status": "cancelled",
  "starts_at": "2026-04-20T15:00:00-05:00",
  "ends_at": "2026-04-20T17:00:00-05:00",
  "cancel_reason": "Change of schedule"
}
```

Error codes para este endpoint:

- `401` (`auth_required`, `auth_invalid_token`): token faltante o inválido.
- `404` (`reservation_not_found`): la reserva no existe o pertenece a otro cliente.
- `409` (`reservation_invalid_transition`): la reserva ya está cancelada.
- `422` (`reservation_reason_required`, `reservation_reason_too_long`, `validation_error`): motivo vacío, demasiado largo o payload inválido.

## Error format

Los errores de dominio y auth deben mantenerse en este formato:

```json
{
  "type": "urn:assessment:problem:auth_invalid_credentials",
  "title": "Authentication Failed",
  "status": 401,
  "detail": "Invalid email or password.",
  "code": "auth_invalid_credentials",
  "instance": "/api/v1/auth/login",
  "errors": null
}
```

El endpoint de cancelación que debe construir el candidato debe seguir este
mismo contrato.
