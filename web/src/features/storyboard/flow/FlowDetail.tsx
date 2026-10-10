/**
 * SB1 — Storyboard 상세(보드 webapp1 SB1 · SB1_Json · SB1_View · SB1_Strat · SB1_StratAI). 경로 `/storyboard/flow/:id`.
 * 머리(이름 · main/분기 · 코드 · 고객 · 분기 n) → 진행 8칸 → [Key message + 연결된 콘텐츠 | 요약본 · md / 전체 흐름 · json 470] → 후속 작업(PPT 제작).
 * 보기 = ContentPopup(페이지 이동 없음) · 만들기 = `/<base>/new?sb=&auto=1`(CF-07) · 요약본 수정 = PATCH summary_md(사람 문장 ✎ 유지).
 */
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import {
  ContentPopup, SBPopup, flowKey, patchFlow, useFlow, useShellPage, whenText, type ContentKey, type FlowCell, type FlowDoc, type StageKey,
} from '@/shell';
import { ErrorState, FlowScreen, Icon, PathIcon, Skeleton, cx, josa, toast } from '@/ui';
import { CONTENT_KEYS, ORDER8, ROW_LABEL, SECTION, TRACK_LABEL, branchName, foldFlowJson, makeHref, stageName } from './model';
import { StrategyPopup } from './StrategyPopup';
import './sbf.css';

const BRANCH_D = 'M6 3v10a4 4 0 0 0 4 4h8 M15 14l3 3-3 3';
const PPT_D = 'M3 4h18v12H3z M8 20h8 M12 16v4 M7 12l3-3 2 2 4-4';

function sharedText(cell: FlowCell | undefined) {
  const sh = cell?.shared ?? [];
  if (!sh.length) return '';
  const w = sh.join(' · ');
  return `${w}${josa(w, '과', '와')} 공유`;
}

/** 연결된 콘텐츠 줄 한 줄 — 카드 line(콘텐츠 서비스가 준 값)이 있으면 그대로, ref 로 시작하지 않으면 앞에 `ref vN` */
function lineOf(d: FlowDoc, cell: FlowCell): string {
  const head = `${cell.ref} v${cell.ver}`;
  const line = d.cards?.[cell.key]?.line?.trim();
  if (!line) return head;
  return cell.ref && line.startsWith(cell.ref) ? line : `${head} · ${line}`;
}

