export type ReservationStatus =
  | "requested"
  | "confirmed"
  | "on_hold"
  | "cancelled";

export interface Reservation {
  id: string;
  room_name: string;
  status: ReservationStatus;
  starts_at: string;
  ends_at: string;
  cancel_reason: string | null;
}

export interface ClientProfile {
  id: string;
  email: string;
  display_name: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail: string;
  code: string;
  instance: string;
  errors?: Array<Record<string, unknown>> | null;
}
