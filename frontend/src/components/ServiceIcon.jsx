// 서비스 실제 로고 (로컬 번들 — 외부 CDN 미사용으로 키 사용 서비스 노출 방지)
import { SERVICE_LOGOS } from "./serviceLogos.js";
import { SERVICE_META } from "../services.js";

export default function ServiceIcon({ service, size = 32 }) {
  const svc = service?.toLowerCase();
  const logo = SERVICE_LOGOS[svc];
  const label = SERVICE_META[svc]?.label || service || "기타";

  // 알려진 서비스: 브랜드 색 배경 + 흰색 로고
  if (logo) {
    return (
      <span
        title={label}
        className="inline-flex shrink-0 items-center justify-center rounded-lg"
        style={{ width: size, height: size, background: logo.hex }}
      >
        <svg
          role="img"
          width={size * 0.58}
          height={size * 0.58}
          viewBox="0 0 24 24"
          fill="#ffffff"
          aria-hidden="true"
        >
          <path d={logo.path} />
        </svg>
      </span>
    );
  }

  // 미지원 서비스: 이니셜 배지 폴백
  return (
    <span
      title={label}
      className="inline-flex shrink-0 items-center justify-center rounded-lg bg-slate-500 font-semibold text-white"
      style={{ width: size, height: size, fontSize: size * 0.36 }}
    >
      {(service || "?").slice(0, 2).toUpperCase()}
    </span>
  );
}

// 하위 호환: 기존 import 유지
export { SERVICE_LIST } from "../services.js";