/** 머리 오른쪽 「분기 n」 — 누르면 분기 목록, 고르면 그 Storyboard 요약 팝업 */
function BranchMenu({ d, onOpen }: { d: FlowDoc; onOpen: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const off = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', off);
    document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', off); document.removeEventListener('keydown', esc); };
  }, [open]);
  const items = d.branch_items?.length ? d.branch_items : (d.branches ?? []).map((id) => ({ id, name: id, stage: null, ref: null, title: null }));
  if (!items.length) return null;
  return (
    <div className="sbf-brwrap" ref={ref}>
      <button type="button" className="sbf-brbtn" aria-expanded={open} aria-haspopup="menu" onClick={() => setOpen((v) => !v)}>
        <PathIcon d={BRANCH_D} size={13} color="var(--wm-text-muted)" />분기 {items.length}
      </button>
      {open && (
        <div className="sbf-brpop" role="menu" aria-label="분기">
          {items.map((b) => (
            <button key={b.id} type="button" role="menuitem" className="sbf-bropt" onClick={() => { setOpen(false); onOpen(b.id); }}>
              <b>{b.name}</b>
              <span>{[b.id, b.stage ? `${stageName(b.stage)}에서 분기` : '', b.ref ? `${b.ref}${b.title && b.title !== b.ref ? ` ${b.title}` : ''}` : ''].filter(Boolean).join(' · ')}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/** 오른쪽 패널 — 요약본 · md / 전체 흐름 · json, 요약본 수정 */
function SummaryPanel({ d, onSaved }: { d: FlowDoc; onSaved: (doc: FlowDoc) => void }) {
  const [tab, setTab] = useState<'md' | 'json'>('md');
  const [edit, setEdit] = useState(false);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const startEdit = () => { setText(d.summary_md); setEdit(true); };
  const save = async () => {
    if (busy) return;
    if (text === d.summary_md) { setEdit(false); return; }
    setBusy(true);
    try {
      const doc = await patchFlow(d.id, { summary_md: text, expected_version: d.version });
      onSaved(doc);
      setEdit(false);
      toast('요약본을 고쳤어요 · 직접 고친 문장은 ✎ 로 남아요');
    } catch (e) { toast((e as Error).message || '요약본을 저장하지 못했어요'); } finally { setBusy(false); }
  };
  const isMd = tab === 'md';
  const foot = isMd ? (edit ? '직접 고친 문장은 콘텐츠가 바뀌어도 유지돼요' : '콘텐츠가 저장될 때마다 다시 써져요 · 직접 고친 부분은 표시해 유지')
    : '콘텐츠의 실제 값까지 이 JSON 하나에 담겨요 · […]는 접힌 배열';
  return (
    <div className="sbf-side">
      <div className="sbf-sidehead">
        <div role="tablist" aria-label="요약본 보기" className="sbf-tabs">
          <button type="button" role="tab" className="sbf-tab" aria-selected={isMd} onClick={() => setTab('md')}>요약본 · md</button>
          <button type="button" role="tab" className="sbf-tab" aria-selected={!isMd} onClick={() => { setTab('json'); setEdit(false); }}>전체 흐름 · json</button>
        </div>
        {isMd && <button type="button" className="sbf-textbtn" onClick={edit ? save : startEdit} disabled={busy} aria-busy={busy || undefined}>{edit ? (busy ? '저장 중…' : '저장') : '요약본 수정'}</button>}
      </div>
      {isMd && edit ? (
        <>
          <label htmlFor="sbf-md" className="wm-sr-only" style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0 0 0 0)' }}>요약본 수정</label>
          <textarea id="sbf-md" className="sbf-md" value={text} onChange={(e) => setText(e.target.value)} spellCheck={false}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') void save();
              if (e.key === 'Escape' && !busy) { e.preventDefault(); setEdit(false); }   // 보드에는 취소 버튼이 없다 — Esc 로 고치기 그만
            }} />
        </>
      ) : (
        <pre className="sbf-pre" data-testid={isMd ? 'sb-summary-md' : 'sb-flow-json'} tabIndex={0} aria-label={isMd ? '요약본' : '전체 흐름 JSON'}>
          {isMd ? d.summary_md : foldFlowJson(d.flow_json as Record<string, unknown>)}
        </pre>
      )}
      <div className="sbf-sidefoot">{foot}</div>
    </div>
  );
}

export function FlowDetailScreen() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const q = useFlow(id);
  const d = q.data;
  useShellPage({ section: SECTION, title: d?.name ?? id, sidebarGroup: 'storyboard' });
  const [cp, setCp] = useState<ContentKey | null>(null);
  const [pop, setPop] = useState<string | null>(null);
  const [strat, setStrat] = useState(false);
  const onSaved = (doc: FlowDoc) => {
    qc.setQueryData(flowKey(doc.id), doc);
    void qc.invalidateQueries({ queryKey: ['storyboard', 'flows'] });
  };
  if (!d) {
    return (
      <FlowScreen pad="22px 40px" gap={14}>
        {q.isError ? <ErrorState message="Storyboard를 불러오지 못했어요" onRetry={() => void q.refetch()} /> : <Skeleton h={560} r={14} />}
      </FlowScreen>
    );
  }
  const cell = (k: StageKey) => d.cells.find((c) => c.key === k);
  const km = d.key_message as { text?: string; by?: string } | null | undefined;
  const isBranch = !!d.parent;
  const view = (k: StageKey) => {
    if (k === 'ppt') { const c = cell('ppt'); if (c?.route) nav(c.route); return; }
    setCp(k as ContentKey);
  };
  return (
    <FlowScreen pad="22px 40px" gap={14} className="sbf-detail">
      <div className="sbf-head">
        <h1>{d.name}</h1>
        <span className={cx('sbf-badge', isBranch && 'sbf-badge--branch')}>{isBranch ? branchName(d.name) : 'main'}</span>
        <span className="sbf-headsub">{[d.id, d.customer].filter(Boolean).join(' · ')}</span>
        {isBranch && (
          <button type="button" className="sbf-parent" onClick={() => setPop(d.parent!)}>
            {d.parent} · {stageName((d.branch_point as { stage?: string } | null)?.stage)}에서 분기
          </button>
        )}
        <BranchMenu d={d} onOpen={setPop} />
        <span style={{ flexGrow: 1 }} />
        <span className="sbf-auto"><i />요약본 자동 갱신 · {whenText(d.updated_at)}</span>
      </div>

      <div className="sbf-track" aria-label="어디까지 입력됐나">
        {ORDER8.map((k, i) => {
          const c = cell(k);
          const done = c?.state === 'done';
          const cls = cx('sbf-cell', done && 'sbf-cell--done', (i === 2 || i === 7) && 'sbf-cell--gap');
          if (done) {
            return (
              <button key={k} type="button" className={cls} data-key={k} onClick={() => view(k)} aria-label={`${TRACK_LABEL[k]} ${c!.ref} v${c!.ver} 보기`}>
                <span className="sbf-celltop"><b>{TRACK_LABEL[k]}</b><Icon name="check" size={12} strokeWidth={3} /></span>
                <small>{c!.ref} v{c!.ver}</small>
              </button>
            );
          }
          return (
            <Link key={k} to={makeHref(k, d.id)} className={cls} data-key={k} aria-label={`${TRACK_LABEL[k]} ${k === 'ppt' ? '후속 작업' : '만들기'}`}>
              <b>{TRACK_LABEL[k]}</b><small>{k === 'ppt' ? '후속 작업' : '+ 만들기'}</small>
            </Link>
          );
        })}
      </div>

      <div className="sbf-grid">
        <div className="sbf-left">
          <div className={cx('sbf-kmcard', !km?.text && 'sbf-kmcard--none')} data-testid="sb-key-message">
            <span className="sbf-kmtxt">
              <small>Key message</small>
              {km?.text ? <b>{km.text}</b> : <b className="none">아직 없음 · 연결된 콘텐츠로 한 줄 메시지를 세워요</b>}
            </span>
            <button type="button" className="sbf-ghostbtn" onClick={() => setStrat(true)}>전략 수립</button>
          </div>
          <div className="sbf-contents">
            <div className="sbf-conthead"><b>연결된 콘텐츠</b><span>종류마다 하나씩</span></div>
            <div className="sbf-contbody" role="list" aria-label="연결된 콘텐츠">
              {CONTENT_KEYS.map((k) => {
                const c = cell(k)!;
                const has = c?.state === 'done';
                const share = has ? sharedText(c) : '';
                return (
                  <div key={k} className="sbf-crow" role="listitem" data-key={k}>
                    <span className={cx('sbf-cdot', !has && 'sbf-cdot--none')} />
                    <span className="sbf-clabel">{ROW_LABEL[k]}</span>
                    <span className="sbf-cmain">
                      <span className={has ? undefined : 'none'}>{has ? lineOf(d, c) : '아직 없음 · 만들면 이 Storyboard를 가져가요'}</span>
                      {share && <small>{share}</small>}
                    </span>
                    {has ? <button type="button" className="sbf-cta" onClick={() => view(k)} aria-label={`${ROW_LABEL[k]} 보기`}>보기</button>
                      : <Link className="sbf-cta sbf-cta--make" to={makeHref(k, d.id)} aria-label={`${ROW_LABEL[k]} 만들기`}>만들기</Link>}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
        <SummaryPanel key={d.id} d={d} onSaved={onSaved} />
      </div>

      <Link to={makeHref('ppt', d.id)} className="sbf-follow">
        <span className="sbf-followtag">후속 작업</span>
        <span className="sbf-followic" aria-hidden><PathIcon d={PPT_D} size={17} color="#fff" /></span>
        <span className="sbf-followtxt"><b>PPT 제작 · B2B 제안서</b><span>이 Storyboard의 요약본 · 연결된 콘텐츠로 제안서를 만들어요</span></span>
        <Icon name="arrowRight" size={16} color="var(--wm-brand)" strokeWidth={2.2} />
      </Link>

      <ContentPopup flow={d} stage={cp} onClose={() => setCp(null)} />
      <SBPopup id={pop} onClose={() => setPop(null)} />
      {strat && <StrategyPopup flow={d} onClose={() => setStrat(false)} onSaved={onSaved} />}
    </FlowScreen>
  );
}
