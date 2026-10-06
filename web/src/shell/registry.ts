/**
 * web/src/features/<기능>/index.tsx 를 자동으로 모은다(공유 파일 수정 없이 기능 추가).
 *
 * 기능마다 따로 불러온다(동적 import + Promise.allSettled, main.tsx 가 처음 그리기 전에 `loadFeatures()` 를 기다린다).
 * 기능 하나가 import 오류(없는 파일 · 문법 오류 · 모듈 실행 오류 · 빈 모듈)로 깨져도 나머지 기능 · 사이드바 · 홈(셸 카탈로그)은 그대로 뜨고,
 * 그 기능 경로만 「이 기능을 불러오지 못했어요」(App.tsx `FeatureLoadFailed`). 화면을 그리다 난 오류는 기능 경로마다 오류 경계(`FeatureError`).
 */
import type { FeatureModule } from './types';

const loaders = import.meta.glob<{ default?: FeatureModule | null }>('../features/*/index.tsx');

export interface FeatureLoadFailure {
  /** 기능 폴더 이름(= 셸 카탈로그 key) */
  key: string;
  path: string;
  error: unknown;
}

/** 불러온 기능 모듈(order 순). `loadFeatures()` 가 채운다 — 같은 배열을 계속 쓴다. */
export const features: FeatureModule[] = [];
/** 불러오지 못한 기능 */
export const failedFeatures: FeatureLoadFailure[] = [];

let version = 0;
/** 기능 목록이 바뀔 때마다 오르는 번호(셸 카탈로그 캐시용) */
export const registryVersion = () => version;

const keyOfPath = (p: string) => p.split('/').slice(-2)[0] ?? p;

function isFeatureModule(m: unknown): m is FeatureModule {
  const f = m as Partial<FeatureModule> | null | undefined;
  return !!f && typeof f === 'object' && typeof f.key === 'string' && typeof f.code === 'string' && Array.isArray(f.routes);
}

let loading: Promise<void> | null = null;

/** 기능 모듈을 모두 불러온다(실패한 기능은 failedFeatures 로). 여러 번 불러도 한 번만 돈다. 거부하지 않는다. */
export function loadFeatures(): Promise<void> {
  if (!loading) {
    loading = (async () => {
      const entries = Object.entries(loaders);
      const results = await Promise.allSettled(entries.map(([, load]) => load()));
      const ok: FeatureModule[] = [];
      const bad: FeatureLoadFailure[] = [];
      results.forEach((r, i) => {
        const path = entries[i][0];
        const key = keyOfPath(path);
        const mod = r.status === 'fulfilled' ? r.value?.default : undefined;
        if (r.status === 'fulfilled' && isFeatureModule(mod)) {
          ok.push(mod);
          return;
        }
        const error = r.status === 'rejected' ? r.reason : new Error('기능 모듈이 비어 있거나 형식이 맞지 않습니다(export default feature({...}))');
        bad.push({ key, path, error });
        console.error(`[winmate] 기능 '${key}' 를 불러오지 못했습니다 — 나머지 기능은 그대로 씁니다.`, error);
      });
      features.splice(0, features.length, ...ok.sort((a, b) => a.order - b.order));
      failedFeatures.splice(0, failedFeatures.length, ...bad.filter((b) => !ok.some((m) => m.key === b.key)));
      version += 1;
    })();
  }
  return loading;
}

export const featureByKey = (key: string) => features.find((f) => f.key === key);
export const featureByCode = (code: string) => features.find((f) => f.code === code);
/** 불러오지 못한 기능이면 그 실패 */
export const featureLoadFailure = (key?: string | null) => failedFeatures.find((f) => f.key === key);
