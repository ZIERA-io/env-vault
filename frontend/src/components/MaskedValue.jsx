import { useEffect, useRef, useState } from "react";
import { useToast } from "./Toast.jsx";
import { errMsg } from "../api/client.js";
import Icon from "./Icon.jsx";
import { useI18n } from "../i18n.jsx";

// 마스킹 토글 + 클립보드 복사(30초 후 자동 초기화)
// getValue: async () => plaintext  (값은 필요 시점에만 서버에서 복호화 요청)
export default function MaskedValue({ getValue, className = "" }) {
  const toast = useToast();
  const { t } = useI18n();
  const [value, setValue] = useState(null);
  const [revealed, setRevealed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [copyLeft, setCopyLeft] = useState(0);
  const timerRef = useRef(null);

  useEffect(() => () => clearInterval(timerRef.current), []);

  const ensureValue = async () => {
    if (value !== null) return value;
    setLoading(true);
    try {
      const v = await getValue();
      setValue(v);
      return v;
    } catch (e) {
      toast.error(errMsg(e, t("mv.loadFail")));
      throw e;
    } finally {
      setLoading(false);
    }
  };

  const toggleReveal = async () => {
    if (revealed) {
      setRevealed(false);
      return;
    }
    try {
      await ensureValue();
      setRevealed(true);
    } catch {
      /* handled */
    }
  };

  const copy = async () => {
    try {
      const v = await ensureValue();
      await navigator.clipboard.writeText(v);
      toast.success(t("mv.copied"));
      setCopyLeft(30);
      clearInterval(timerRef.current);
      timerRef.current = setInterval(() => {
        setCopyLeft((s) => {
          if (s <= 1) {
            clearInterval(timerRef.current);
            navigator.clipboard.writeText("").catch(() => {});
            return 0;
          }
          return s - 1;
        });
      }, 1000);
    } catch {
      /* handled */
    }
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <code className="min-w-0 flex-1 truncate rounded bg-slate-100 px-2 py-1 font-mono text-xs text-slate-800 dark:bg-slate-800 dark:text-slate-200">
        {revealed && value !== null ? value : "•".repeat(20)}
      </code>
      <button
        type="button"
        onClick={toggleReveal}
        disabled={loading}
        className="btn-ghost gap-1 px-2 py-1 text-xs"
        title={revealed ? "숨기기" : "보기"}
      >
        {loading ? (
          "…"
        ) : (
          <>
            <Icon name={revealed ? "eyeOff" : "eye"} size={14} />
            {revealed ? t("mv.hide") : t("mv.show")}
          </>
        )}
      </button>
      <button
        type="button"
        onClick={copy}
        className="btn-outline gap-1 px-2 py-1 text-xs"
        title="복사 (30초 후 자동 초기화)"
      >
        <Icon name="clipboard" size={14} />
        {copyLeft > 0 ? `${copyLeft}s` : t("mv.copy")}
      </button>
    </div>
  );
}
