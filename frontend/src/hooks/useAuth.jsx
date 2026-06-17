import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import { useNavigate } from "react-router-dom";
import api, { tokenStore, setAuthFailureHandler } from "../api/client.js";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const navigate = useNavigate();
  const [authed, setAuthed] = useState(!!tokenStore.access);
  const [status, setStatus] = useState(null); // /auth/status 응답
  const [loading, setLoading] = useState(true);

  const refreshStatus = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/status", { skipAuth: true });
      setStatus(data);
      return data;
    } catch {
      return null;
    }
  }, []);

  // 리프레시 토큰까지 만료되면 로그인 화면으로
  useEffect(() => {
    setAuthFailureHandler(() => {
      setAuthed(false);
      navigate("/login");
    });
  }, [navigate]);

  useEffect(() => {
    (async () => {
      await refreshStatus();
      setLoading(false);
    })();
  }, [refreshStatus]);

  const login = useCallback(
    async (creds) => {
      const { data } = await api.post("/auth/login", creds, { skipAuth: true });
      tokenStore.set(data.access_token, data.refresh_token);
      setAuthed(true);
      await refreshStatus();
    },
    [refreshStatus]
  );

  const setup = useCallback(
    async (creds) => {
      await api.post("/auth/setup", creds, { skipAuth: true });
      await login(creds);
    },
    [login]
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      /* 만료 토큰도 로그아웃 허용 */
    }
    tokenStore.clear();
    setAuthed(false);
    await refreshStatus();
    navigate("/login");
  }, [navigate, refreshStatus]);

  return (
    <AuthContext.Provider
      value={{ authed, status, loading, login, setup, logout, refreshStatus }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
