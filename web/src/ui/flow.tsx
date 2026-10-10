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
      <svg width={size === 30 ? 12 : size === 34 ? 13 : 14} height={size === 30 ? 12 : size === 34 ? 13 : 14} viewBox="0 0 24 24" fill="currentColor" aria-hidden><path d="M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.9z" /></svg>
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
  /** icon: 글 앞 아이콘(보드 MI2 「🔍 웹 검색 후 정제로」 같은 것) · busyLabel: 진행 중 글(기본 「저장 중…」) */
  primary: { label: string; onClick?: () => void; to?: string; disabled?: boolean; busy?: boolean; icon?: ReactNode; busyLabel?: string };
}) {
  const btn = primary.to && !primary.disabled
    ? <Link className="wm-flow__primary" to={primary.to}>{primary.icon}{primary.label}</Link>
    : <button type="button" className="wm-flow__primary" onClick={primary.onClick} disabled={primary.disabled || primary.busy} aria-busy={primary.busy || undefined}>
      {primary.icon}{primary.busy ? primary.busyLabel ?? '저장 중…' : primary.label}</button>;
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

/** flow.json 에서 `stages.<key>` 블록(키 줄 ~ 닫는 괄호) 줄 범위 — 2칸 들여쓰기 JSON 기준 */
export function stageLineRange(lines: string[], key: string): [number, number] | null {
  const st = lines.findIndex((l) => l === '  "stages": {');
  if (st < 0) return null;
  const i = lines.findIndex((l, j) => j > st && l.startsWith(`    "${key}": `));
  if (i < 0) return null;
  if (!/[{[]$/.test(lines[i])) return [i, i];
  for (let j = i + 1; j < lines.length; j++) if (/^ {4}[}\]]/.test(lines[j])) return [i, j];
  return [i, i];
}

/** flow.json 전체 보기 팝업(보드 JsonPopup 900×780) — 전체 / 추가된 값만 · 이번에 추가 · 바뀐 줄 초록 · 복사 */
export function JsonPopup({ open, onClose, json, highlightKey, highlightAll, title = 'flow.json', sub }: {
  open: boolean; onClose: () => void; json: unknown; highlightKey?: string | null; title?: string; sub?: ReactNode;
  /** 새 Storyboard 처럼 전체가 이번에 생긴 값이면 모든 줄을 강조 */
  highlightAll?: boolean;
}) {
  const [only, setOnly] = useStateLocal(false);
  const lines = JSON.stringify(json ?? {}, null, 2).split('\n');
  const rg: [number, number] | null = highlightAll ? [0, lines.length - 1] : highlightKey ? stageLineRange(lines, highlightKey) : null;
  const rows = lines.map((t, i) => ({ n: i + 1, t, add: !!rg && i >= rg[0] && i <= rg[1] })).filter((r) => !only || r.add);
  const copy = () => { try { void navigator.clipboard.writeText(lines.join('\n')); } catch { /* 복사 못 함 */ } };
  return (
    <Modal open={open} onClose={onClose} width={900} height={780} ariaLabel={`${title} 전체 보기`}
      // 보드 JsonPopup: 머리 = 제목(mono 16/700) · 오른쪽 탭(전체 · 추가된 값만) · ×
      title={<span className="wm-jsonpop__head">
        <span className="wm-jsonpop__titles"><span className="wm-jsonpop__t">{title}</span>{sub && <span className="wm-jsonpop__s">{sub}</span>}</span>
        <span className="wm-jsonpop__tabs" role="tablist" aria-label="보기">
          <button type="button" role="tab" aria-selected={!only} className={cx('wm-jsonpop__tab', !only && 'wm-jsonpop__tab--on')} onClick={() => setOnly(false)}>전체</button>
          <button type="button" role="tab" aria-selected={only} className={cx('wm-jsonpop__tab', only && 'wm-jsonpop__tab--on')} onClick={() => setOnly(true)} disabled={!rg}
            title={rg ? `${rows.length}줄` : '이번에 추가 · 바뀐 값이 없어요'}>추가된 값만</button>
        </span></span>}
      bodyStyle={{ padding: 0, display: 'flex', flexDirection: 'column' }}
      footer={<div className="wm-jsonpop__foot">
        <span className="wm-jsonpop__legend"><span aria-hidden />이번에 추가 · 바뀐 줄</span>
        <button type="button" className="wm-btn wm-btn--h38" onClick={copy}>복사</button>
        <button type="button" className="wm-btn wm-btn--primary wm-btn--h38" onClick={onClose}>닫기</button>
      </div>}>
      <div className="wm-jsonlines">{rows.map((r) => (
        <div key={r.n} className={cx('wm-jsonline', r.add && 'wm-jsonline--add')}><span>{r.n}</span><span>{r.t}</span></div>
      ))}</div>
    </Modal>
  );
}

/**
 * 완료 화면(보드 Done · VP_Done · SC_Done · CA_Done) — 저장했어요 머리 · Storyboard 카드(단계 칸 · 요약 md 더해진 부분 · flow.json 추가 값 접힘)
 * · 전체 JSON 팝업(fullJson 이 있으면 flow.json 전체에서 stages.<key> 를 강조) · 후속 작업.
 */
export function FlowDone({ title, sub, sbName, sbStage, stages, md, stageKey, stage, fullJson, onEdit, follow, onOpenStoryboard, jsonHead, jsonTitle, highlightAll }: {
  title: string; sub?: ReactNode; sbName?: string | null; sbStage?: string; stages: DoneStage[]; md: string; stageKey: string; stage: unknown;
  fullJson?: unknown; onEdit?: () => void; follow?: ReactNode; onOpenStoryboard?: () => void;
  /** FLOW.JSON 칸 머리 글(기본 `stages.<key> · n줄 추가` · 새 Storyboard 면 `새 Storyboard 전체`) */
  jsonHead?: ReactNode;
  /** 전체 JSON 팝업 제목(기본 flow.json · 보드 `SB-06/flow.json`) */
  jsonTitle?: string;
  /** 전체 JSON 팝업에서 모든 줄을 이번에 생긴 값으로 강조(새 Storyboard) */
  highlightAll?: boolean;
}) {
  const [full, setFull] = useStateLocal(false);
  const folded = `"stages.${stageKey}": ${JSON.stringify(foldJson(stage), null, 2)}`;
  const addLines = JSON.stringify(stage ?? {}, null, 2).split('\n').length;
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
            <div className="wm-done__colhead wm-done__colhead--json"><b>FLOW.JSON</b><span>{jsonHead ?? `stages.${stageKey} · ${addLines}줄 추가`}</span><span style={{ flex: 1 }} />
              <button type="button" className="wm-done__jsonbtn" onClick={() => setFull(true)}>전체 JSON 보기</button></div>
            <pre>{folded}</pre>
          </div>
        </div>
      </div>
      <div className="wm-done__follow"><span className="wm-done__followh">후속 작업</span>{follow ?? (
        <div className="wm-done__nofollow"><span>이 콘텐츠는 후속 작업이 없어요. Storyboard에서 다른 콘텐츠를 이어서 만들 수 있어요.</span>
          {onOpenStoryboard && <button type="button" className="wm-done__nofollowlink" onClick={onOpenStoryboard}>Storyboard로</button>}</div>
      )}</div>
      <JsonPopup open={full} onClose={() => setFull(false)} json={fullJson ?? { stages: { [stageKey]: stage } }} highlightKey={stageKey} highlightAll={highlightAll} title={jsonTitle} />
    </div>
  );
}

/** 후속 작업 카드(보드 Done: h84 r16 · 아이콘 40 · 제목 15/700 · 설명 12.5 · →) */
export function FollowCard({ to, icon, title, desc }: { to: string; icon: string; title: string; desc: string }) {
  return (
    <Link className="wm-follow" to={to}>
      <span className="wm-follow__ic" aria-hidden><PathIcon d={icon} size={18} color="#fff" /></span>
      <span className="wm-follow__txt"><b>{title}</b><span>{desc}</span></span>
      <Icon name="arrowRight" size={16} color="var(--wm-brand)" />
    </Link>
  );
}
