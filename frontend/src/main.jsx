import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";
import App from "./App.jsx";
import { AuthProvider } from "./hooks/useAuth.jsx";
import { ThemeProvider } from "./hooks/useTheme.jsx";
import { I18nProvider } from "./i18n.jsx";
import { ToastProvider } from "./components/Toast.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <I18nProvider>
      <ThemeProvider>
        <ToastProvider>
          <HashRouter>
            <AuthProvider>
              <App />
            </AuthProvider>
          </HashRouter>
        </ToastProvider>
      </ThemeProvider>
    </I18nProvider>
  </React.StrictMode>
);
