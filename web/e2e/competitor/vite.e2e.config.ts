/**
 * 경쟁사 e2e 전용 Vite 설정(선택) — 같은 작업 트리에서 다른 기능 세션이 아직 만들지 않은 파일을 import 하면 개발 서버 전체가 깨진다.
 * 이 설정은 다른 기능 폴더(src/features/<x>, x ≠ competitor)의 없는 상대 경로 import 만 빈 컴포넌트로 바꿔 경쟁사 화면 시험을 계속할 수 있게 한다.
 *   cd web && WM_E2E_DEV=1 npx vite --config e2e/competitor/vite.e2e.config.ts --port 5204 --strictPort --host 127.0.0.1
 *   (그 뒤 make e2e-feature SERVICE=competitor 는 떠 있는 서버를 그대로 쓴다)
 */
import fs from 'node:fs';
import path from 'node:path';
import { defineConfig, mergeConfig, type Plugin } from 'vite';
import base from '../../vite.config';

function stubMissing(): Plugin {
  const EXT = ['', '.tsx', '.ts', '.jsx', '.js', '/index.tsx', '/index.ts'];
  return {
    name: 'wm-e2e-stub-missing',
    enforce: 'pre',
    resolveId(source, importer) {
      if (!importer || !source.startsWith('.')) return null;
      const norm = importer.split(path.sep).join('/');
      if (!norm.includes('/src/features/') || norm.includes('/src/features/competitor/')) return null;
      const target = path.resolve(path.dirname(importer), source);
      if (EXT.some((e) => fs.existsSync(target + e))) return null;
      return `\0wm-e2e-stub:${target}`;
    },
    load(id) {
      if (!id.startsWith('\0wm-e2e-stub:')) return null;
      return 'export default function WmE2eStub() { return null; }\n';
    },
  };
}

// 의존성 사전 번들 캐시는 따로 둔다(다른 세션 개발 서버의 node_modules/.vite 를 다시 만들지 않게)
export default mergeConfig(base, defineConfig({ plugins: [stubMissing()], cacheDir: 'node_modules/.vite-e2e-competitor' }));
