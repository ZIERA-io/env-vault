import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useTheme } from "../hooks/useTheme.jsx";
import { useAuth } from "../hooks/useAuth.jsx";
import { useVault } from "../hooks/useVault.js";
import { useI18n } from "../i18n.jsx";
import Icon from "./Icon.jsx";
import LanguageSwitcher from "./LanguageSwitcher.jsx";

const NAV = [
  { to: "/", key: "nav.dashboard", icon: "home", end: true },
  { to: "/keys", key: "nav.apiKeys", icon: "key" },
  { to: "/envfiles", key: "nav.envFiles", icon: "file" },
  { to: "/settings", key: "nav.settings", icon: "settings" },
];

function VaultLockedOverlay({ onRelogin }) {
  const { t } = useI18n();
  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="card max-w-sm p-6 text-center">
        <div className="mb-3 flex justify-center text-slate-400">
          <Icon name="lock" size={44} strokeWidth={1.5} />
        </div>
        <h3 className="mb-1 text-lg font-semibold text-slate-900 dark:text-slate-100">
          {t("vault.lockedTitle")}
        </h3>
        <p className="mb-4 text-sm text-slate-500">{t("vault.lockedDesc")}</p>
        <button className="btn-primary w-full" onClick={onRelogin}>
          {t("vault.relogin")}
        </button>
      </div>
    </div>
  );
}

export default function Layout() {
  const { theme, toggle } = useTheme();
  const { logout } = useAuth();
  const { vault } = useVault();
  const { t } = useI18n();
  const navigate = useNavigate();

  const locked = vault && vault.initialized && !vault.vault_unlocked;

  return (
    <div className="flex h-full min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      {/* 사이드바 */}
      <aside className="flex w-60 shrink-0 flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center gap-2 px-5 py-5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white">
            <Icon name="lock" size={20} />
          </span>
          <div>
            <div className="text-base font-bold">ENV Vault</div>
            <div className="text-xs text-slate-400">{t("app.tagline")}</div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 px-3">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-brand-50 text-brand-700 dark:bg-brand-600/15 dark:text-brand-400"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                }`
              }
            >
              <Icon name={n.icon} size={18} />
              {t(n.key)}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-200 px-3 py-3 dark:border-slate-800">
          <div className="flex items-center gap-2 px-2 pb-2 text-xs text-slate-400">
            <span
              className={`h-2 w-2 rounded-full ${
                vault?.vault_unlocked ? "bg-emerald-500" : "bg-red-500"
              }`}
            />
            {vault?.vault_unlocked ? t("vault.unlocked") : t("vault.locked")}
          </div>
          <button onClick={logout} className="btn-ghost w-full justify-start gap-2">
            <Icon name="logout" size={16} /> {t("nav.logout")}
          </button>
        </div>
      </aside>

      {/* 메인 */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-end gap-2 border-b border-slate-200 bg-white px-6 py-3 dark:border-slate-800 dark:bg-slate-900">
          <LanguageSwitcher />
          <button
            onClick={toggle}
            className="btn-ghost gap-1.5 px-2.5"
            title={t("theme.title")}
          >
            <Icon name={theme === "dark" ? "sun" : "moon"} size={16} />
            {theme === "dark" ? t("theme.light") : t("theme.dark")}
          </button>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>

      {locked && (
        <VaultLockedOverlay
          onRelogin={async () => {
            await logout();
            navigate("/login");
          }}
        />
      )}
    </div>
  );
}
