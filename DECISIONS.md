# Decisiones técnicas (`DECISIONS.md`)

## 1. Reglas de transición, validación de motivos y permisos en la capa de servicios (`ReservationLifecycleService`)

- **Contexto**: Tanto el paso a `ON_HOLD` en el backoffice como la cancelación por parte del cliente en el API son transiciones del ciclo de vida de `Reservation` que requieren validar el estado origen, normalizar y exigir un motivo no vacío, y bloquear la fila ante escrituras concurrentes.
- **Decisión**: Centralizar ambas transiciones (`hold_reservation` y `cancel_reservation`) en `ReservationLifecycleService` usando transacciones atómicas, `select_for_update(of=("self",))`, conjuntos explícitos de estados permitidos (`RESERVATION_HOLDABLE_STATUSES` y `RESERVATION_CANCELLABLE_STATUSES` en `constants.py`) y un validador común `normalize_reason`. Además, `hold_reservation` verifica `actor.has_perm("reservations.hold_reservation")` dentro del propio servicio además del `AuthenticatedPermissionRequiredMixin` de la vista (defensa en profundidad), y `cancel_reservation` filtra la consulta por `(pk=reservation_id, customer_id=customer_id)` para que una reserva ajena responda con `404 reservation_not_found` sin filtrar la existencia de recursos de otros clientes.
- **Impacto**: Las vistas de Django y los routers de Django Ninja quedan delgados (solo orquestan HTTP/formularios/schemas) y cualquier consumidor futuro del servicio hereda exactamente las mismas invariantes de dominio y seguridad.

## 2. Contrato de errores unificado (Problem Details RFC 9457) y mapeo semántico de códigos HTTP

- **Contexto**: El starter mapeaba cualquier `DomainError` a HTTP `400`, mientras que los errores de validación de Pydantic/Ninja (`ValidationError`) y la ausencia del header `Authorization` (`AuthenticationError`) devolvían el formato por defecto de Ninja (`{"detail": ...}`), rompiendo el contrato `ProblemDetailSchema` definido en `API_CONTRACT.md`.
- **Decisión**:
  1. Mantener las excepciones de dominio desacopladas de HTTP en `reservations/exceptions.py`, y definir una tabla `CODE_HTTP` en `client_portal/api.py` que traduce códigos de dominio a estados HTTP semánticos (`reservation_not_found` → `404`, `reservation_invalid_transition` → `409`, `reservation_reason_required` / `reservation_reason_too_long` → `422`), conservando `FAMILY_HTTP` como fallback.
  2. Registrar exception handlers explícitos en `NinjaAPI` para `AuthenticationError` y `ValidationError`, envolviéndolos en `ProblemDetailSchema`.
- **Impacto**: El frontend puede confiar en que **cualquier** respuesta no exitosa del API incluye siempre `type`, `title`, `status`, `detail`, `code`, `instance` y `errors`.

## 3. PostgreSQL en Docker con `select_for_update` real y proxy de mismo origen en Nginx/Vite

- **Contexto**: El servicio de reservas utiliza `select_for_update()` para serializar cambios de estado concurrentes. En SQLite ese bloqueo es un no-op y las escrituras bloquean todo el archivo de base de datos, lo cual resulta frágil bajo múltiples workers de Gunicorn. Por otro lado, exponer el frontend y el backend en orígenes distintos suele llevar a agregar middlewares de CORS.
- **Decisión**:
  1. Incorporar PostgreSQL 17 (`postgres:17-alpine`) como servicio `db` en `docker-compose.yml` con healthcheck y `psycopg[binary]`, manteniendo SQLite como fallback automático en `settings.py` cuando `POSTGRES_HOST` no está definido para no romper el flujo local con `uv run`.
  2. En la mini app cliente (`client-app/`), configurar Nginx (en producción/Docker) y el servidor de desarrollo de Vite para hacer proxy de `/api/*` hacia el backend, sirviendo SPA y API bajo el mismo origen.
- **Impacto**: Las garantías transaccionales de `ReservationLifecycleService` se cumplen realmente en PostgreSQL bajo Gunicorn multi-worker, y no fue necesario añadir `django-cors-headers` ni acoplar orígenes en el backend.

---

## Alternativa descartada

### Usar `django-cors-headers` y exponer el cliente contra un origen distinto (o usar un estado global pesado en el frontend)

- **Por qué se descartó**:
  - Añadir `django-cors-headers` introduce una dependencia adicional en el backend y obliga a sincronizar listas de orígenes permitidos (`CORS_ALLOWED_ORIGINS`) entre entornos locales y contenedores. Con un bloque `location /api/` en el contenedor Nginx de `client-app` y `server.proxy` en Vite, el navegador habla siempre con el mismo origen (`/api/v1/...`), eliminando preflights `OPTIONS` y configuración extra.
  - Del mismo modo, en el frontend se descartó incorporar librerías de ruteo o gestión de estado global (React Router, Redux, TanStack Query) porque la aplicación consta de dos pantallas (login y listado con modal de cancelación); un cliente HTTP tipado (`src/api/client.ts`) que traduce `ProblemDetail` a `ApiError` junto con estado local de React mantiene el bundle mínimo y el código directo de auditar.

---

## Declaración de uso de IA

Durante el desarrollo de esta prueba técnica se utilizó asistencia de IA (Antigravity) como apoyo para el análisis del repositorio base, generación de código boilerplate y redacción de pruebas y documentación, revisando y validando cada decisión arquitectónica, regla de negocio y prueba automatizada.
