/**
 * 콘텐츠 목록(보드 webapp1 List v61) — 본문 폭 전체 가운데 「새 ○○ 만들기」 · 그 아래 넉넉히 띄운 작업 내역 그리드.
 * 카드 = 썸네일(콘텐츠 보기 팝업 카드를 반 크기로) · 제목 · 코드 · 수정 · n/N 단계 · 연결된 Storyboard.
 * Storyboard 목록(SB0)도 같은 부품(ListHero · HistoryHead · ThumbFrame · StepMeter)을 쓴다.
 */
import { Fragment, useMemo, useState, type ReactNode } from 'react';
import { Link } from 'react-router';
import { useShellPage } from '../ShellContext';
import { ErrorState, Icon, PathIcon, Skeleton, cx, josa, toast, useConfirm } from '@/ui';
import { CONTENT, useFlowContents, useFlowsById, type ContentKey, type FlowCard } from './api';
import { SBPopup, whenText } from './parts';
import './flow.css';

const SB_ICON = 'M4 5h16v14H4z M4 11h16 M10 11v8';

// ── 공용 부품(목록 · SB0) ─────────────────────────────

/** 「새 ○○ 만들기」(보드 List · SB0: 1100×156 r18 · 브랜드 바탕) — 아래 줄에 단계 흐름(① → ② → ③)과 한마디 */
export function ListHero({ to, label, steps, note }: { to: string; label: string; steps: string[]; note: string }) {
  return (
    <Link className="fl-hero" to={to}>
      <span className="fl-hero__main">
        <span className="fl-hero__plus" aria-hidden><Icon name="plus" size={22} strokeWidth={2.6} /></span>
        <span className="fl-hero__label">{label}</span>
      </span>
      <span className="fl-hero__flow">
        {steps.map((t, i) => (
          <Fragment key={`${i}-${t}`}>
            {i > 0 && <Icon name="arrowRight" size={14} strokeWidth={2.2} color="var(--wm-brand-on-dark)" />}
            <span className="fl-hero__step"><b>{i + 1}</b>{t}</span>
          </Fragment>
        ))}
        <span className="fl-hero__sep" aria-hidden />
        <span className="fl-hero__note">{note}</span>
      </span>
    </Link>
  );
}

/** 작업 내역 머리(보드: 16px 굵게 · 수 칩 · 오른쪽 범례) */
export function HistoryHead({ count, legend }: { count: number; legend?: ReactNode }) {
  return (
    <div className="fl-histhead">
      <h2>작업 내역</h2>
      <span className="fl-histcount">{count}</span>
      <span style={{ flex: 1 }} />
      {legend}
    </div>
  );
}

export type SegState = 'done' | 'cur' | 'todo';

/** 범례 조각 — [막대 색, 이름] */
export function SegLegend({ items, tail }: { items: Array<[SegState, string]>; tail?: string }) {
  return (
    <span className="fl-seglegend">
      {items.map(([s, t]) => <span key={t}><i className={`fl-seg fl-seg--${s}`} />{t}</span>)}
      {tail && <span className="fl-seglegend__tail">{tail}</span>}
    </span>
  );
}

/** n/N 단계 — 「2/3 단계 · 공간 · 제품」 + 막대 N칸(지난 · 지금 · 남은). gaps: 그 칸 앞에 조금 더 띄운다(SB0 8칸: 3 · 8번째) */
export function StepMeter({ n, total, text, segs, gaps = [] }: { n: number; total: number; text: string; segs: SegState[]; gaps?: number[] }) {
  return (
    <div className="fl-step" aria-label={`${total}단계 중 ${n}단계 · ${text}`}>
      <div className="fl-steptxt" aria-hidden><b>{n}/{total}</b><strong>단계</strong><span>· {text}</span></div>
      <div className="fl-segs" aria-hidden>{segs.map((s, i) => <i key={i} className={cx('fl-seg', `fl-seg--${s}`, gaps.includes(i) && 'fl-seg--gap')} />)}</div>
    </div>
  );
}

/** 썸네일 틀(보드 258×148 · 회색 바탕 위 흰 문서 236×136) — 안은 472px 폭으로 그려 반으로 줄인다. 오른쪽 아래 배지.
 *  to 를 주면 그 화면으로 가는 링크(키보드는 제목 링크로 — 탭 순서에서 뺀다), 없으면 카드 전체가 링크일 때 쓰는 그림 */
export function ThumbFrame({ to, children, badge, tone = 'done' }: { to?: string; children: ReactNode; badge?: string; tone?: 'done' | 'draft' | 'line' }) {
  const inner = (
    <>
      <span className="fl-thumb__page"><span className="fl-thumb__in">{children}</span></span>
      {badge && <span className={cx('fl-thumb__badge', `fl-thumb__badge--${tone}`)}>{badge}</span>}
    </>
  );
  return to ? <Link className="fl-thumb" to={to} tabIndex={-1} aria-hidden>{inner}</Link> : <span className="fl-thumb" aria-hidden>{inner}</span>;
}

