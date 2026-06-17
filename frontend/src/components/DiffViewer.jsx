import { useI18n } from "../i18n.jsx";

const STATUS = {
  added: { key: "diff.added", cls: "text-emerald-600 dark:text-emerald-400" },
  removed: { key: "diff.removed", cls: "text-red-600 dark:text-red-400" },
  changed: { key: "diff.changed", cls: "text-amber-600 dark:text-amber-400" },
  unchanged: { key: "diff.unchanged", cls: "text-slate-400" },
};

// items: [{key, old_value(마스킹), new_value(마스킹), status}]
export default function DiffViewer({ items }) {
  const { t } = useI18n();
  if (!items?.length) {
    return (
      <p className="py-6 text-center text-sm text-slate-500">{t("diff.noItems")}</p>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs uppercase text-slate-500 dark:border-slate-700">
            <th className="px-3 py-2">{t("diff.status")}</th>
            <th className="px-3 py-2">{t("diff.key")}</th>
            <th className="px-3 py-2">{t("diff.snapValue")}</th>
            <th className="px-3 py-2">{t("diff.curValue")}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => {
            const s = STATUS[it.status] || STATUS.unchanged;
            return (
              <tr
                key={it.key}
                className="border-b border-slate-100 dark:border-slate-800"
              >
                <td className={`px-3 py-2 font-medium ${s.cls}`}>{t(s.key)}</td>
                <td className="px-3 py-2 font-mono text-xs">{it.key}</td>
                <td className="px-3 py-2 font-mono text-xs text-slate-500">
                  {it.old_value ?? "—"}
                </td>
                <td className="px-3 py-2 font-mono text-xs text-slate-500">
                  {it.new_value ?? "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
