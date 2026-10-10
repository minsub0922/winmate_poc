/**
 * 콘텐츠 흐름 공통 화면(보드 webapp1 SBBar · SBPopup · ContentPopup · List · Gate · Done) — 데이터는 Storyboard 허브(`./api`).
 * 기능 화면은 이것만 조합한다. 보드 px 그대로(본문 열 1180 안에서).
 */
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Link, useNavigate } from 'react-router';
import { useShellPage } from '../ShellContext';
import { ErrorState, FlowDone, Icon, LinkedStoryboardBar, Modal, PathIcon, Skeleton, cx, josa, toast, type DoneStage } from '@/ui';
import {
  CONTENT, ORDER, STAGE_LABEL, branchFlow, doneKeys, useFlow, useFlowContents, useFlowInvalidate, useFlows, useFlowsById,
  type ContentKey, type FlowCell, type FlowDoc, type FlowListItem, type StageKey,
} from './api';
import './flow.css';

const SB_ICON = 'M4 5h16v14H4z M4 11h16 M10 11v8';

export function whenText(iso?: string | null) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const hm = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  if (d.toDateString() === now.toDateString()) return `오늘 ${hm}`;
  const y = new Date(now); y.setDate(now.getDate() - 1);
  if (d.toDateString() === y.toDateString()) return '어제';
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

/** 진행 칸 8(보드 Gate · SB0 dots: 7×12 r2, 3번째 · 8번째 앞 간격) */
export function FlowDots({ cells, current, size = 'sm' }: { cells: FlowCell[]; current?: StageKey; size?: 'sm' | 'md' }) {
  return (
    <span className={cx('fl-dots', size === 'md' && 'fl-dots--md')} aria-hidden>
      {ORDER.map((k, i) => {
        const c = cells.find((x) => x.key === k);
        return <span key={k} className={cx('fl-dot', (i === 2 || i === 7) && 'fl-dot--gap', current === k ? 'fl-dot--cur' : c?.state === 'done' && 'fl-dot--on')} />;
      })}
    </span>
  );
}

// ── SB 바 · 요약 팝업 ─────────────────────────────────

/** 연결된 Storyboard 바(보드 SBBar) — Storyboard id 들로 진행 칸을 그리고, 누르면 요약 팝업 */
export function FlowBar({ sbIds, current, note, emptyText }: { sbIds: string[]; current?: StageKey; note?: ReactNode; emptyText?: string }) {
  const qs = useFlowsById(sbIds);
  const [pop, setPop] = useState<string | null>(null);
  const chips = sbIds.map((id, i) => {
    const d = qs[i]?.data;
    return { id, name: d?.name ?? id, branch: !!d?.parent, done: d ? doneKeys(d.cells) : [], current, onOpen: () => setPop(id) };
  });
  return (
    <>
      <LinkedStoryboardBar chips={chips} note={note} emptyText={emptyText} />
      <SBPopup id={pop} onClose={() => setPop(null)} />
    </>
  );
}

/** 팝업 닫기(보드 SBPopup · ContentPopup: 36×36 r10) */
function PopX({ onClose }: { onClose: () => void }) {
  return <button type="button" className="fl-popx" onClick={onClose} aria-label="닫기"><Icon name="x" size={16} strokeWidth={2.2} /></button>;
}

