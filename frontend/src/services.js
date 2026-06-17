// 서비스 메타데이터 + API 키 값으로 서비스 자동 감지
// (백엔드 test_router.SERVICES 의 감지 규칙과 동일하게 유지)
import { SERVICE_LOGOS } from "./components/serviceLogos.js";

export const SERVICE_META = {
  openai: { label: "OpenAI" },
  anthropic: { label: "Anthropic" },
  github: { label: "GitHub" },
  google: { label: "Google AI" },
  stripe: { label: "Stripe" },
  aws: { label: "AWS" },
};

export const SERVICE_LIST = Object.entries(SERVICE_META).map(([service, m]) => ({
  service,
  label: m.label,
}));

// 키 값(평문)으로 서비스 추론 — 못 찾으면 null
export function detectService(value) {
  const k = (value || "").trim();
  if (!k) return null;
  if (k.startsWith("sk-ant-")) return "anthropic";
  if (k.startsWith("sk-")) return "openai";
  if (
    k.startsWith("ghp_") ||
    k.startsWith("github_pat_") ||
    k.startsWith("gho_") ||
    k.startsWith("ghu_")
  )
    return "github";
  if (k.startsWith("AIza") && k.length === 39) return "google";
  if (
    k.startsWith("sk_live_") ||
    k.startsWith("sk_test_") ||
    k.startsWith("rk_live_") ||
    k.startsWith("rk_test_")
  )
    return "stripe";
  if (k.startsWith("AKIA") && k.length === 20) return "aws";
  return null;
}

export function logoFor(service) {
  return SERVICE_LOGOS[service?.toLowerCase()] || null;
}
