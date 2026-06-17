import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.jsx";
import { useToast } from "../components/Toast.jsx";
import { errMsg } from "../api/client.js";
import Icon from "../components/Icon.jsx";
import LanguageSwitcher from "../components/LanguageSwitcher.jsx";
import { useI18n } from "../i18n.jsx";

export default function Login() {
  const { status, login, refreshStatus } = useAuth();
  const toast = useToast();
  const { t } = useI18n();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    username: "",
    password: "",
    master_password: "",
  });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  // 미초기화 → 최초 설정으로
  useEffect(() => {
    if (status && status.initialized === false) {
      navigate("/setup", { replace: true });
    }
  }, [status, navigate]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await login(form);
      toast.success(t("login.ok"));
      navigate("/", { replace: true });
    } catch (err) {
      toast.error(errMsg(err, t("login.fail")));
    } finally {
      setBusy(false);
    }
  };

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4 dark:bg-slate-950">
      <div className="absolute right-4 top-4">
        <LanguageSwitcher />
      </div>
      <form onSubmit={submit} className="card w-full max-w-md p-8">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-2 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600 text-white">
            <Icon name="lock" size={28} />
          </div>
          <h1 className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-100">
            {t("login.title")}
          </h1>
          <p className="mt-1 text-sm text-slate-500">{t("login.desc")}</p>
        </div>

        <div className="space-y-4">
          <div>
            <label className="label">{t("login.username")}</label>
            <input
              className="input"
              value={form.username}
              onChange={set("username")}
              autoFocus
            />
          </div>
          <div>
            <label className="label">{t("login.password")}</label>
            <input
              type="password"
              className="input"
              value={form.password}
              onChange={set("password")}
            />
          </div>
          <div>
            <label className="label">{t("login.master")}</label>
            <input
              type="password"
              className="input"
              value={form.master_password}
              onChange={set("master_password")}
            />
          </div>
        </div>

        <button type="submit" disabled={busy} className="btn-primary mt-6 w-full">
          {busy ? t("login.submitting") : t("login.submit")}
        </button>
      </form>
    </div>
  );
}
