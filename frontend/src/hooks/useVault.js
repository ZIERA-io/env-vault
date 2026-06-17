import { useEffect, useState, useCallback } from "react";
import api from "../api/client.js";

// Vault 잠금 상태를 주기적으로 폴링 (자동 잠금 감지)
export function useVault(pollMs = 30000) {
  const [vault, setVault] = useState(null);

  const check = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/status", { skipAuth: true });
      setVault(data);
      return data;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    check();
    const id = setInterval(check, pollMs);
    return () => clearInterval(id);
  }, [check, pollMs]);

  return { vault, check };
}
