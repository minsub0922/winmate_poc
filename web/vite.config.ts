import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

// 개발 서버(5001)는 /api 를 게이트웨이(5000)로 넘긴다. 운영은 게이트웨이가 dist 를 서빙한다.
// e2e 용 개발 서버(WM_E2E_DEV=1, make e2e-feature)는 HMR · 파일 감시를 끈다 — 같은 작업 트리에서 다른 세션이 파일을 저장해도
// 시험 중인 화면이 다시 그려지지 않게.
const e2e = !!process.env.WM_E2E_DEV;

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    port: 5001,
    strictPort: true,
    host: '127.0.0.1',
    proxy: { '/api': { target: 'http://127.0.0.1:5000', changeOrigin: false, ws: false } },
    ...(e2e ? { hmr: false, watch: null } : {}),
  },
  preview: { port: 5001, strictPort: true },
  build: { outDir: 'dist', sourcemap: true, chunkSizeWarningLimit: 1500 },
});
