import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errMsg } from "../api/client.js";
import { useToast } from "../components/Toast.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import ServiceIcon from "../components/ServiceIcon.jsx";
import Icon from "../components/Icon.jsx";
import { notifyExpiring } from "../notify.js";
import { useI18n } from "../i18n.jsx";

function StatCard({ label, value, hint, accent }) {
  return (
    <div className="card p-5">
      <div className="text-sm text-slate-500">{label}</div>
      <div className={`mt-1 text-3xl font-bold ${accent || ""}`}>{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-400">{hint}</div>}
    </div>
  );
}

function daysUntil(iso) {
  if (!iso) return null;
  const ms = new Date(iso).getTime() - Date.now();
  return Math.ceil(ms / 86400000);
}

export default function Dashboard() {
  const toast = useToast();
  const { t } = useI18n();
  const [keys, setKeys] = useState([]);
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [k, f] = await Promise.all([
          api.get("/keys"),
          api.get("/envfiles"),
        ]);
        setKeys(k.data);
        setFiles(f.data);
      } catch (e) {
        toast.error(errMsg(e));
      } finally {
        setLoading(false);
      }
    })();
  }, [toast]);

  const ok = keys.filter((k) => k.last_test_status === "ok").length;
  const err = keys.filter((k) => k.last_test_status === "error").length;
  const untested = keys.filter((k) => k.last_test_status === "untested").length;
  const expiring = keys
    .map((k) => ({ ...k, d: daysUntil(k.expires_at) }))
    .filter((k) => k.d !== null && k.d <= 30)
    .sort((a, b) => a.d - b.d);

  // 7일 이내 만료 키는 브라우저 알림 (권한 있을 때, 세션당 1회)
  useEffect(() => {
    if (loading) return;
    const d7 = expiring.filter((k) => k.d <= 7);
    if (d7.length && !sessionStorage.getItem("env_vault_expiry_notified")) {
      notifyExpiring(d7);
      sessionStorage.setItem("env_vault_expiry_notified", "1");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, keys]);

  if (loading) return <div className="text-slate-400">{t("common.loading")}</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t("dash.title")}</h1>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label={t("dash.totalKeys")}
          value={keys.length}
          hint={t("dash.envFilesCount", { n: files.length })}
        />
        <StatCard label={t("dash.ok")} value={ok} accent="text-emerald-600" />
        <StatCard label={t("dash.error")} value={err} accent="text-red-600" />
        <StatCard label={t("dash.untested")} value={untested} accent="text-slate-500" />
      </div>

      {expiring.length > 0 && (
        <div className="card p-5">
          <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
            <Icon name="alarm" size={18} className="text-amber-500" />{" "}
            {t("dash.expiringTitle")}
          </h2>
          <ul className="space-y-2">
            {expiring.map((k) => (
              <li
                key={k.id}
                className="flex items-center justify-between rounded-lg bg-amber-50 px-3 py-2 text-sm dark:bg-amber-900/20"
              >
                <span className="flex items-center gap-2">
                  <ServiceIcon service={k.service} size={24} />
                  {k.name}
                </span>
                <span
                  className={`font-medium ${k.d <= 7 ? "text-red-600" : "text-amber-600"}`}
                >
                  {k.d <= 0 ? t("dash.expired") : t("dash.dminus", { n: k.d })}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="card p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{t("dash.recentKeys")}</h2>
          <Link to="/keys" className="text-sm text-brand-600 hover:underline">
            {t("dash.viewAll")}
          </Link>
        </div>
        {keys.length === 0 ? (
          <p className="py-6 text-center text-sm text-slate-500">
            {t("dash.noKeys")}{" "}
            <Link to="/keys" className="text-brand-600 hover:underline">
              {t("dash.noKeysAdd")}
            </Link>
          </p>
        ) : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {keys.slice(0, 5).map((k) => (
              <li key={k.id} className="flex items-center justify-between py-2.5">
                <span className="flex items-center gap-3">
                  <ServiceIcon service={k.service} size={28} />
                  <span>
                    <span className="font-medium">{k.name}</span>
                    <span className="ml-2 text-xs text-slate-400">
                      {k.service}
                    </span>
                  </span>
                </span>
                <StatusBadge status={k.last_test_status} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
