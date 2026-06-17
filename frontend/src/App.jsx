import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./hooks/useAuth.jsx";
import Layout from "./components/Layout.jsx";
import Setup from "./pages/Setup.jsx";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import ApiKeys from "./pages/ApiKeys.jsx";
import EnvFiles from "./pages/EnvFiles.jsx";
import Settings from "./pages/Settings.jsx";

function FullLoader() {
  return (
    <div className="flex h-screen items-center justify-center bg-slate-50 dark:bg-slate-950">
      <div className="text-slate-400">불러오는 중…</div>
    </div>
  );
}

function Protected({ children }) {
  const { authed, loading } = useAuth();
  if (loading) return <FullLoader />;
  if (!authed) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const { loading } = useAuth();
  if (loading) return <FullLoader />;

  return (
    <Routes>
      <Route path="/setup" element={<Setup />} />
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/keys" element={<ApiKeys />} />
        <Route path="/envfiles" element={<EnvFiles />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