/** 콘텐츠 썸네일 내용 — 콘텐츠 보기 팝업 카드(facts 3 · groups[머리 · 부제 · 줄]) 그대로. 카드가 없으면(작성 중 · 카드 없이 저장) 빈 틀 */
export function CardMini({ card, note }: { card?: FlowCard | null; note: string }) {
  if (!card || (!card.facts?.length && !card.groups?.length)) {
    return (
      <>
        <span className="fl-mini__facts"><span className="fl-mini__ph" /><span className="fl-mini__ph" /><span className="fl-mini__ph fl-mini__ph--dash" /></span>
        <span className="fl-mini__box fl-mini__box--ph"><i style={{ width: '62%' }} /><i style={{ width: '84%' }} /><i style={{ width: '48%' }} /></span>
        <span className="fl-mini__note">{note}</span>
      </>
    );
  }
  return (
    <>
      {!!card.facts?.length && (
        <span className="fl-mini__facts">{card.facts.slice(0, 3).map(([k, v], i) => <span key={`${i}-${k}`} className="fl-mini__fact"><small>{k}</small><b>{v}</b></span>)}</span>
      )}
      {(card.groups ?? []).slice(0, 3).map((g, i) => (
        <span key={`${i}-${g.h}`} className="fl-mini__box">
          <span className="fl-mini__gh"><b>{g.h}</b>{g.sub && <em>{g.sub}</em>}</span>
          <span className="fl-mini__lines">{(g.lines ?? []).slice(0, 3).map((l, j) => (
            <span key={j}><span>{l.t}</span>{l.note && <i className={cx('fl-mini__tag', l.note === '확인 필요' && 'fl-mini__tag--warn', l.note === '확장' && 'fl-mini__tag--ext')}>{l.note}</i>}</span>
          ))}</span>
        </span>
      ))}
    </>
  );
}

// ── 콘텐츠 목록(보드 List) ───────────────────────────

export interface DraftRow {
  title: string; ref?: string | null; to: string; sbIds: string[]; when?: string | null;
  /** 지금 단계(1부터 · CONTENT[key].steps 의 자리). 없으면 Storyboard 를 고른 다음 단계(사전 작업이 없는 요구사항은 1) */
  step?: number;
  /** 아직 저장 전 초안 지우기(보드에 없음 — 카드에 손을 올리면 × · 확인 뒤 지운다). 없으면 × 를 그리지 않는다 */
  onDelete?: () => Promise<unknown>;
}

interface Row {
  key: string; title: string; ref: string; to: string; when: string | null; draft: boolean; step: number; card: FlowCard | null;
  sbs: Array<{ id: string; name: string }>; onDelete?: DraftRow['onDelete'];
}

/** 연결된 Storyboard 칩 — 첫 칩 + 「+n」(누르면 모두 펼침). 칩을 누르면 요약 팝업 */
function SbChips({ sbs, onOpen }: { sbs: Row['sbs']; onOpen: (id: string) => void }) {
  const [all, setAll] = useState(false);
  const shown = all ? sbs : sbs.slice(0, 1);
  return (
    <div className={cx('fl-chips', all && 'fl-chips--all')}>
      {shown.map((b) => (
        <button key={b.id} type="button" className="fl-sbchip" onClick={() => onOpen(b.id)} title={b.name}>
          <PathIcon d={SB_ICON} size={11} color="var(--wm-brand)" strokeWidth={2.2} /><span>{b.name}</span>
        </button>
      ))}
      {!all && sbs.length > 1 && (
        <button type="button" className="fl-chipmore" onClick={() => setAll(true)} aria-label={`연결된 Storyboard ${sbs.length - 1}개 더 보기`} title={sbs.slice(1).map((b) => b.name).join(' · ')}>+{sbs.length - 1}</button>
      )}
    </div>
  );
}

