# Mini app cliente (`client-app/`)

Aplicación React + TypeScript + Vite que consume el API de clientes (`/api/v1`) para:

- Iniciar sesión (`POST /api/v1/auth/login` + `GET /api/v1/auth/me`).
- Consultar "Mis reservas" (`GET /api/v1/reservations/`).
- Cancelar una reserva propia con motivo obligatorio (`POST /api/v1/reservations/{id}/cancel`).
- Mostrar errores estables del contrato ProblemDetail (`code`, `detail`).

## Ejecutar en local (sin Docker)

Con el backend corriendo en `http://127.0.0.1:8000`:

```bash
cd client-app
npm install
npm run dev
```

La app quedará disponible en `http://localhost:5173`. Vite redirige automáticamente `/api/*` hacia `http://127.0.0.1:8000` (configurable mediante `VITE_API_PROXY_TARGET`), evitando problemas de CORS.

## Build de producción

```bash
cd client-app
npm run build
```

## Credenciales demo

- `alice@example.com` / `demo1234`
- `bob@example.com` / `demo1234`
