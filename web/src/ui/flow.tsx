/**
 * 콘텐츠 흐름 공통 조각(웹앱 ① 2026-10-08 재설계 — 보드 SBBar · VP2 · SC2 · CA2 · DS2 의 공통 부분).
 * 값은 보드 인라인 스타일 그대로다(px). 색은 토큰.
 *
 *   <FlowScreen bar={<LinkedStoryboardBar …/>} pad="18px 40px">   // 본문 = 보드 section(높이를 채움, 아래 FlowFooter 고정)
 *     <FlowHead title="…" desc="…" actions={<><Button …/><AiButton …/></>} />
 *     <AiBar count={…} onAcceptAll={…}>…</AiBar>
 *     <div className="wm-flow__grid" style={{ gridTemplateColumns: '280px minmax(0, 1fr)' }}>…</div>
 *     <FlowFooter back={{ to, label }} summary="…" primary={{ label: '저장', onClick }} />
 *   </FlowScreen>
 */
import { useState as useStateLocal, type CSSProperties, type ReactNode } from 'react';
import { Link } from 'react-router';
import { cx } from './controls';
import { Icon, PathIcon } from './icons';
import { Modal } from './overlay';

export interface StoryboardChip {
  id: string;
  name: string;
  /** rq · dss · mi · ca · vp · sp · sc · ppt 중 완료된 것 */
  done: string[];
  /** 지금 화면이 채우는 단계(초록 칸) */
  current?: string;
  branch?: boolean;
  onOpen?: () => void;
}

const ORDER = ['rq', 'dss', 'mi', 'ca', 'vp', 'sp', 'sc', 'ppt'];

function stageLabel(done: string[]) {
  const n = ['mi', 'ca', 'vp', 'sp', 'sc'].filter((k) => done.includes(k)).length;
  if (done.includes('ppt')) return '제안서까지';
  if (!done.includes('dss')) return '요구사항까지';
  return n ? `DSS + 콘텐츠 ${n}/5` : 'DSS까지';
}

/** 연결된 Storyboard 바(보드 SBBar, 52px) — 칩 = 이름 · 진행 칸 8 · 단계, 누르면 요약 팝업 */
export function LinkedStoryboardBar({ chips, note, emptyText = '저장하면 Storyboard가 자동으로 만들어져요' }:
  { chips: StoryboardChip[]; note?: ReactNode; emptyText?: string }) {
  return (
    <div className="wm-sbbar" role="region" aria-label="연결된 Storyboard">
      <span className="wm-sbbar__label"><PathIcon d="M4 5h16v14H4z M4 11h16 M10 11v8" size={14} color="var(--wm-brand)" />연결된 Storyboard</span>
      {!chips.length && <span className="wm-sbbar__empty">{emptyText}</span>}
      {chips.map((c, i) => (
        <button key={c.id} type="button" className={cx('wm-sbbar__chip', i === 0 && 'wm-sbbar__chip--on')} onClick={c.onOpen} aria-label={`${c.name} 요약 보기`}>
          <span className="wm-sbbar__name">{c.name}</span>
          {c.branch && <span className="wm-sbbar__branch">분기</span>}
          <span className="wm-sbbar__dots" aria-hidden>
            {ORDER.map((k, j) => (
              <span key={k} className={cx('wm-sbbar__dot', (j === 2 || j === 7) && 'wm-sbbar__dot--gap',
                c.current === k && i === 0 ? 'wm-sbbar__dot--cur' : c.done.includes(k) && 'wm-sbbar__dot--on')} />
            ))}
          </span>
          <span className="wm-sbbar__stage">{stageLabel(c.done)}</span>
        </button>
      ))}
      <span style={{ flex: 1 }} />
      {note && <span className="wm-sbbar__note">{note}</span>}
    </div>
  );
}

/** 작업 화면 본문(보드 section): SB 바 아래를 꽉 채우고 안에서 패널이 스크롤한다. pad = 보드 section padding 그대로 */
export function FlowScreen({ bar, pad = '18px 40px', gap = 12, children, className }: { bar?: ReactNode; pad?: string; gap?: number; children: ReactNode; className?: string }) {
  return (
    <div className={cx('wm-flow', className)}>
      {bar}
      <section className="wm-flow__section" style={{ padding: pad, gap }}>{children}</section>
    </div>
  );
}

/** 화면 머리(h1 23/700 · 설명 13) + 오른쪽 버튼 */
export function FlowHead({ title, desc, actions }: { title: ReactNode; desc?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="wm-flow__head">
      <div className="wm-flow__titles">
        <h1 className="wm-flow__h1">{title}</h1>
        {desc && <span className="wm-flow__desc">{desc}</span>}
      </div>
      {actions}
    </div>
  );
}

