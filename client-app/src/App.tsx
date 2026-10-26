import { useCallback, useEffect, useState } from "react";
import { ApiError, apiClient } from "./api/client";
import type { ClientProfile, Reservation } from "./api/types";
import { CancelDialog } from "./components/CancelDialog";
import { LoginForm } from "./components/LoginForm";
import { ReservationList } from "./components/ReservationList";

const TOKEN_STORAGE_KEY = "assessment_client_token";

export function App() {
  const [token, setToken] = useState<string | null>(() =>
    sessionStorage.getItem(TOKEN_STORAGE_KEY),
  );
  const [profile, setProfile] = useState<ClientProfile | null>(null);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [selectedToCancel, setSelectedToCancel] =
    useState<Reservation | null>(null);

  const handleLogout = useCallback((message?: string) => {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setProfile(null);
    setReservations([]);
    setSelectedToCancel(null);
    if (message) {
      setBanner({ type: "error", text: message });
    }
  }, []);

  const loadPortalData = useCallback(
    async (activeToken: string) => {
      setLoading(true);
      try {
        const [meData, listData] = await Promise.all([
          apiClient.getMe(activeToken),
          apiClient.listReservations(activeToken),
        ]);
        setProfile(meData);
        setReservations(listData);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          handleLogout(err.message);
        } else if (err instanceof ApiError) {
          setBanner({ type: "error", text: err.message });
        } else {
          setBanner({
            type: "error",
            text: "No se pudieron cargar tus reservas.",
          });
        }
      } finally {
        setLoading(false);
      }
    },
    [handleLogout],
  );

  useEffect(() => {
    if (token) {
      void loadPortalData(token);
    }
  }, [token, loadPortalData]);

  async function handleLogin(email: string, password: string) {
    setBanner(null);
    const { access_token } = await apiClient.login(email, password);
    sessionStorage.setItem(TOKEN_STORAGE_KEY, access_token);
    setToken(access_token);
  }

  async function handleConfirmCancel(reservationId: string, reason: string) {
    if (!token) return;
    setBanner(null);
    try {
      const updated = await apiClient.cancelReservation(
        token,
        reservationId,
        reason,
      );
      setReservations((prev) =>
        prev.map((item) => (item.id === updated.id ? updated : item)),
      );
      setSelectedToCancel(null);
      setBanner({
        type: "success",
        text: `Reserva en ${updated.room_name} cancelada correctamente.`,
      });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        handleLogout(err.message);
        return;
      }
      throw err;
    }
  }

  return (
    <>
      <header className="app-header">
        <div className="app-header__inner">
          <div className="brand">
            <span className="brand__mark">CP</span>
            <span className="brand__text">
              <span className="brand__title">Portal de Cliente</span>
              <span className="brand__subtitle">
                Gestión y cancelación de reservas
              </span>
            </span>
          </div>
          {token && profile && (
            <div className="header-actions">
              <span className="user-chip">
                {profile.display_name} ({profile.email})
              </span>
              <button
                type="button"
                className="btn"
                onClick={() => handleLogout()}
              >
                Cerrar sesión
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="shell stack">
        {banner && (
          <div
            className={`alert alert--${banner.type}`}
            role="status"
            onClick={() => setBanner(null)}
          >
            {banner.text}
          </div>
        )}

        {!token ? (
          <LoginForm onLogin={handleLogin} />
        ) : (
          <ReservationList
            reservations={reservations}
            loading={loading}
            onRefresh={() => void loadPortalData(token)}
            onRequestCancel={(reservation) => {
              setBanner(null);
              setSelectedToCancel(reservation);
            }}
          />
        )}

        {selectedToCancel && (
          <CancelDialog
            reservation={selectedToCancel}
            onConfirm={handleConfirmCancel}
            onClose={() => setSelectedToCancel(null)}
          />
        )}
      </main>
    </>
  );
}
