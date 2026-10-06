/**
 * 조감도 화면 공용 부품 — 보드 틀(§화면 원칙): W 말풍선 1개 + 사용자 메아리 + 하단 작업 카드 1장.
 * 색 · 그림자는 var(--wm-*) 토큰만(be.css).
 */
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link } from 'react-router';
import { useShellPage } from '@/shell/ShellContext';
import type { ShellPageConfig } from '@/shell/types';
import { Icon, Spinner, cx } from '@/ui';
import type { Birdseye } from './api';

export const SECTION = '공간 조감도 생성';
export const STEPS = ['공간 입력', '배치될 제품', '가구 추천', '배치 · 인테리어 컨펌', '3D 조감도 생성'];

/** 화면마다 셸에 맥락을 넘긴다(상단바 · 스텝바). */
export function useBeShell(b: Birdseye | undefined | null, step: number, extra: Partial<ShellPageConfig> = {}, complete = false) {
  useShellPage({
    section: SECTION,
    title: b?.title ?? '새 작업',
    hasTask: true,
    sidebarGroup: 'birdseye',
    stepper: { steps: STEPS, current: step, complete },
    ...extra,
  });
}

/** 본문(가운데 800 열, 스크롤) + 하단 작업 카드 */
export function BePage({ children, dock, width = 800, testId }: { children: ReactNode; dock?: ReactNode; width?: number; testId?: string }) {
  return (
    <div className="be-page" data-testid={testId}>
      <div className="be-scroll">
        <div className="be-col" style={{ width }}>{children}</div>
      </div>
      {dock}
    </div>
  );
}

/** W 말풍선(로고 + 글 + 아래 부품) */
export function Agent({ text, sub, children, busy }: { text?: ReactNode; sub?: ReactNode; children?: ReactNode; busy?: boolean }) {
  return (
    <div className="be-agent">
      <div className="be-agent__logo" aria-hidden="true">W</div>
      <div className="be-agent__body">
        {text && <div className="be-agent__text" data-testid="be-w">{busy && <Spinner label="진행 중" />} {text}</div>}
        {sub && <div className="be-agent__sub">{sub}</div>}
        {children}
      </div>
    </div>
  );
}

/** 사용자 입력 메아리(오른쪽 말풍선 + 첨부 파일 칩) */
export function Echo({ text, files }: { text?: ReactNode; files?: Array<{ name: string; to?: string | null }> }) {
  if (!text && !files?.length) return null;
  return (
    <div className="be-echo">
      <div className="be-echo__inner">
        {text && <div className="be-echo__bubble" data-testid="be-echo">{text}</div>}
        {files?.map((f, i) => (
          f.to
            ? <Link key={i} to={f.to} className="be-file-chip"><Icon name="file" size={14} />{f.name}</Link>
            : <span key={i} className="be-file-chip"><Icon name="file" size={14} />{f.name}</span>
        ))}
      </div>
    </div>
  );
}

/** 요약 칩(BE2 「120평 · 층고 4.5m」 · BE1P 추정 칩) */
export function InfoChips({ items, testId }: { items: Array<{ label: string; estimated?: boolean } | string>; testId?: string }) {
  if (!items.length) return null;
  return (
    <div className="be-infochips" data-testid={testId}>
      {items.map((c, i) => {
        const label = typeof c === 'string' ? c : c.label;
        return <span key={i} className="be-infochip">{label}</span>;
      })}
    </div>
  );
}

/** 하단 작업 카드 — 머리 「{제목} · {메타}」 + 오른쪽 링크 + 몸통 + 아래 줄 */
export function Dock({ title, meta, right, children, foot, testId }: {
  title: ReactNode; meta?: ReactNode; right?: ReactNode; children?: ReactNode; foot?: ReactNode; testId?: string;
}) {
  return (
    <div className="be-dock-wrap">
      <div className="be-dock" role="region" aria-label="작업 카드" data-testid={testId ?? 'be-dock'}>
        <div className="be-dock__head">
          <div className="be-dock__title">{title}{meta && <small> · {meta}</small>}</div>
          {right && <div className="be-dock__links">{right}</div>}
        </div>
        {children && <div className="be-dock__body">{children}</div>}
        {foot && <div className="be-dock__foot">{foot}</div>}
      </div>
    </div>
  );
}

/** 작업 카드 오른쪽 위 글 버튼 */
export function DockLink({ children, onClick, to, icon, disabled, title }: {
  children: ReactNode; onClick?: () => void; to?: string; icon?: ReactNode; disabled?: boolean; title?: string;
}) {
  if (to && !disabled) return <Link className="be-docklink" to={to}>{icon}{children}</Link>;
  return <button type="button" className="be-docklink" onClick={onClick} disabled={disabled} title={disabled ? title : undefined}>{icon}{children}</button>;
}

