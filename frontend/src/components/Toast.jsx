import { createContext, useContext, useState, useCallback } from "react";

const ToastContext = createContext();

const STYLES = {
  info: "bg-slate-800 text-white dark:bg-slate-700",
  success: "bg-emerald-600 text-white",
  error: "bg-red-600 text-white",
};

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const push = useCallback((message, type = "info") => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setToasts((t) => [...t, { id, message, type }]);
    setTimeout(
      () => setToasts((t) => t.filter((x) => x.id !== id)),
      3500
    );
  }, []);

  const toast = {
    info: (m) => push(m, "info"),
    success: (m) => push(m, "success"),
    error: (m) => push(m, "error"),
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto max-w-sm rounded-lg px-4 py-2.5 text-sm shadow-lg ${STYLES[t.type]}`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
