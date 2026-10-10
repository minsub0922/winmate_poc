/** 기능 · 상단바 · 솔루션 아이콘(00-shell 부록 A). 사이드바·홈·최근 작업·드래그 고스트 공통. */
import type { FeatureCode } from './types';

export const FEATURE_ICON: Record<FeatureCode, string> = {
  RQ: 'M9 4h6v3H9z M7 5.5H5V21h14V5.5h-2 M8.5 12h7 M8.5 16h5',
  SB: 'M4 5h16v14H4z M4 11h16 M10 11v8',
  DS: 'M3 21h18 M5 21V9l7-5 7 5v12 M9 21v-6h6v6',
  IMG: 'M4 5h16v14H4z M9 10.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z M20 15l-5-5-8 8',
  BE: 'M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z M12 12l8-4.5 M12 12v9 M12 12L4 7.5',
  SC: 'M4 6h16v12H4z M10 9l5 3-5 3V9z',
  MI: 'M4 20V10 M10 20V4 M16 20v-8 M22 20H2',
  CA: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10z M12 11a1 1 0 1 0 0 2 1 1 0 0 0 0-2z M21 3l-4 4',
  VP: 'M6 4h12l3 5-9 11L3 9l3-5z M3 9h18 M9.5 9L12 20l2.5-11',
  SP: 'M6 3h8l5 5v13H6V3z M14 3v5h5 M9 13h7 M9 17h7',
  PR: 'M3 4h18v12H3z M8 20h8 M12 16v4 M7 12l3-3 2 2 4-4',
};

export function FeatureIcon({ code, size = 16, color = 'currentColor', strokeWidth = 2 }: { code: FeatureCode | string; size?: number; color?: string; strokeWidth?: number }) {
  const d = FEATURE_ICON[code as FeatureCode] ?? FEATURE_ICON.RQ;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ flexShrink: 0 }}>
      <path d={d} />
    </svg>
  );
}

/** 상단바 버튼 아이콘(15px, 선 `#1428a0` 굵기 2) */
export function TopBarIcon({ kind }: { kind: 'product' | 'solution' | 'image' | 'case' }) {
  const common = { width: 15, height: 15, viewBox: '0 0 24 24', fill: 'none', stroke: 'var(--wm-brand)', strokeWidth: 2, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, 'aria-hidden': true, style: { flexShrink: 0 } };
  if (kind === 'product') {
    return <svg {...common}><rect x="4" y="4" width="7" height="7" rx="1.5" /><rect x="13" y="4" width="7" height="7" rx="1.5" /><rect x="4" y="13" width="7" height="7" rx="1.5" /><rect x="13" y="13" width="7" height="7" rx="1.5" /></svg>;
  }
  if (kind === 'solution') return <svg {...common}><path d="M12 3l9 5-9 5-9-5 9-5z" /><path d="M3 13l9 5 9-5" /></svg>;
  if (kind === 'image') return <svg {...common}><rect x="3" y="4" width="18" height="16" rx="2" /><circle cx="9" cy="10" r="2" /><path d="M21 16l-5-5-9 9" /></svg>;
  return <svg {...common}><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" /><path d="M9 14h6" /></svg>;
}

/** 솔루션 아이콘(16px) — 카탈로그 id 기준 */
export const SOLUTION_ICON: Record<string, string> = {
  magicinfo: 'M3 4h18v12H3z M8 20h8',
  vxt: 'M4 16a4 4 0 0 1 1-7.9A6 6 0 0 1 17 8a4 4 0 0 1 1 8H4z',
  smartthings_pro: 'M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z M12 2v3 M12 19v3 M2 12h3 M19 12h3',
  biot: 'M4 21V3h10v18 M14 9h6v12 M8 7h2 M8 11h2 M8 15h2',
  lynk_cloud: 'M3 5h18v14H3z M3 10h18',
  knox_suite: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z',
  knox_capture: 'M4 6v12 M7 6v12 M10 6v12 M14 6v12 M17 6v12 M20 6v12',
  dex: 'M3 5h14v10H3z M7 19h6 M19 9h2v10h-2z',
  cold_chain: 'M12 2v20 M4.9 7l14.2 10 M4.9 17L19.1 7',
  hvac_integrated: 'M3 8h12a3 3 0 1 0-3-3 M3 12h16a3 3 0 1 1-3 3 M3 16h8',
  sac_control: 'M4 6h16 M4 12h16 M4 18h16 M9 4v4 M15 10v4 M7 16v4',
};
export const SOLUTION_ICON_FALLBACK = 'M12 3l9 5-9 5-9-5 9-5z M3 13l9 5 9-5';

/** 솔루션 아이콘 path: 카탈로그 id → API 가 준 path(M 으로 시작) → 기본 */
export function solutionIconPath(id?: string | null, apiIcon?: string | null) {
  if (id && SOLUTION_ICON[id]) return SOLUTION_ICON[id];
  if (apiIcon && /^M[\d\s.,-]/.test(apiIcon)) return apiIcon;
  return SOLUTION_ICON_FALLBACK;
}