/** 알약 칩 버튼(공간 유형 · 톤 · 시점 · 조명 · 표시 토글) */
export function Pill({ on, onClick, children, swatch, disabled, title, testId }: {
  on?: boolean; onClick?: () => void; children: ReactNode; swatch?: string; disabled?: boolean; title?: string; testId?: string;
}) {
  return (
    <button type="button" className={cx('be-pill', on && 'be-pill--on', swatch && 'be-pill--swatch')} aria-pressed={!!on} onClick={onClick}
      disabled={disabled} title={title} data-testid={testId}>
      {swatch && <span className="be-swatch" style={{ background: swatch }} aria-hidden="true" />}
      {children}
    </button>
  );
}

export function FieldLabel({ children }: { children: ReactNode }) {
  return <span className="be-flabel">{children}</span>;
}

/** 주 버튼(→) · 보조 버튼 */
export function MainButton({ children, onClick, disabled, reason, busy, testId, arrow = true }: {
  children: ReactNode; onClick?: () => void; disabled?: boolean; reason?: string; busy?: boolean; testId?: string; arrow?: boolean;
}) {
  return (
    <button type="button" className="be-btn be-btn--primary" onClick={onClick} disabled={disabled || busy} title={disabled ? reason : undefined}
      data-testid={testId}>
      {busy && <Spinner label="진행 중" />}
      <span>{children}</span>
      {arrow && <Icon name="arrowRight" size={16} />}
    </button>
  );
}

export function SubButton({ children, onClick, to, disabled, testId, danger }: {
  children: ReactNode; onClick?: () => void; to?: string; disabled?: boolean; testId?: string; danger?: boolean;
}) {
  if (to) return <Link className={cx('be-btn', danger && 'be-btn--danger')} to={to} data-testid={testId}>{children}</Link>;
  return <button type="button" className={cx('be-btn', danger && 'be-btn--danger')} onClick={onClick} disabled={disabled} data-testid={testId}>{children}</button>;
}

/** 한 줄 입력(말로 고치기 · 배치 수정 요청 · 수정 요청 · 진행 중 요청) — 한글 조합 중 Enter 무시 */
export function PromptBar({ label, placeholder, onSend, busy, disabled, initial, testId }: {
  label: string; placeholder: string; onSend: (text: string) => Promise<unknown> | void; busy?: boolean; disabled?: boolean; initial?: string; testId?: string;
}) {
  const [v, setV] = useState(initial ?? '');
  const id = useRef(`be-prompt-${Math.random().toString(36).slice(2, 8)}`).current;
  useEffect(() => { if (initial) setV(initial); }, [initial]);
  const send = async () => {
    const t = v.trim();
    if (!t || busy || disabled) return;
    const r = await onSend(t);
    if (r !== false) setV('');
  };
  return (
    <div className="be-prompt" data-testid={testId}>
      <label htmlFor={id} className="wm-sr-only">{label}</label>
      <input id={id} value={v} placeholder={placeholder} onChange={(e) => setV(e.target.value)} disabled={disabled}
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); void send(); } }} />
      <button type="button" className="be-prompt__send" aria-label={`${label} 보내기`} onClick={() => void send()} disabled={!v.trim() || busy || disabled}>
        {busy ? <Spinner label="보내는 중" /> : <Icon name="send" size={15} />}
      </button>
    </div>
  );
}

/** 불러오는 중 · 오류 자리 */
export function Loading() {
  return <div className="be-center"><Spinner /></div>;
}

export function Fail({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="be-center" role="alert">
      <div className="be-fail">{message}</div>
      {onRetry && <button type="button" className="be-btn" onClick={onRetry}>다시 시도</button>}
    </div>
  );
}

/** 「오늘 HH:mm」 / 「어제 HH:mm」 / 「M월 D일」(§10.2) */
export function whenLabel(iso: string, now = new Date()): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const fmt = new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', year: 'numeric', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false });
  const parts = (x: Date) => Object.fromEntries(fmt.formatToParts(x).map((p) => [p.type, p.value]));
  const a = parts(d);
  const n = parts(now);
  const y = parts(new Date(now.getTime() - 86_400_000));
  const hm = `${a.hour === '24' ? '00' : a.hour}:${a.minute}`;
  if (a.year === n.year && a.month === n.month && a.day === n.day) return `오늘 ${hm}`;
  if (a.year === y.year && a.month === y.month && a.day === y.day) return `어제 ${hm}`;
  return `${Number(a.month)}월 ${Number(a.day)}일`;
}

/** 받침 있는지(숫자 · 영문 대문자 끝 포함, 서버 text.py 와 같은 규칙) */
export function hasBatchim(word: string): boolean {
  const s = (word || '').trim();
  if (!s) return false;
  const ch = s[s.length - 1];
  const code = ch.charCodeAt(0);
  if (code >= 0xac00 && code <= 0xd7a3) return (code - 0xac00) % 28 !== 0;
  if (/[0-9]/.test(ch)) return '013678'.includes(ch);
  if (/[A-Za-z]/.test(ch)) return 'LMNRlmnr'.includes(ch);
  return false;
}
export const jo = (word: string, withB: string, without: string) => `${word}${hasBatchim(word) ? withB : without}`;

export const VIEW_PHRASE: Record<string, (label: string) => string> = {
  aerial45: () => '45° 조감',
  entrance: () => '입구',
  top: () => '탑뷰',
  product_front: (label) => label,
  custom: (label) => label,
};