/** AI 추가기능 버튼(보드 o-aib · v-aib · c-aib: h38 r10 · 1px #c9d1f2 · 13/700 brand · ✦) */
export function AiButton({ children, onClick, busy, disabled, size = 38, title }:
  { children: ReactNode; onClick: () => void; busy?: boolean; disabled?: boolean; size?: 30 | 34 | 38; title?: string }) {
  return (
    <button type="button" className={cx('wm-aib', `wm-aib--h${size}`)} onClick={onClick} disabled={disabled || busy} aria-busy={busy || undefined} title={title}>
      <svg width={size === 30 ? 12 : 14} height={size === 30 ? 12 : 14} viewBox="0 0 24 24" fill="currentColor" aria-hidden><path d="M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.9z" /></svg>
      {busy ? 'AI가 찾는 중…' : children}
    </button>
  );
}

/** AI 추천 안내 줄(보드: h38 r10 · 점선 #b8c2e6 · #f7f8fd · 12.5 brand) — 수락해야 들어간다 */
export function AiBar({ children, actionLabel = '모두 수락', onAction }: { children: ReactNode; actionLabel?: string; onAction?: () => void }) {
  return (
    <div className="wm-aibar" role="status">
      <span style={{ flex: 1, minWidth: 0 }}>{children}</span>
      {onAction && <button type="button" className="wm-aibar__btn" onClick={onAction}>{actionLabel}</button>}
    </div>
  );
}

export type ByKind = 'manual' | 'ai-pending' | 'ai-accepted';
const BY_LABEL: Record<ByKind, string> = { manual: '직접', 'ai-pending': 'AI 추천', 'ai-accepted': 'AI 추천 · 수락' };

/** 출처 태그(h20 r5 11/700): 직접 · AI 추천(점선) · AI 추천 · 수락(초록) */
export function ByTag({ by, label }: { by: ByKind; label?: string }) {
  return <span className={cx('wm-bytag', `wm-bytag--${by}`)}>{label ?? BY_LABEL[by]}</span>;
}

/** 제품 · 솔루션 종류 태그(h20 r5 11/700) */
export function KindTag({ kind }: { kind: 'product' | 'solution' }) {
  return <span className={cx('wm-kindtag', kind === 'solution' && 'wm-kindtag--sol')}>{kind === 'solution' ? '솔루션' : '제품'}</span>;
}

/** 아래 줄: ‹ 뒤로 · (빈칸) · 요약 · 주 버튼(h48 r12 15/700). disabled 면 회색(이유는 summary 에) */
export function FlowFooter({ back, summary, summaryTone, primary }: {
  back?: { to: string; label: string };
  summary?: ReactNode;
  summaryTone?: 'warn';
  primary: { label: string; onClick?: () => void; to?: string; disabled?: boolean; busy?: boolean };
}) {
  const btn = primary.to && !primary.disabled
    ? <Link className="wm-flow__primary" to={primary.to}>{primary.label}</Link>
    : <button type="button" className="wm-flow__primary" onClick={primary.onClick} disabled={primary.disabled || primary.busy} aria-busy={primary.busy || undefined}>{primary.busy ? '저장 중…' : primary.label}</button>;
  return (
    <div className="wm-flow__foot">
      {back && <Link className="wm-flow__back" to={back.to}><Icon name="chevronLeft" size={14} strokeWidth={2.4} />{back.label}</Link>}
      <span style={{ flex: 1 }} />
      {summary && <span className={cx('wm-flow__summary', summaryTone === 'warn' && 'wm-flow__summary--warn')}>{summary}</span>}
      {btn}
    </div>
  );
}

/** 흰 패널(r14 · 1px 선) — 점선이면 AI 후보 */
export function FlowPanel({ children, dashed, style, className, ...rest }: { children: ReactNode; dashed?: boolean; style?: CSSProperties; className?: string } & Record<string, unknown>) {
  return <div className={cx('wm-flow__panel', dashed && 'wm-flow__panel--dashed', className)} style={style} {...rest}>{children}</div>;
}

export interface DoneStage { key: string; label: string; ref?: string | null; state: 'done' | 'cur' | 'none' }