/** Storyboard 요약 팝업(보드 SBPopup 760×660) — 머리 · 바닥은 보드 값 그대로라 Modal 머리 · 바닥을 쓰지 않는다 */
export function SBPopup({ id, onClose }: { id: string | null; onClose: () => void }) {
  const q = useFlow(id);
  const d = q.data;
  return (
    <Modal open={!!id} onClose={onClose} width={760} height={660} ariaLabel="Storyboard 요약" bodyStyle={{ padding: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div className="fl-pophead fl-pophead--sb">
        <span className="fl-popic fl-popic--brand"><PathIcon d={SB_ICON} size={19} color="#fff" /></span>
        <span className="fl-poptitles"><span className="fl-popkind">Storyboard · {id}</span><span className="fl-popname">{d?.name ?? '…'}</span>
          <span className="fl-popsub">{d ? `${d.customer ?? ''}${d.parent ? ` · ${d.parent} · ${STAGE_LABEL[(d.branch_point?.stage as StageKey) ?? 'mi']}에서 분기` : ' · main'}` : ''}</span></span>
        <PopX onClose={onClose} />
      </div>
      {!d ? <div style={{ padding: 24, flex: 1 }}><Skeleton h={420} r={12} /></div> : (
        <>
          <div className="fl-track">{d.cells.map((c, i) => (
            <div key={c.key} className={cx('fl-trackcell', c.state === 'done' && 'fl-trackcell--on', (i === 2 || i === 7) && 'fl-trackcell--gap')}>
              <b>{c.label}</b><small>{c.ref ?? '—'}</small></div>
          ))}</div>
          <div className="fl-mdbox"><div className="fl-mdhead"><b>SUMMARY.MD</b><span>콘텐츠가 바뀔 때마다 자동 갱신</span></div><pre>{d.summary_md}</pre></div>
        </>
      )}
      <div className="fl-popfoot fl-popfoot--sb"><span>{d ? `마지막 갱신 · ${whenText(d.updated_at)}` : ''}</span>
        <button type="button" className="wm-btn wm-btn--h42" onClick={onClose}>닫기</button>
        <Link className="wm-btn wm-btn--primary wm-btn--h42 fl-popbtn18" to={`/storyboard/flow/${id}`} onClick={onClose}>Storyboard 열기</Link></div>
    </Modal>
  );
}

/** 연결된 콘텐츠 보기 팝업(보드 ContentPopup 820×680) — 콘텐츠 서비스가 stage 와 함께 준 card 를 그린다. 머리 · 바닥은 보드 값 그대로 */
export function ContentPopup({ flow, stage, onClose }: { flow: FlowDoc | undefined; stage: ContentKey | null; onClose: () => void }) {
  const cell = flow?.cells.find((c) => c.key === stage);
  const card = stage ? flow?.cards?.[stage] : undefined;
  const meta = stage ? CONTENT[stage] : null;
  // 연결된 Storyboard 칩: 이 Storyboard 이름 + 같은 콘텐츠를 쓰는 다른 Storyboard(분기면 「분기 B」처럼 짧게)
  const others = useFlowsById(cell?.shared ?? []);
  const shared = cell ? [flow!.name, ...(cell.shared ?? []).map((id, i) => {
    const o = others[i]?.data;
    if (!o) return id;
    return o.parent === flow!.id && o.name.startsWith(`${flow!.name} · `) ? o.name.slice(flow!.name.length + 3) : o.name;
  })] : [];
  const saved = flow?.history?.slice().reverse().find((h) => h.key === stage);
  const title = card?.title ?? cell?.ref ?? meta?.label ?? '';
  return (
    <Modal open={!!stage && !!cell} onClose={onClose} width={820} height={680} ariaLabel={title} bodyStyle={{ padding: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div className="fl-pophead fl-pophead--cp">
        <span className="fl-popic"><PathIcon d={meta?.icon ?? SB_ICON} size={19} color="var(--wm-brand)" /></span>
        <span className="fl-poptitles fl-poptitles--cp"><span className="fl-popkind">{meta?.label}<span className="fl-refpill">{cell?.ref} v{cell?.ver}</span></span>
          <span className="fl-popname">{title}</span>
          <span className="fl-popsub fl-popsub--cp">연결된 Storyboard{shared.map((s) => <span key={s} className="fl-sbpill">{s}</span>)}{saved?.at && <span>· {whenText(saved.at)} 저장</span>}</span></span>
        <PopX onClose={onClose} />
      </div>
      <div className="fl-cpbody">
        {card && <>
          {!!card.facts?.length && <div className="fl-facts">{card.facts.slice(0, 3).map(([k, v]) => <div key={k}><span>{k}</span><b>{v}</b></div>)}</div>}
          {card.groups?.map((g) => (
            <div key={g.h} className="fl-group"><div className="fl-grouph"><b>{g.h}</b>{g.sub && <span>{g.sub}</span>}</div>
              <div className="fl-grouplines">{g.lines?.map((l, i) => <div key={i}><span>{l.t}</span>{l.note && <em className={cx('fl-note', l.note === '확인 필요' && 'fl-note--warn', l.note === '확장' && 'fl-note--ext')}>{l.note}</em>}</div>)}</div></div>
          ))}
        </>}
        {!card && <span className="fl-muted">이 콘텐츠의 요약 카드가 아직 없어요 · 편집 화면에서 다시 저장하면 생겨요</span>}
      </div>
      <div className="fl-popfoot fl-popfoot--cp"><span>{card?.foot ?? ''}</span>
        {cell?.route && <Link className="wm-btn wm-btn--h42 fl-popbtn14" to={cell.route} onClick={onClose}>편집 화면에서 고치기</Link>}
        <button type="button" className="wm-btn wm-btn--primary wm-btn--h42 fl-popbtn18" onClick={onClose}>닫기</button></div>
    </Modal>
  );
}

// ── 목록(보드 List) ───────────────────────────────────

export interface DraftRow { title: string; ref?: string | null; to: string; sbIds: string[]; when?: string | null }

/** 콘텐츠 목록(보드 List) — 저장된 콘텐츠(허브)와 아직 저장 전 초안(drafts) */
export function ContentListScreen({ content, drafts = [], extra }: { content: ContentKey; drafts?: DraftRow[]; extra?: ReactNode }) {
  const m = CONTENT[content];
  useShellPage({ section: m.label, title: '', hasTask: false });
  const q = useFlowContents(content);
  const [pop, setPop] = useState<string | null>(null);
  const saved = (q.data?.items ?? []).map((it) => ({ title: it.title, ref: `${it.ref} v${it.ver}`, to: it.route, sbs: it.storyboards.map((s) => ({ id: s.id, name: s.name })), when: it.updated_at }));
  const savedRoutes = new Set(saved.map((r) => r.to));
  // 초안 줄의 Storyboard 칩은 id 대신 이름(보드 List) — 허브에서 읽는다
  const draftSbIds = useMemo(() => [...new Set(drafts.flatMap((d) => d.sbIds))], [drafts]);
  const draftSbs = useFlowsById(draftSbIds);
  const sbName = (id: string) => draftSbs[draftSbIds.indexOf(id)]?.data?.name ?? id;
  const rows = [...saved, ...drafts.filter((d) => !savedRoutes.has(d.to)).map((d) => ({ title: d.title, ref: d.ref ? `${d.ref} · 작성 중` : '작성 중', to: d.to, sbs: d.sbIds.map((id) => ({ id, name: sbName(id) })), when: d.when ?? null }))];
  const newTo = `/${m.base}/new`;
  return (
    <div className="fl-list">
      <div className="fl-listhead">
        <div className="fl-listtitles">
          <h1>{m.label}</h1>
          <div className="fl-listdesc"><span>{m.desc}</span><span className="fl-tag fl-tag--brand">사전 작업 · {m.pre}</span><span className="fl-tag">후속 작업 · {m.post}</span></div>
        </div>
        {extra}
        <Link className="fl-newbtn" to={newTo}><Icon name="plus" size={15} strokeWidth={2.4} />{m.newLabel}</Link>
      </div>
      {q.isError && <ErrorState message="목록을 불러오지 못했어요" onRetry={() => q.refetch()} />}
      {q.isLoading && <Skeleton h={220} r={14} />}
      {!q.isLoading && rows.length > 0 && (
        <div className="fl-table" role="table" aria-label={`${m.label} 목록`}>
          <div className="fl-tr fl-th" role="row"><span>{m.short}</span><span>연결된 Storyboard</span><span>수정</span><span /></div>
          {rows.map((r) => (
            <div key={r.to} className="fl-tr" role="row">
              <div className="fl-tdtitle"><Link to={r.to}>{r.title}</Link><span>{r.ref}</span></div>
              <div className="fl-chips">{r.sbs.map((b) => (
                <button key={b.id} type="button" className="fl-sbchip" onClick={() => setPop(b.id)}><PathIcon d={SB_ICON} size={12} color="var(--wm-brand)" strokeWidth={2.2} />{b.name}</button>
              ))}</div>
              <span className="fl-when">{whenText(r.when)}</span>
              <Link className="fl-open" to={r.to}>열기</Link>
            </div>
          ))}
        </div>
      )}
      {!q.isLoading && !q.isError && rows.length === 0 && (
        <div className="fl-empty"><b>아직 만든 {m.short}{josa(m.short, '이', '가')} 없어요</b><span>{content === 'rq' ? '고객 요구사항을 저장하면 Storyboard가 자동으로 만들어져요.' : `${m.pre}이 된 Storyboard를 골라 시작해요.`}</span>
          <Link className="fl-emptybtn" to={newTo}>{m.newLabel}</Link></div>
      )}
      <SBPopup id={pop} onClose={() => setPop(null)} />
    </div>
  );
}

// ── 사전 작업 고르기(보드 Gate) ──────────────────────

export interface GateStart { sbId: string; flow: FlowListItem }

/**
 * 사전 작업 Storyboard 고르기(보드 Gate · MI1 · MI1_Branch) — 고를 수 없는 Storyboard 는 아래(점선), 같은 콘텐츠가 있으면 수정 / 복제본.
 * onStart: 새로 만들 때(새 Storyboard 또는 분기 뒤) 콘텐츠 자원을 만들고 그 편집 경로를 돌려준다.
 */
export function GateScreen({ content, onStart, initialSb, autoStart }: {
  content: Exclude<ContentKey, 'rq'>; onStart: (s: GateStart) => Promise<string>; initialSb?: string | null;
  /** Storyboard 화면의 「만들기」(`?sb=&auto=1`) — 그 Storyboard 에 아직 이 콘텐츠가 없으면 고르기를 건너뛰고 바로 만든다(CF-07) */
  autoStart?: boolean;
}) {
  const m = CONTENT[content];
  const nav = useNavigate();
  const inval = useFlowInvalidate();
  useShellPage({ section: m.label, title: `새 ${m.short}`, hasTask: false, stepper: { steps: m.steps, current: 1 } });
  const q = useFlows(content);
  const items = q.data?.items ?? [];
  const firstOk = items.find((x) => x.eligible)?.id ?? null;
  const [sel, setSel] = useState<string | null>(null);
  const [choice, setChoice] = useState<'edit' | 'branch'>('edit');
  const [pop, setPop] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const cur = items.find((x) => x.id === (sel ?? (initialSb && items.some((y) => y.id === initialSb && y.eligible) ? initialSb : firstOk)));
  const ex = cur?.existing ?? null;
  const exRef = ex ? `${ex.ref} v${ex.ver}` : '';
  const sharedN = useMemo(() => (ex ? 1 + (ex.shared?.length ?? 0) : 0), [ex]);
  const cta = !cur ? '이 Storyboard로 시작' : !ex ? '이 Storyboard로 시작' : choice === 'edit' ? `${ex.ref} 수정하기` : '분기 만들고 시작';
  const nextLetter = 'BCDEFGH'[Math.min(items.filter((x) => x.parent === cur?.id).length, 6)];
  const foot = !cur ? '' : !ex ? `${cur.name}에 ${m.short}${josa(m.short, '이', '가')} 연결돼요` : choice === 'edit' ? '수정 내용은 요약본에 바로 반영돼요' : `‘${cur.name} · 분기 ${nextLetter}’가 새로 생겨요`;
  const autoRef = useRef(false);
  useEffect(() => {
    if (!autoStart || autoRef.current || !initialSb || !q.data) return;
    const it = q.data.items.find((x) => x.id === initialSb);
    if (!it || !it.eligible || it.existing) return;
    autoRef.current = true;
    setBusy(true);
    onStart({ sbId: it.id, flow: it }).then((to) => nav(to, { replace: true })).catch((e) => { toast((e as Error).message || '시작하지 못했어요'); setBusy(false); });
  }, [autoStart, initialSb, q.data, onStart, nav]);
  const go = async () => {
    if (!cur || busy) return;
    setBusy(true);
    try {
      if (ex && choice === 'edit' && ex.route) { nav(ex.route); return; }
      if (ex && choice === 'branch') {
        const b = await branchFlow(cur.id, content);
        inval();
        const to = await onStart({ sbId: b.id, flow: { ...cur, id: b.id, name: b.name, parent: cur.id, is_branch: true } });
        nav(to);
        return;
      }
      nav(await onStart({ sbId: cur.id, flow: cur }));
    } catch (e) { toast((e as Error).message || '시작하지 못했어요'); } finally { setBusy(false); }
  };
  return (
    <div className="fl-gate">
      <div className="fl-gatehead">
        <h1>어느 Storyboard로 만들까요?</h1>
        <div className="fl-gatedesc"><span className="fl-tag fl-tag--brand fl-tag--h24">사전 작업</span><span>{m.preDesc}이 있어야 시작할 수 있어요. 없으면 먼저 만들고 와 주세요.</span></div>
      </div>
      {q.isLoading && <Skeleton h={300} r={14} />}
      {q.isError && <ErrorState message="Storyboard 목록을 불러오지 못했어요" onRetry={() => q.refetch()} />}
      {!q.isLoading && !items.length && (
        <div className="fl-empty"><b>아직 Storyboard가 없어요</b><span>고객 요구사항을 저장하면 Storyboard가 자동으로 만들어져요.</span><Link className="fl-emptybtn" to="/requirements/new">새 요구사항</Link></div>
      )}
      <div className="fl-gaterows" role="radiogroup" aria-label="Storyboard">
        {items.map((r) => {
          const can = !!r.eligible;
          const on = can && cur?.id === r.id;
          const has = r.existing;
          return (
            <div key={r.id} className={cx('fl-grow', !can && 'fl-grow--off', on && 'fl-grow--on')}>
              <button type="button" className="fl-growbtn" role="radio" aria-checked={on} aria-disabled={!can} onClick={() => { if (can) { setSel(r.id); setChoice('edit'); } }}>
                <span className={cx('fl-radio', !can && 'fl-radio--off', on && 'fl-radio--on')} />
                <span className="fl-growtxt">
                  <span className="fl-growname"><b>{r.name}</b>{r.is_branch && <span className="fl-branch">분기</span>}</span>
                  <span className="fl-growmeta"><span>{r.customer ?? ''}</span><FlowDots cells={r.cells} /><span>{r.progress}</span></span>
                </span>
                <span className={cx('fl-pill', !can ? 'fl-pill--off' : has ? 'fl-pill--has' : 'fl-pill--go')}>{!can ? `${m.preShort} 먼저` : has ? `${has.ref} v${has.ver} 있음` : '이어서 만들기'}</span>
              </button>
              {!can && <Link className="fl-prego" to={m.preHref}>{m.preShort} 하러 가기</Link>}
              <button type="button" className="fl-ghost" onClick={() => setPop(r.id)} aria-label={`${r.name} 요약 보기`}>요약</button>
            </div>
          );
        })}
      </div>
      {ex && (
        <div className="fl-exist">
          <b>이 Storyboard에는 {m.short} {exRef}{josa(exRef, '이', '가')} 이미 있어요</b>
          <div className="fl-opts" role="radiogroup">
            {([['edit', '수정', `${exRef}${josa(exRef, '을', '를')} 고쳐요.${sharedN > 1 ? ` 연결된 Storyboard ${sharedN}개 모두에 반영돼요.` : ' 이 Storyboard에만 연결돼 있어요.'}`],
              ['branch', '복제본 만들기', `Storyboard를 분기해 새 ${m.short}${josa(m.short, '을', '를')} 만들어요. 앞 단계는 그대로 공유하고, 원본 ${exRef}는 바뀌지 않아요.`]] as const).map(([id, t, d]) => (
              <button key={id} type="button" role="radio" aria-checked={choice === id} className={cx('fl-opt', choice === id && 'fl-opt--on')} onClick={() => setChoice(id)}>
                <span className="fl-optt"><span className={cx('fl-radio fl-radio--18', choice === id && 'fl-radio--on18')} /><b>{t}</b></span><span className="fl-optd">{d}</span>
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="fl-gatefoot">
        <Link className="wm-flow__back" to={`/${m.base}`}><Icon name="chevronLeft" size={14} strokeWidth={2.4} />목록</Link>
        <span style={{ flex: 1 }} />
        <span className="fl-footline">{foot}</span>
        <button type="button" className="fl-cta" onClick={go} disabled={!cur || busy} aria-busy={busy || undefined}>{busy ? '여는 중…' : cta}<Icon name="arrowRight" size={16} strokeWidth={2.2} /></button>
      </div>
      <SBPopup id={pop} onClose={() => setPop(null)} />
    </div>
  );
}

// ── 완료(보드 Done) ──────────────────────────────────

/**
 * 완료 화면(보드 Done · *_Done · *_DoneJson) — 허브의 flow.json 전체에서 stages.<key> 를 강조하고, 단계 칸 · 요약 md 추가분을 그린다.
 *   <FlowDoneView sbId="SB-01" stageKey="mi" mdAdded={out.flow_sync?.md_added ?? out.summary_md} title="MI를 저장했어요" sub="…" onEdit={…} follow={…} />
 */
export function FlowDoneView({ sbId, sbIds, stageKey, mdAdded, stage, title, sub, onEdit, follow, note = '요약본이 방금 갱신됐어요', newStoryboard, jsonHead }: {
  sbId: string | null; sbIds?: string[]; stageKey: StageKey; mdAdded: string; stage?: unknown; title: string; sub?: ReactNode; onEdit?: () => void; follow?: ReactNode; note?: string;
  /** 이번 저장으로 Storyboard 가 새로 생겼다(고객 요구사항 첫 저장) → JSON 칸 머리 「새 Storyboard 전체」 · 팝업 전체 강조 */
  newStoryboard?: boolean;
  jsonHead?: ReactNode;
}) {
  const nav = useNavigate();
  const q = useFlow(sbId);
  const d = q.data;
  const stages: DoneStage[] = (d?.cells ?? ORDER.map((k) => ({ key: k, label: STAGE_LABEL[k], state: 'none', ref: null } as FlowCell))).map((c) => ({
    key: c.key, label: c.label, ref: c.ref, state: c.key === stageKey && c.state === 'done' ? 'cur' : c.state === 'done' ? 'done' : 'none',
  }));
  const st = stage ?? (d?.stages as Record<string, unknown> | undefined)?.[stageKey] ?? {};
  return (
    <div className="wm-flow">
      {sbId ? <FlowBar sbIds={sbIds ?? [sbId]} current={stageKey} note={note} /> : <LinkedStoryboardBar chips={[]} emptyText="연결된 Storyboard가 없어요" />}
      {sbId && q.isLoading ? <div style={{ padding: 28 }}><Skeleton h={420} r={16} /></div> : (
        <FlowDone title={title} sub={sub} sbName={d?.name ?? null} sbStage={d?.progress} stages={stages} md={mdAdded} stageKey={stageKey} stage={st}
          fullJson={d?.flow_json} onEdit={onEdit} follow={follow} onOpenStoryboard={sbId ? () => nav(`/storyboard/flow/${sbId}`) : undefined}
          jsonTitle={d?.id ? `${d.id}/flow.json` : 'flow.json'} highlightAll={newStoryboard} jsonHead={jsonHead ?? (newStoryboard ? '새 Storyboard 전체' : undefined)} />
      )}
    </div>
  );
}
