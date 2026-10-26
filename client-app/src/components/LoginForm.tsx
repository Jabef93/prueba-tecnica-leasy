import { FormEvent, useState } from "react";
import { ApiError } from "../api/client";

interface LoginFormProps {
  onLogin: (email: string, password: string) => Promise<void>;
}

export function LoginForm({ onLogin }: LoginFormProps) {
  const [email, setEmail] = useState("alice@example.com");
  const [password, setPassword] = useState("demo1234");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onLogin(email.trim(), password);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Ocurrió un error inesperado al iniciar sesión.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="card stack">
        <div>
          <h2 className="card-title">Iniciar sesión</h2>
          <p className="muted">
            Ingresa con tu cuenta de cliente para gestionar tus reservas.
          </p>
        </div>

        {error && (
          <div className="alert alert--error" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="stack">
          <div className="field">
            <label htmlFor="email">
              <strong>Correo electrónico</strong>
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={submitting}
            />
          </div>

          <div className="field">
            <label htmlFor="password">
              <strong>Contraseña</strong>
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={4}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={submitting}
            />
          </div>

          <button
            className="btn btn-primary"
            type="submit"
            disabled={submitting}
          >
            {submitting ? "Ingresando..." : "Ingresar"}
          </button>
        </form>

        <div className="demo-hint">
          <strong>Cuentas demo:</strong>{" "}
          <button
            type="button"
            className="link-btn"
            onClick={() => {
              setEmail("alice@example.com");
              setPassword("demo1234");
            }}
          >
            alice@example.com
          </button>{" "}
          ·{" "}
          <button
            type="button"
            className="link-btn"
            onClick={() => {
              setEmail("bob@example.com");
              setPassword("demo1234");
            }}
          >
            bob@example.com
          </button>{" "}
          (clave: <code>demo1234</code>)
        </div>
      </div>
    </div>
  );
}