/** JSON 을 접힌 모양으로 — 2개 넘는 객체 배열은 첫 항목 + `… n개 더 · 전체 JSON에서 보기`(보드 Done fold) */
export function foldJson(v: unknown): unknown {
  if (Array.isArray(v)) {
    if (v.length > 2 && v[0] && typeof v[0] === 'object') return [foldJson(v[0]), `… ${v.length - 1}개 더 · 전체 JSON에서 보기`];
    return v.map(foldJson);
  }
  if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v as Record<string, unknown>).map(([k, x]) => [k, foldJson(x)]));
  return v;
}

/**
 * 완료 화면(보드 Done · VP_Done · SC_Done · CA_Done) — 저장했어요 머리 · Storyboard 카드(단계 칸 · 요약 md 더해진 부분 · flow.json 추가 값 접힘)
 * · 전체 JSON 팝업 · 후속 작업. JSON 은 stage(`stages.<key>`)만 받는다.
 */
export function FlowDone({ title, sub, sbName, sbStage, stages, md, stageKey, stage, onEdit, follow, onOpenStoryboard }: {
  title: string; sub?: ReactNode; sbName?: string | null; sbStage?: string; stages: DoneStage[]; md: string; stageKey: string; stage: unknown;
  onEdit?: () => void; follow?: ReactNode; onOpenStoryboard?: () => void;
}) {
  const [full, setFull] = useStateLocal(false);
  const folded = `"stages.${stageKey}": ${JSON.stringify(foldJson(stage), null, 2)}`;
  const fullText = JSON.stringify({ stages: { [stageKey]: stage } }, null, 2);
  const lines = fullText.split('\n');
  const addLines = lines.length;
  return (
    <div className="wm-done">
      <div className="wm-done__head">
        <span className="wm-done__check" aria-hidden><Icon name="check" size={22} color="#fff" strokeWidth={2.6} /></span>
        <span className="wm-flow__titles"><h1 className="wm-flow__h1">{title}</h1>{sub && <span className="wm-flow__desc">{sub}</span>}</span>
        {onEdit && <button type="button" className="wm-btn wm-btn--h40" onClick={onEdit}>다시 고치기</button>}
      </div>
      <div className="wm-done__card">
        <div className="wm-done__sbrow">
          <span className="wm-done__sbname">Storyboard{sbName ? ` · ${sbName}` : ''}</span>
          <span style={{ flex: 1 }} />
          {sbStage && <span className="wm-flow__desc" style={{ fontSize: 12.5 }}>{sbStage}</span>}
          {onOpenStoryboard && <button type="button" className="wm-done__link" onClick={onOpenStoryboard}>Storyboard 열기</button>}
        </div>
        <div className="wm-done__stages">
          {stages.map((s) => (
            <span key={s.key} className={cx('wm-done__stage', `wm-done__stage--${s.state}`)}><b>{s.label}</b><small>{s.ref || '—'}</small></span>
          ))}
        </div>
        <div className="wm-done__cols">
          <div className="wm-done__md"><div className="wm-done__colhead"><b>SUMMARY.MD</b><span>요약본에 더해진 부분</span></div><pre>{md}</pre></div>
          <div className="wm-done__json">
            <div className="wm-done__colhead wm-done__colhead--json"><b>FLOW.JSON</b><span>stages.{stageKey} · {addLines}줄 추가</span><span style={{ flex: 1 }} />
              <button type="button" className="wm-done__jsonbtn" onClick={() => setFull(true)}>전체 JSON 보기</button></div>
            <pre>{folded}</pre>
          </div>
        </div>
      </div>
      <div className="wm-done__follow"><span className="wm-done__followh">후속 작업</span>{follow ?? (
        <div className="wm-done__nofollow"><span>이 콘텐츠는 후속 작업이 없어요. Storyboard에서 다른 콘텐츠를 이어서 만들 수 있어요.</span></div>
      )}</div>
      <Modal open={full} onClose={() => setFull(false)} width={900} height={780} ariaLabel="flow.json 전체 보기"
        title={<span style={{ display: 'flex', flexDirection: 'column', gap: 3 }}><span style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 16 }}>flow.json</span><span style={{ fontSize: 12.5, color: 'var(--wm-text-muted)', fontWeight: 400 }}>초록 줄이 이번에 추가 · 바뀐 값이에요 · {lines.length}줄</span></span>}
        bodyStyle={{ padding: '10px 0', background: 'var(--wm-surface-2)' }}>
        <div className="wm-jsonlines">{lines.map((t, i) => (
          <div key={i} className={cx('wm-jsonline', i > 1 && i < lines.length - 2 && 'wm-jsonline--add')}><span>{i + 1}</span><span>{t}</span></div>
        ))}</div>
      </Modal>
    </div>
  );
}
