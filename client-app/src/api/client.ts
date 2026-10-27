import type {
  ClientProfile,
  ProblemDetail,
  Reservation,
  TokenResponse,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

const ERROR_MESSAGES_ES: Record<string, string> = {
  auth_invalid_credentials: "Correo o contraseña inválidos.",
  auth_invalid_token: "Tu sesión expiró o el token no es válido.",
  auth_required: "Debes iniciar sesión para continuar.",
  reservation_not_found: "No se encontró la reserva solicitada.",
  reservation_invalid_transition:
    "Esta reserva ya no puede cancelarse desde su estado actual.",
  reservation_reason_required: "Debes ingresar un motivo para cancelar.",
  reservation_reason_too_long:
    "El motivo ingresado supera el máximo permitido (500 caracteres).",
  validation_error: "Los datos enviados no son válidos.",
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly detail: string;
  readonly errors?: Array<Record<string, unknown>> | null;

  constructor(problem: {
    status: number;
    code: string;
    detail: string;
    errors?: Array<Record<string, unknown>> | null;
  }) {
    const message = ERROR_MESSAGES_ES[problem.code] ?? problem.detail;
    super(message);
    this.name = "ApiError";
    this.status = problem.status;
    this.code = problem.code;
    this.detail = problem.detail;
    this.errors = problem.errors;
  }
}

async function request<T>(
  path: string,
  options: RequestInit & { token?: string | null } = {},
): Promise<T> {
  const { token, headers, ...rest } = options;
  const finalHeaders: Record<string, string> = {
    Accept: "application/json",
    ...(headers as Record<string, string> | undefined),
  };

  if (rest.body && !finalHeaders["Content-Type"]) {
    finalHeaders["Content-Type"] = "application/json";
  }

  if (token) {
    finalHeaders.Authorization = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...rest,
      headers: finalHeaders,
    });
  } catch {
    throw new ApiError({
      status: 0,
      code: "network_error",
      detail: "No se pudo conectar con el servidor. Verifica tu conexión.",
    });
  }

  if (!response.ok) {
    let payload: Partial<ProblemDetail> | null = null;
    try {
      payload = (await response.json()) as Partial<ProblemDetail>;
    } catch {
      payload = null;
    }

    throw new ApiError({
      status: payload?.status ?? response.status,
      code: payload?.code ?? "http_error",
      detail: payload?.detail ?? `Error HTTP ${response.status}.`,
      errors: payload?.errors ?? null,
    });
  }

  return (await response.json()) as T;
}

export const apiClient = {
  login(email: string, password: string): Promise<TokenResponse> {
    return request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  getMe(token: string): Promise<ClientProfile> {
    return request<ClientProfile>("/auth/me", { token });
  },

  listReservations(token: string): Promise<Reservation[]> {
    return request<Reservation[]>("/reservations/", { token });
  },

  cancelReservation(
    token: string,
    reservationId: string,
    reason: string,
  ): Promise<Reservation> {
    return request<Reservation>(`/reservations/${reservationId}/cancel`, {
      method: "POST",
      token,
      body: JSON.stringify({ reason }),
    });
  },
};
