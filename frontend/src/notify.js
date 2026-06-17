// 브라우저 알림 (만료 임박 키) — localhost/HTTPS 는 보안 컨텍스트라 동작
export function notificationSupported() {
  return typeof window !== "undefined" && "Notification" in window;
}

export function notificationStatus() {
  if (!notificationSupported()) return "unsupported";
  return Notification.permission; // "granted" | "denied" | "default"
}

export async function requestNotificationPermission() {
  if (!notificationSupported()) return "unsupported";
  if (Notification.permission === "granted") return "granted";
  return await Notification.requestPermission();
}

// 7일 이내 만료 키 알림 (권한 있을 때만)
export function notifyExpiring(keys) {
  if (!notificationSupported() || Notification.permission !== "granted") return;
  if (!keys?.length) return;
  const names = keys.map((k) => k.name).join(", ");
  new Notification("ENV Vault — 키 만료 임박", {
    body: `7일 이내 만료 예정: ${names}`,
    tag: "env-vault-expiry", // 동일 태그로 중복 알림 누적 방지
  });
}
