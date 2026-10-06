/** 경쟁사 분석 화면 공용 부품 — 보드 CA*.dc.html 모양. 색은 ca.css(토큰)에서. */
import type { ReactNode } from 'react';
import { Link } from 'react-router';
import { BoltIcon, Button, ErrorState, Grip, Icon, Skeleton, cx } from '@/ui';
import { SLOT_ORDER, type ChipView, type CompetitorView, type SlotView, type SlotsView } from './api';

/** 가운데 820 한 줄 화면 */
export function CaPage({ children }: { children: ReactNode }) {
  return <div className="ca-page"><section className="ca-col">{children}</section></div>;
}

export function Head({ kicker, title, desc, kickerIcon }: { kicker: ReactNode; title: ReactNode; desc?: ReactNode; kickerIcon?: ReactNode }) {
  return (
    <div className="ca-head">
      <span className="ca-kicker">{kickerIcon}{kicker}</span>
      <h1 className="ca-title">{title}</h1>
      {desc && <span className="ca-desc">{desc}</span>}
    </div>
  );
}

/** 아래 막대: `뒤로`(왼쪽) · 가운데 · 큰 버튼(오른쪽) */
export function FootBar({ back, children }: { back?: { to?: string; onClick?: () => void; label?: string; icon?: ReactNode } | null; children?: ReactNode }) {
  const icon = back?.icon ?? <Icon name="chevronLeft" size={14} strokeWidth={2.4} />;
  return (
    <div className="ca-foot">
      {back && (back.to
        ? <Link to={back.to} className="ca-back" onClick={back.onClick}>{icon}{back.label ?? '뒤로'}</Link>
        : <button type="button" className="ca-back" onClick={back.onClick}>{icon}{back.label ?? '뒤로'}</button>)}
      <span className="ca-grow" />
      {children}
    </div>
  );
}

/** 큰 버튼(h48 · 오른쪽 화살표) */
export function BigButton({ children, onClick, disabled, disabledReason, loading, arrow = true }:
  { children: ReactNode; onClick?: () => void; disabled?: boolean; disabledReason?: string; loading?: boolean; arrow?: boolean }) {
  return (
    <Button h={48} variant="primary" className="ca-big" onClick={onClick} disabled={disabled} disabledReason={disabledReason} loading={loading}
      iconRight={arrow ? <Icon name="arrowRight" size={16} strokeWidth={2.2} /> : undefined}>
      {children}
    </Button>
  );
}

export function InfoLine({ children }: { children: ReactNode }) {
  return (
    <div className="ca-info">
      <Icon name="info" size={14} color="var(--wm-text-subtle)" />
      <span>{children}</span>
    </div>
  );
}

export const GUIDE = '고객사 · 업종 · 장소 · 제품까지 알려 주면 경쟁사를 훨씬 잘 찾아요. 업종만 있어도 찾긴 하지만 후보가 넓어져요.';

/** 칸 칩 — 읽힘 초록(+ `일부`) · 비어 있음 점선 */
export function SlotChip({ slot, small }: { slot: SlotView; small?: boolean }) {
  const found = slot.found !== 'empty' && !!slot.value;
  return (
    <span className={cx('ca-slot', found ? 'ca-slot--found' : 'ca-slot--empty', small && 'ca-slot--sm')} data-slot={slot.key} data-found={slot.found}>
      {found && <Icon name="check" size={11} strokeWidth={3} />}
      <b>{slot.label}</b><i>·</i><span>{found ? slot.value : '비어 있음'}</span>
      {found && slot.found === 'partial' && <span className="ca-slot__part">일부</span>}
    </span>
  );
}

export function slotList(slots: SlotsView | undefined | null, order: 'board' | 'found-first' = 'board'): SlotView[] {
  if (!slots) return [];
  const list = SLOT_ORDER.map((k) => slots[k]);
  if (order === 'found-first') return [...list.filter((s) => s.found !== 'empty'), ...list.filter((s) => s.found === 'empty')];
  return list;
}

/** `입력에서 읽은 것` 줄 — 칩 4 + `{n} / 4` */
export function SlotStrip({ label, slots, count, loading, reading, order, extra }:
  { label: string; slots: SlotsView | null | undefined; count?: number | null; loading?: boolean; reading?: boolean; order?: 'board' | 'found-first'; extra?: ReactNode }) {
  const list = slotList(slots, order);
  return (
    <div className="ca-strip" role="group" aria-label={label} aria-busy={loading || undefined}>
      <span className="ca-strip__label">{label}</span>
      <div className="ca-strip__chips">
        {reading && <span className="ca-slot ca-slot--wait"><Icon name="file" size={11} />파일 읽는 중</span>}
        {list.length
          ? list.map((s) => <SlotChip key={s.key} slot={s} />)
          : ['고객사', '업종', '장소', '제품'].map((k) => (
            <span key={k} className={cx('ca-slot', loading ? 'ca-slot--wait' : 'ca-slot--empty')}><b>{k}</b><i>·</i><span>비어 있음</span></span>
          ))}
      </div>
      {extra}
      <span className="ca-strip__n">{count ?? list.filter((s) => s.found !== 'empty').length} / 4</span>
    </div>
  );
}

