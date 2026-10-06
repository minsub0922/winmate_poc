/**
 * 선 아이콘(viewBox 24×24, stroke, round) — 00-shell §2.7 · 부록 A.
 * 기능·솔루션·상단바 아이콘 path 는 셸(web/src/shell/icons.tsx)에 있고, 여기는 공통 아이콘만 둔다.
 */
import type { CSSProperties } from 'react';

export const ICON_PATHS: Record<string, string> = {
  search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14z M20 20l-4-4',
  x: 'M6 6l12 12 M18 6L6 18',
  check: 'M5 12l5 5L20 7',
  info: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M12 11v5 M12 8h.01',
  upload: 'M12 15V4 M7 9l5-5 5 5 M4 15v5h16v-5',
  download: 'M12 4v11 M7 10l5 5 5-5 M4 15v5h16v-5',
  drop: 'M12 16V4 M6 10l6-6 6 6 M4 20h16',
  plus: 'M12 5v14 M5 12h14',
  minus: 'M5 12h14',
  chevronRight: 'M9 6l6 6-6 6',
  chevronDown: 'M6 9l6 6 6-6',
  chevronLeft: 'M15 6l-6 6 6 6',
  chevronUp: 'M6 15l6-6 6 6',
  external: 'M14 4h6v6 M20 4l-9 9 M18 14v6H4V6h6',
  link: 'M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7 M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7',
  bolt: 'M13 3L5 14h6l-1 7 8-11h-6l1-7z',
  lock: 'M5 11h14v10H5z M8 11V7a4 4 0 0 1 8 0v4',
  edit: 'M4 20h4L19 9l-4-4L4 16v4z',
  trash: 'M4 7h16 M9 7V4h6v3 M6 7l1 13h10l1-13',
  refresh: 'M20 11a8 8 0 1 0-2.3 5.7 M20 4v7h-7',
  file: 'M6 3h8l5 5v13H6z M14 3v5h5',
  image: 'M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z M9 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4z M21 16l-5-5-9 9',
  grip: 'M9 6h.01 M15 6h.01 M9 12h.01 M15 12h.01 M9 18h.01 M15 18h.01',
  more: 'M5 12h.01 M12 12h.01 M19 12h.01',
  copy: 'M9 9h11v11H9z M5 15H4V4h11v1',
  mail: 'M4 6h16v12H4z M4 7l8 6 8-6',
  clock: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M12 7v5l3 2',
  warn: 'M12 3l10 18H2L12 3z M12 10v5 M12 18v.01',
  arrowRight: 'M5 12h14 M13 6l6 6-6 6',
  arrowLeft: 'M19 12H5 M11 6l-6 6 6 6',
  arrowUp: 'M12 19V5 M6 11l6-6 6 6',
  settings: 'M4 7h16 M4 12h16 M4 17h16',
  play: 'M7 4l13 8-13 8z',
  stop: 'M6 6h12v12H6z',
  folder: 'M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M4 21a8 8 0 0 1 16 0',
  send: 'M12 19V5 M6 11l6-6 6 6',
  sparkle: 'M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z',
  undo: 'M9 14L4 9l5-5 M4 9h11a5 5 0 0 1 0 10h-3',
};

export type IconName = keyof typeof ICON_PATHS;

export function Icon({ name, size = 16, color = 'currentColor', strokeWidth = 2, style, title }:
  { name: IconName | string; size?: number; color?: string; strokeWidth?: number; style?: CSSProperties; title?: string }) {
  const d = ICON_PATHS[name] ?? ICON_PATHS.info;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round"
      strokeLinejoin="round" aria-hidden={title ? undefined : true} role={title ? 'img' : undefined} style={{ flexShrink: 0, ...style }}>
      {title && <title>{title}</title>}
      <path d={d} />
    </svg>
  );
}

/** 임의 path 로 그리는 선 아이콘(기능 · 솔루션 아이콘 등). */
export function PathIcon({ d, size = 16, color = 'currentColor', strokeWidth = 2, style }:
  { d: string; size?: number; color?: string; strokeWidth?: number; style?: CSSProperties }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true" style={{ flexShrink: 0, ...style }}>
      <path d={d} />
    </svg>
  );
}

/** 채운 번개(딸깍) */
export function BoltIcon({ size = 14, color = 'var(--wm-brand-on-dark)' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color} aria-hidden="true" style={{ flexShrink: 0 }}>
      <path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z" />
    </svg>
  );
}

/** 6점 그립(끌기 손잡이) — 행 9×13 `#8a91a0` · 머리 안내 `#1428a0` · 타일 8×12 `#596170` */
export function Grip({ color = 'var(--wm-text-subtle)', width = 9, height = 13 }: { color?: string; width?: number; height?: number }) {
  return (
    <svg width={width} height={height} viewBox="0 0 10 14" fill={color} aria-hidden="true" style={{ flexShrink: 0 }}>
      <circle cx="2.5" cy="2.5" r="1.3" /><circle cx="7.5" cy="2.5" r="1.3" /><circle cx="2.5" cy="7" r="1.3" />
      <circle cx="7.5" cy="7" r="1.3" /><circle cx="2.5" cy="11.5" r="1.3" /><circle cx="7.5" cy="11.5" r="1.3" />
    </svg>
  );
}

/** 슬라이더 아이콘(사용자 카드 `설정`) */
export function SlidersIcon({ size = 16, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" aria-hidden="true" style={{ flexShrink: 0 }}>
      <path d="M4 7h16M4 12h16M4 17h16" />
      <circle cx="9" cy="7" r="2" fill="var(--wm-surface)" /><circle cx="15" cy="12" r="2" fill="var(--wm-surface)" /><circle cx="8" cy="17" r="2" fill="var(--wm-surface)" />
    </svg>
  );
}

/** 폴더(제품 트리) — 펼침·활성이면 채움 `#eaeefb` + 선 `#1428a0` */
export function FolderIcon({ open, size = 14 }: { open?: boolean; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={open ? 'var(--wm-brand-50)' : 'none'} stroke={open ? 'var(--wm-brand)' : 'var(--wm-text-muted)'}
      strokeWidth="1.8" strokeLinejoin="round" aria-hidden="true" style={{ flexShrink: 0 }}>
      <path d={ICON_PATHS.folder} />
    </svg>
  );
}
