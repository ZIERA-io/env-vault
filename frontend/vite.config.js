import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 프로덕션: FastAPI 가 frontend/dist 를 동일 출처(8443)에서 서빙 → '/api' 상대경로
// 개발(5173): /api 요청을 로컬 HTTPS 백엔드로 프록시 (자체서명 인증서 → secure:false)
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "https://127.0.0.1:8443",
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
