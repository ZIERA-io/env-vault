import { useI18n } from "../i18n.jsx";

const MAP = {
  ok: { key: "status.ok", cls: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300", dot: "bg-emerald-500" },
  error: { key: "status.error", cls: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300", dot: "bg-red-500" },
  untested: { key: "status.untested", cls: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400", dot: "bg-slate-400" },
};

export default function StatusBadge({ status }) {
  const { t } = useI18n();
  const s = MAP[status] || MAP.untested;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${s.cls}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {t(s.key)}
    </span>
  );
}