/** 확인 권장 칩(업종 기준 · 지역 미반영 · 업종 추정 · 장소 추정 · 업종 확인 · 후보 자동 확정 · 확인 필요 n) */
export function Flags({ chips }: { chips: ChipView[] | undefined }) {
  if (!chips?.length) return null;
  return (
    <div className="ca-flags" role="list" aria-label="확인 권장">
      {chips.map((c) => (
        <span key={c.key} role="listitem" className={cx('ca-flag', c.mode === 'auto' && 'ca-flag--auto')} data-chip={c.key}>
          {c.mode === 'check' && <Icon name="info" size={11} />}{c.label}
        </span>
      ))}
    </div>
  );
}

export function Switch({ on, onChange, label, disabled }: { on: boolean; onChange: (v: boolean) => void; label: string; disabled?: boolean }) {
  return <button type="button" role="switch" aria-checked={on} aria-label={label} className="ca-switch" disabled={disabled} onClick={() => onChange(!on)} />;
}

export function Letter({ letter, off, size }: { letter: string; off?: boolean; size?: 30 | 36 }) {
  return <span className={cx('ca-letter', off && 'ca-letter--off', size && `ca-letter--${size}`)} aria-hidden="true">{letter}</span>;
}

export function CandBadge({ c }: { c: Pick<CompetitorView, 'status' | 'status_label'> }) {
  return <span className={cx('ca-badge', `ca-badge--${c.status}`)}>{c.status_label}</span>;
}

/** 진행 줄의 점(완료 · 진행 중 · 대기) */
export function Dot({ state }: { state: 'done' | 'active' | 'run' | 'wait' | 'partial' }) {
  return (
    <span className={cx('ca-dot', `ca-dot--${state}`)} aria-hidden="true">
      {state === 'done' && <Icon name="check" size={11} strokeWidth={3} color="currentColor" />}
      {state === 'partial' && <Icon name="minus" size={11} strokeWidth={3} color="currentColor" />}
    </span>
  );
}

/** W 로고 + 제목 + 한 줄 */
export function Agent({ title, desc }: { title: ReactNode; desc?: ReactNode }) {
  return (
    <>
      <div className="ca-logo" aria-hidden="true">W</div>
      <div className="ca-agent"><h1>{title}</h1>{desc && <span>{desc}</span>}</div>
    </>
  );
}

export function Bar({ pct, wide }: { pct: number; wide?: boolean }) {
  const v = Math.max(0, Math.min(100, Math.round(pct)));
  return <div className={cx('ca-bar', wide && 'ca-bar--w560')} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={v}><span style={{ width: `${v}%` }} /></div>;
}

export function ModeChip({ mode }: { mode: 'auto' | 'pin' | string }) {
  return mode === 'pin'
    ? <span className="ca-mode ca-mode--pin"><Icon name="lock" size={10} strokeWidth={2.4} />고정</span>
    : <span className="ca-mode"><BoltIcon size={10} color="currentColor" />자동</span>;
}

export function VerdictChips({ up, eq, dn, unknown }: { up: number; eq: number; dn: number; unknown?: number }) {
  return (
    <span className="ca-vs">
      <span className="ca-v ca-v--up">우위 {up}</span>
      <span className="ca-v ca-v--eq">비슷 {eq}</span>
      <span className="ca-v ca-v--dn">열위 {dn}</span>
      {!!unknown && <span className="ca-v ca-v--unk" title="판정 못 한 기준은 세지 않아요">확인 필요 {unknown}</span>}
    </span>
  );
}

export function LoadingCol({ lines = 4 }: { lines?: number }) {
  return (
    <CaPage>
      <Skeleton w={120} h={14} />
      <Skeleton w={360} h={28} />
      {Array.from({ length: lines }).map((_, i) => <Skeleton key={i} h={48} r={12} />)}
    </CaPage>
  );
}

export function ErrorCol({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <CaPage><ErrorState message={message} onRetry={onRetry} /></CaPage>;
}

export function Band({ tone, children, action }: { tone?: 'warn' | 'muted' | 'danger'; children: ReactNode; action?: ReactNode }) {
  return (
    <div className={cx('ca-band', tone && `ca-band--${tone}`)} role="status">
      <span className="ca-band__text">{children}</span>
      {action}
    </div>
  );
}

/** 경쟁사 이름: `경쟁사 {글자}` + 실명 보조 글자(작업 화면 안에서만) */
export function CmpName({ letter, real }: { letter: string; real?: string | null }) {
  return <>경쟁사 {letter}{real ? <small>{real}</small> : null}</>;
}

export { Grip };
