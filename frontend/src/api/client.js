import axios from "axios";

const ACCESS_KEY = "env_vault_access";
const REFRESH_KEY = "env_vault_refresh";

export const tokenStore = {
  get access() {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(access, refresh) {
    localStorage.setItem(ACCESS_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

// 리프레시 실패(재로그인 필요) 시 호출될 콜백 — AuthProvider 가 등록
let onAuthFailure = () => {};
export function setAuthFailureHandler(fn) {
  onAuthFailure = fn;
}

const api = axios.create({ baseURL: "/api", timeout: 30000 });

api.interceptors.request.use((config) => {
  const t = tokenStore.access;
  if (t && !config.skipAuth) {
    config.headers.Authorization = `Bearer ${t}`;
  }
  // 현재 UI 언어를 서버에 전달 → 서버 메시지도 해당 언어로 응답
  config.headers["X-Lang"] = localStorage.getItem("env_vault_lang") || "en";
  return config;
});

let refreshing = null;

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const { config, response } = error;
    // 액세스 토큰 만료(401) → refresh 토큰으로 1회 자동 갱신 후 재시도
    if (response?.status === 401 && config && !config._retry && tokenStore.refresh) {
      config._retry = true;
      try {
        if (!refreshing) {
          refreshing = axios
            .post("/api/auth/refresh", null, {
              headers: {
                Authorization: `Bearer ${tokenStore.refresh}`,
                "X-Lang": localStorage.getItem("env_vault_lang") || "en",
              },
            })
            .then((r) => {
              tokenStore.set(r.data.access_token, r.data.refresh_token);
              return r.data.access_token;
            })
            .finally(() => {
              refreshing = null;
            });
        }
        const newAccess = await refreshing;
        config.headers.Authorization = `Bearer ${newAccess}`;
        return api(config);
      } catch (e) {
        tokenStore.clear();
        onAuthFailure();
        return Promise.reject(e);
      }
    }
    return Promise.reject(error);
  }
);

export function errMsg(e, fallback = "오류가 발생했습니다.") {
  return e?.response?.data?.detail || e?.message || fallback;
}

export default api;
