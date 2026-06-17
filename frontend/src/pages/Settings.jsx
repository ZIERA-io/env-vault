import { useState } from "react";
import api, { errMsg } from "../api/client.js";
import { useToast } from "../components/Toast.jsx";
import { useAuth } from "../hooks/useAuth.jsx";
import { useTheme } from "../hooks/useTheme.jsx";
import Icon from "../components/Icon.jsx";
import LanguageSwitcher from "../components/LanguageSwitcher.jsx";
import { useI18n } from "../i18n.jsx";
import {
  notificationStatus,
  requestNotificationPermission,
} from "../notify.js";

function Section({ title, desc, children }) {
  return (
    <div className="card p-5">
      <h2 className="text-lg font-semibold">{title}</h2>
      {desc && <p className="mb-4 mt-1 text-sm text-slate-500">{desc}</p>}
      {children}
    </div>
  );
}

export default function Settings() {
  const toast = useToast();
  const { t } = useI18n();
  const { status, refreshStatus } = useAuth();
  const { theme, toggle } = useTheme();

  const [pw, setPw] = useState({ current_password: "", new_password: "" });
  const [mpw, setMpw] = useState({
    current_master_password: "",
    new_master_password: "",
  });
  const [busy, setBusy] = useState(false);
  const [notif, setNotif] = useState(notificationStatus());

  const enableNotif = async () => {
    const r = await requestNotificationPermission();
    setNotif(notificationStatus());
    if (r === "granted") toast.success(t("set.notifEnabled"));
    else if (r === "denied") toast.error(t("set.notifDenied"));
    else if (r === "unsupported") toast.error(t("set.notifUnsupported"));
  };

  const changePw = async () => {
    setBusy(true);
    try {
      await api.post("/auth/change-password", pw);
      toast.success(t("set.pwChanged"));
      setPw({ current_password: "", new_password: "" });
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  const changeMpw = async () => {
    if (!window.confirm(t("set.masterConfirm"))) return;
    setBusy(true);
    try {
      await api.post("/auth/change-master-password", mpw);
      toast.success(t("set.masterChanged"));
      setMpw({ current_master_password: "", new_master_password: "" });
      refreshStatus();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-2xl space-y-5">
      <h1 className="text-2xl font-bold">{t("set.title")}</h1>

      <Section title={t("set.langSection")} desc={t("set.langDesc")}>
        <LanguageSwitcher />
      </Section>

      <Section title={t("set.themeSection")}>
        <button className="btn-outline gap-1.5" onClick={toggle}>
          <Icon name={theme === "dark" ? "sun" : "moon"} size={16} />
          {theme === "dark" ? t("theme.light") : t("theme.dark")}
        </button>
      </Section>

      <Section title={t("set.notifSection")} desc={t("set.notifDesc")}>
        {notif === "granted" ? (
          <span className="inline-flex items-center gap-1.5 text-sm text-emerald-600 dark:text-emerald-400">
            <Icon name="check" size={16} /> {t("set.notifOn")}
          </span>
        ) : notif === "denied" ? (
          <span className="inline-flex items-center gap-1.5 text-sm text-red-600 dark:text-red-400">
            <Icon name="alert" size={16} /> {t("set.notifBlocked")}
          </span>
        ) : notif === "unsupported" ? (
          <span className="text-sm text-slate-500">
            {t("set.notifUnsupported")}
          </span>
        ) : (
          <button className="btn-outline gap-1.5" onClick={enableNotif}>
            <Icon name="alarm" size={16} /> {t("set.enableNotif")}
          </button>
        )}
      </Section>

      <Section title={t("set.sessionSection")}>
        <dl className="space-y-1 text-sm">
          <div className="flex justify-between">
            <dt className="text-slate-500">{t("set.vaultUnlocked")}</dt>
            <dd>{status?.vault_unlocked ? t("set.yes") : t("set.no")}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-500">{t("set.autoLock")}</dt>
            <dd>
              {status?.timeout_minutes != null
                ? t("set.minutes", { n: status.timeout_minutes })
                : "—"}
            </dd>
          </div>
          {status?.idle_seconds != null && (
            <div className="flex justify-between">
              <dt className="text-slate-500">{t("set.idle")}</dt>
              <dd>{t("set.seconds", { n: Math.round(status.idle_seconds) })}</dd>
            </div>
          )}
        </dl>
      </Section>

      <Section title={t("set.changePwSection")} desc={t("set.changePwDesc")}>
        <div className="space-y-3">
          <div>
            <label className="label">{t("set.currentPw")}</label>
            <input
              type="password"
              className="input"
              value={pw.current_password}
              onChange={(e) =>
                setPw({ ...pw, current_password: e.target.value })
              }
            />
          </div>
          <div>
            <label className="label">{t("set.newPw")}</label>
            <input
              type="password"
              className="input"
              value={pw.new_password}
              onChange={(e) => setPw({ ...pw, new_password: e.target.value })}
            />
          </div>
          <button
            className="btn-primary"
            onClick={changePw}
            disabled={busy || pw.new_password.length < 8}
          >
            {t("set.changeBtn")}
          </button>
        </div>
      </Section>

      <Section
        title={t("set.changeMasterSection")}
        desc={
          <span className="inline-flex items-start gap-1 text-amber-600 dark:text-amber-400">
            <Icon name="alert" size={14} className="mt-0.5" />
            {t("set.changeMasterDesc")}
          </span>
        }
      >
        <div className="space-y-3">
          <div>
            <label className="label">{t("set.currentMaster")}</label>
            <input
              type="password"
              className="input"
              value={mpw.current_master_password}
              onChange={(e) =>
                setMpw({ ...mpw, current_master_password: e.target.value })
              }
            />
          </div>
          <div>
            <label className="label">{t("set.newMaster")}</label>
            <input
              type="password"
              className="input"
              value={mpw.new_master_password}
              onChange={(e) =>
                setMpw({ ...mpw, new_master_password: e.target.value })
              }
            />
          </div>
          <button
            className="btn-danger"
            onClick={changeMpw}
            disabled={busy || mpw.new_master_password.length < 8}
          >
            {t("set.changeMasterBtn")}
          </button>
        </div>
      </Section>
    </div>
  );
}