/** 콘텐츠 목록(보드 List v61) — 저장된 콘텐츠(허브 · 썸네일 = 보기 팝업 카드)와 아직 저장 전 초안(drafts · 지금 단계) */
export function ContentListScreen({ content, drafts = [], extra }: { content: ContentKey; drafts?: DraftRow[]; extra?: ReactNode }) {
  const m = CONTENT[content];
  useShellPage({ section: m.label, title: '', hasTask: false });
  const q = useFlowContents(content);
  const [pop, setPop] = useState<string | null>(null);
  const { confirm, dialog } = useConfirm();
  const [gone, setGone] = useState<Set<string>>(() => new Set());
  const N = m.steps.length;
  const saved: Row[] = (q.data?.items ?? []).map((it) => ({
    key: it.route, title: it.title, ref: `${it.ref} v${it.ver}`, to: it.route, when: it.updated_at, draft: false, step: N, card: it.card ?? null,
    sbs: it.storyboards.map((s) => ({ id: s.id, name: s.name })),
  }));
  const savedRoutes = new Set(saved.map((r) => r.to));
  // 초안 칩은 id 대신 이름(보드 List) — 허브에서 읽는다
  const draftSbIds = useMemo(() => [...new Set(drafts.flatMap((d) => d.sbIds))], [drafts]);
  const draftSbs = useFlowsById(draftSbIds);
  const sbName = (id: string) => draftSbs[draftSbIds.indexOf(id)]?.data?.name ?? id;
  const firstStep = m.preKey ? 2 : 1;
  const draftRows: Row[] = drafts.filter((d) => !savedRoutes.has(d.to) && !gone.has(d.to)).map((d) => ({
    key: d.to, title: d.title, ref: d.ref ? `${d.ref} · 작성 중` : '작성 중', to: d.to, when: d.when ?? null, draft: true,
    step: Math.min(Math.max(d.step ?? firstStep, 1), N), card: null, sbs: d.sbIds.map((id) => ({ id, name: sbName(id) })), onDelete: d.onDelete,
  }));
  // 최근 수정 순(보드: 작성 중 초안 「방금」이 맨 앞) — 시각이 없는 줄은 뒤로
  const rows = [...saved, ...draftRows].sort((a, b) => (b.when ?? '').localeCompare(a.when ?? ''));
  const del = async (r: Row) => {
    if (!r.onDelete || !(await confirm({ title: '작성 중인 초안을 지울까요?', message: `‘${r.title || '이름 없음'}’ 초안을 지워요. 저장하지 않은 내용이라 되돌릴 수 없어요.`, confirmLabel: '지우기', tone: 'danger' }))) return;
    try { await r.onDelete(); setGone((g) => new Set(g).add(r.to)); toast('초안을 지웠어요'); } catch (e) { toast((e as Error).message || '지우지 못했어요'); }
  };
  const newTo = `/${m.base}/new`;
  const newLabel = `${m.newLabel} 만들기`;
  return (
    <div className="fl-list">
      <div className="fl-listhead">
        <div className="fl-listtitles">
          <h1>{m.label}</h1>
          <div className="fl-listdesc"><span>{m.desc}</span><span className="fl-tag fl-tag--brand">사전 작업 · {m.pre}</span><span className="fl-tag">후속 작업 · {m.post}</span></div>
        </div>
        {extra}
      </div>
      <ListHero to={newTo} label={newLabel} steps={m.steps} note={`모두 ${N}단계`} />
      <HistoryHead count={rows.length} legend={rows.length > 0 && <SegLegend items={[['done', '지난 단계'], ['cur', '지금 단계'], ['todo', '남은 단계']]} tail="최근 수정 순" />} />
      {q.isError && <ErrorState message="목록을 불러오지 못했어요" onRetry={() => q.refetch()} />}
      {q.isLoading && <Skeleton h={320} r={14} />}
      {!q.isLoading && rows.length > 0 && (
        <ul className="fl-grid" aria-label={`${m.label} 작업 내역`}>
          {rows.map((r) => {
            const segs: SegState[] = m.steps.map((_, i) => (!r.draft || i + 1 < r.step ? 'done' : i + 1 === r.step ? 'cur' : 'todo'));
            return (
              <li key={r.key} className="fl-card" data-draft={r.draft || undefined}>
                <ThumbFrame to={r.to} badge={r.draft ? '작성 중' : '완성'} tone={r.draft ? 'draft' : 'done'}>
                  <CardMini card={r.card} note={r.draft ? `작성 중 · ${m.steps[r.step - 1]} 단계` : '요약 카드가 아직 없어요'} />
                </ThumbFrame>
                <div className="fl-cardbody">
                  <Link className="fl-cardtitle" to={r.to}>{r.title || '이름 없음'}</Link>
                  <div className="fl-cardmeta"><span className="fl-cardref">{r.ref}</span><span className="fl-when">{whenText(r.when)}</span></div>
                  <StepMeter n={r.step} total={N} text={r.draft ? m.steps[r.step - 1] : '완성'} segs={segs} />
                  <SbChips sbs={r.sbs} onOpen={setPop} />
                </div>
                {r.onDelete && <button type="button" className="fl-del" aria-label={`${r.title || '초안'} 지우기`} onClick={() => del(r)}><Icon name="x" size={13} strokeWidth={2.4} /></button>}
              </li>
            );
          })}
        </ul>
      )}
      {!q.isLoading && !q.isError && rows.length === 0 && (
        <div className="fl-empty fl-empty--hist"><b>아직 만든 {m.short}{josa(m.short, '이', '가')} 없어요</b>
          <span>{content === 'rq' ? `위 「${newLabel}」로 시작해요 · 저장하면 Storyboard가 자동으로 만들어져요.` : `위 「${newLabel}」로 시작해요 · ${m.pre}${josa(m.pre, '이', '가')} 있어야 해요.`}</span></div>
      )}
      <SBPopup id={pop} onClose={() => setPop(null)} />
      {dialog}
    </div>
  );
}
