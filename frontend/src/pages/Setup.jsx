import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.jsx";
import { useToast } from "../components/Toast.jsx";
import { errMsg } from "../api/client.js";
import Icon from "../components/Icon.jsx";
import LanguageSwitcher from "../components/LanguageSwitcher.jsx";
import { useI18n } from "../i18n.jsx";

export default function Setup() {
  const { status, setup, refreshStatus } = useAuth();
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

  // 이미 초기화됨 → 로그인으로
  useEffect(() => {
    if (status?.initialized) navigate("/login", { replace: true });
  }, [status, navigate]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await setup(form);
      toast.success(t("setup.ok"));
      navigate("/", { replace: true });
    } catch (err) {
      toast.error(errMsg(err, t("setup.fail")));
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
            {t("setup.title")}
          </h1>
          <p className="mt-1 text-sm text-slate-500">{t("setup.desc")}</p>
        </div>

        <div className="space-y-4">
          <div>
            <label className="label">{t("setup.username")}</label>
            <input
              className="input"
              value={form.username}
              onChange={set("username")}
              placeholder={t("setup.usernamePlaceholder")}
              autoFocus
            />
          </div>
          <div>
            <label className="label">{t("setup.password")}</label>
            <input
              type="password"
              className="input"
              value={form.password}
              onChange={set("password")}
              placeholder={t("setup.passwordPlaceholder")}
            />
          </div>
          <div>
            <label className="label">{t("setup.master")}</label>
            <input
              type="password"
              className="input"
              value={form.master_password}
              onChange={set("master_password")}
              placeholder={t("setup.masterPlaceholder")}
            />
            <p className="mt-1 flex items-start gap-1 text-xs text-amber-600 dark:text-amber-400">
              <Icon name="alert" size={14} className="mt-0.5" />
              <span>{t("setup.masterWarning")}</span>
            </p>
          </div>
        </div>

        <button type="submit" disabled={busy} className="btn-primary mt-6 w-full">
          {busy ? t("setup.submitting") : t("setup.submit")}
        </button>
      </form>
    </div>
  );
}
