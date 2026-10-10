/**
 * CA2 · CA2_Info · CA2_Pc · CA2_AI — 경쟁사 리스트업 · 제안 기준 비교(보드 webapp1 CA2.dc.html 인라인 px 그대로 · caflow.css).
 * 왼쪽 290px 경쟁사 목록(직접 · AI 웹 탐색 · 점선 AI 후보 · 회사 이름으로 추가) | 오른쪽 1fr 고른 경쟁사(탭 3: 개요 · 선별 기준 / 제안 기준 비교 / 장단점 · 주장 포인트).
 * 바꾸는 호출은 모두 고친 문서를 돌려준다(→ 캐시). 보드에 없는 편집은 글을 눌러서 고치고, 더하기 · 빼기는 작게(올렸을 때만) 둔다.
 */
import { useState } from 'react';
import { useSearchParams } from 'react-router';
import { FlowBar } from '@/shell';
import { ApiError } from '@/api/client';
import { AiButton, FlowFooter, FlowScreen, cx, displayUrl, josa, toast, useConfirm } from '@/ui';
import {
  DIMS, useCfActions,
  type CFClaim, type CFCompetitor, type CFCriterion, type CFDoc, type CFDssItem, type CFMatch, type CFStageOut, type DimKey,
} from './api';
import { InlineText, VerdictPill, hasPlaceholder, type V } from './edit';

type Tab = 'info' | 'cmp' | 'pc';
const TABS: Array<[Tab, string]> = [['info', '개요 · 선별 기준'], ['cmp', '제안 기준 비교'], ['pc', '장단점 · 주장 포인트']];
const BY_TAG: Record<CFCompetitor['by'], string> = { manual: '직접', 'ai-web': 'AI 웹 탐색 · 추가', 'ai-pending': 'AI 후보' };
const AI_DOWN = '지금은 AI를 쓸 수 없어요 · 경쟁사를 직접 추가해 주세요.';

export function errText(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.code === 'LLM_UNAVAILABLE' || e.code === 'POLICY_CONFIDENTIAL' || e.code === 'LLM_TIMEOUT') return AI_DOWN;
    return e.message || '문제가 생겼어요. 다시 시도해 주세요.';
  }
  return '연결이 끊겼어요. 다시 시도해 주세요.';
}

const NO_DIM = { verdict: 'no-data' as V, note: '자료 없음' };
const dimOf = (m: CFMatch, k: DimKey) => (m.dims?.[k] as { verdict: V; note: string } | undefined) ?? NO_DIM;

/** 규모 칸 = 규모 · 매출(보드 ‘대기업 · 매출 [위키 값]’) */
function sizeText(w: CFCompetitor['wiki']) {
  return w.size.includes('매출') ? w.size : `${w.size} · 매출 ${w.revenue}`;
}
function splitSize(v: string): { size: string; revenue?: string } {
  const m = /^(.*?)\s*·\s*매출\s*(.*)$/.exec(v);
  return m ? { size: m[1].trim(), revenue: m[2].trim() } : { size: v };
}
/** 주장 문장 = 문장 — 연결 요구(보드 ‘… 증빙 — RQ-01’) */
const claimText = (c: CFClaim) => (c.supports ? `${c.text} — ${c.supports}` : c.text);
function splitClaim(v: string): { text: string; supports: string | null } {
  const m = /^(.*\S)\s+—\s+((?:RQ|요구)[^—]*)$/.exec(v);
  return m ? { text: m[1].trim(), supports: m[2].trim() } : { text: v, supports: null };
}

function ByTag({ by }: { by: CFCompetitor['by'] }) {
  return <span className={cx('caf-tag', `caf-tag--${by}`)}>{BY_TAG[by]}</span>;
}

// ── 개요 · 선별 기준 ─────────────────────────────────

function InfoTab({ c, patch }: { c: CFCompetitor; patch: (b: Parameters<ReturnType<typeof useCfActions>['patchCompetitor']>[1]) => void }) {
  const w = c.wiki;
  const meta: Array<[string, string, (v: string) => void]> = [
    ['본사', w.hq, (v) => patch({ wiki: { hq: v } })],
    ['규모', sizeText(w), (v) => patch({ wiki: splitSize(v) })],
    ['임직원', w.employees, (v) => patch({ wiki: { employees: v } })],
    ['업종', w.industry, (v) => patch({ wiki: { industry: v } })],
    ['주력 사업', w.mainBusiness, (v) => patch({ wiki: { mainBusiness: v } })],
    ['B2B 오피스', w.b2bOffice, (v) => patch({ wiki: { b2bOffice: v } })],
  ];
  const src = w.source;
  const ev = c.candidateEvidence;
  const [adding, setAdding] = useState(false);
  const setCrit = (i: number, x: Partial<CFCriterion>) => patch({ criteria: c.criteria.map((y, j) => (j === i ? { ...y, ...x } : y)) });
  const delCrit = (i: number) => patch({ criteria: c.criteria.filter((_, j) => j !== i) });
  return (
    <>
      <div className="caf-meta">
        {meta.map(([k, v, save]) => (
          <div key={k} className="caf-mcell">
            <span className="caf-mcell__k">{k}</span>
            <InlineText className={cx('caf-mcell__v', hasPlaceholder(v) && 'caf-ph')} value={v} label={`${c.name} ${k}`} onCommit={save} />
          </div>
        ))}
      </div>
      <span className="caf-src">
        기본 정보 · {src.type}{src.type === '직접 입력' ? '' : ' 기준'}
        {src.url ? <> <a href={src.url} target="_blank" rel="noreferrer" title={src.title ?? src.url}>{displayUrl(src.url)}</a></>
          : <> · <InlineText inline value="" placeholder="원문 URL [확인 필요]" label={`${c.name} 기본 정보 원문 URL`} onCommit={(v) => patch({ wiki: { source_url: v } })} /></>}
        {ev && <span title={ev.quote}> · 후보 근거 · {ev.source}{ev.date ? ` · ${ev.date}` : ''}</span>}
      </span>
      <div className="caf-hrow"><span className="caf-h">선별 기준</span>
        {!adding && <button type="button" className="caf-more" onClick={() => setAdding(true)}>+ 선별 기준</button>}</div>
      <div className="caf-crits">
        {c.criteria.map((x, i) => (
          <div key={`${i}-${x.k}`} className="caf-crit">
            <InlineText className="caf-crit__k" value={x.k} label={`선별 기준 ${i + 1} 이름`} onCommit={(v) => (v ? setCrit(i, { k: v }) : delCrit(i))} />
            <InlineText className="caf-crit__v" value={x.v} label={`${x.k} 선별 기준`} onCommit={(v) => (v ? setCrit(i, { v }) : delCrit(i))} />
            {x.status === 'check'
              ? <button type="button" className="caf-tbd" title="눌러서 확인 끝내기" aria-label={`${x.k} 확인 필요 · 눌러서 확인 끝내기`} onClick={() => setCrit(i, { status: 'ok' })}>확인 필요</button>
              : <button type="button" className="caf-tbd caf-tbd--mark" aria-label={`${x.k} 확인 필요로 표시`} onClick={() => setCrit(i, { status: 'check' })}>확인 필요</button>}
          </div>
        ))}
        {adding && (
          <div className="caf-crit">
            <span className="caf-crit__k">기준</span>
            <InlineText className="caf-crit__v" value="" startEditing placeholder="예) 고객 접점 · E 자산운용 거래 이력" label="새 선별 기준"
              onCancel={() => setAdding(false)}
              onCommit={(v) => { setAdding(false); const [k, ...rest] = v.split(' · '); patch({ criteria: [...c.criteria, rest.length ? { k: k.trim(), v: rest.join(' · ').trim(), status: 'check' } : { k: '기준', v, status: 'check' }] }); }} />
          </div>
        )}
      </div>
    </>
  );
}

// ── 제안 기준 비교 ──────────────────────────────────

function AddPair({ items, onAdd, onCancel, busy }: { items: CFDssItem[]; onAdd: (ours: string, theirs: string) => void; onCancel: () => void; busy: boolean }) {
  const [ours, setOurs] = useState(items[0]?.name ?? '');
  const [theirs, setTheirs] = useState('');
  const cats = [...new Set(items.map((i) => i.category))];
  return (
    <div className="caf-addpair" role="group" aria-label="비교 쌍 추가">
      <label className="wm-sr-only" htmlFor="caf-ours">우리 제품 · 솔루션(DSS)</label>
      <select id="caf-ours" value={ours} onChange={(e) => setOurs(e.target.value)}>
        {cats.map((cat) => (
          <optgroup key={cat} label={cat}>
            {items.filter((i) => i.category === cat).map((i) => <option key={i.name} value={i.name}>{i.name}{i.spaces?.length ? ` · ${i.spaces.join(' · ')}` : ''}</option>)}
          </optgroup>
        ))}
      </select>
      <span aria-hidden>↔</span>
      <label className="wm-sr-only" htmlFor="caf-theirs">경쟁 제품</label>
      <input id="caf-theirs" value={theirs} placeholder="경쟁 제품 · 예) 55&quot; 보급형 사이니지" onChange={(e) => setTheirs(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing && ours) onAdd(ours, theirs); if (e.key === 'Escape') onCancel(); }} />
      <button type="button" className="caf-mini caf-mini--primary" disabled={!ours || busy} onClick={() => onAdd(ours, theirs)}>추가</button>
      <button type="button" className="caf-mini" onClick={onCancel}>취소</button>
    </div>
  );
}

function CompareTab({ c, items, act }: { c: CFCompetitor; items: CFDssItem[]; act: ReturnType<typeof useCfActions> }) {
  const [adding, setAdding] = useState(false);
  const run = async (fn: () => Promise<unknown>) => { try { await fn(); } catch (e) { toast(errText(e)); } };
  const pick = (m: CFMatch, k: DimKey, x: V) => {
    const cur = dimOf(m, k);
    const body: { verdict: V; note?: string } = { verdict: x };
    if (x !== 'no-data' && cur.note === '자료 없음') body.note = '';          // 판정을 고르면 기본 메모(자료 없음)는 지운다
    if (x === 'no-data' && !cur.note.trim()) body.note = '';                 // 서버가 ‘자료 없음’ 으로 채운다
    void run(() => act.patchMatch(c.id, m.id, { dims: { [k]: body } }));
  };
  return (
    <>
      <div className="caf-cmp caf-cmphead"><span>우리 제안 ↔ 경쟁 제품</span>{DIMS.map(([, l]) => <span key={l}>{l}</span>)}</div>
      {c.matches.map((m) => (
        <div key={m.id} className="caf-cmp caf-pair" data-match={m.id}>
          <span className="caf-pair__l">
            <InlineText className="caf-where" value={m.space} label={`${m.ours} 공간`} onCommit={(v) => { if (v) void run(() => act.patchMatch(c.id, m.id, { space: v })); }} />
            <span className="caf-ours">{m.ours}</span>
            <InlineText className="caf-theirs" value={m.theirs} display={`↔ ${m.theirs}`} label={`${m.ours} 경쟁 제품`}
              onCommit={(v) => void run(() => act.patchMatch(c.id, m.id, { theirs: v }))} />
            <button type="button" className="caf-pairx" aria-label={`${m.ours} 비교 쌍 빼기`} title="비교 쌍 빼기" onClick={() => void run(() => act.deleteMatch(c.id, m.id))}>×</button>
          </span>
          {DIMS.map(([k, l]) => {
            const x = dimOf(m, k);
            return (
              <span key={k} className="caf-dim" data-dim={k}>
                <VerdictPill v={x.verdict} label={`${m.ours} ${l}`} onPick={(v) => pick(m, k, v)} />
                <InlineText className="caf-note" value={x.note} placeholder="한 줄 메모" label={`${m.ours} ${l} 메모`}
                  onCommit={(v) => void run(() => act.patchMatch(c.id, m.id, { dims: { [k]: { note: v } } }))} />
              </span>
            );
          })}
        </div>
      ))}
      {!c.matches.length && !adding && <div className="caf-cmpempty">비교 쌍이 없어요 · 「+ 비교 쌍」으로 DSS 제품과 맞서는 경쟁 제품을 더해요</div>}
      {adding && (
        <AddPair items={items} busy={act.busy} onCancel={() => setAdding(false)}
          onAdd={(ours, theirs) => void run(async () => { await act.addMatch(c.id, { ours, theirs: theirs.trim() || '[확인 필요]' }); setAdding(false); })} />
      )}
      <div className="caf-footrow">
        <span className="caf-foot">판정은 우리 제품 기준 · 우위 / 비슷 / 열위 · 수치와 견적은 원문 · 사내 자료로 확인</span>
        {!adding && <button type="button" className="caf-more" disabled={!items.length} onClick={() => setAdding(true)}>+ 비교 쌍</button>}
      </div>
    </>
  );
}

// ── 장단점 · 주장 포인트 ─────────────────────────────

function PcBox({ kind, title, items, onChange, who }: { kind: 'pro' | 'con'; title: string; items: string[]; onChange: (xs: string[]) => void; who: string }) {
  const [adding, setAdding] = useState(false);
  const word = kind === 'pro' ? '장점' : '단점';
  return (
    <div className={cx('caf-pcbox', `caf-pcbox--${kind}`)}>
      <span className="caf-pcbox__h">{title}</span>
      {items.map((t, i) => (
        <InlineText key={`${i}-${t}`} className="caf-pcitem" value={t} display={`· ${t}`} label={`${who} ${word} ${i + 1}`}
          onCommit={(v) => onChange(v ? items.map((y, j) => (j === i ? v : y)) : items.filter((_, j) => j !== i))} />
      ))}
      {adding
        ? <InlineText className="caf-pcitem" value="" startEditing placeholder={`${word} 한 줄`} label={`${who} 새 ${word}`} onCancel={() => setAdding(false)}
            onCommit={(v) => { setAdding(false); onChange([...items, v]); }} />
        : <button type="button" className="caf-more caf-more--corner" onClick={() => setAdding(true)}>+ {word}</button>}
    </div>
  );
}

function PcTab({ c, patch }: { c: CFCompetitor; patch: (b: Parameters<ReturnType<typeof useCfActions>['patchCompetitor']>[1]) => void }) {
  const [adding, setAdding] = useState(false);
  const setClaim = (i: number, x: Partial<CFClaim>) => patch({ claims: c.claims.map((y, j) => (j === i ? { ...y, ...x } : y)) });
  return (
    <>
      <div className="caf-pc">
        <PcBox kind="pro" title="경쟁사 장점 · 삼성 대비" items={c.pros} who={c.name} onChange={(xs) => patch({ pros: xs })} />
        <PcBox kind="con" title="경쟁사 단점 · 삼성 대비" items={c.cons} who={c.name} onChange={(xs) => patch({ cons: xs })} />
      </div>
      <div className="caf-claims">
        <span className="caf-claims__h">그래서 우리가 주장할 것</span>
        {c.claims.map((x, i) => (
          <span key={`${i}-${x.axis}-${x.text}`} className="caf-claim">
            <InlineText className="caf-axis" value={x.axis} label={`주장 ${i + 1} 축`} onCommit={(v) => setClaim(i, { axis: v || '주장' })} />
            <span className="caf-claim__t">
              <InlineText value={claimText(x)} label={`주장 ${i + 1}`}
                onCommit={(v) => (v ? setClaim(i, splitClaim(v)) : patch({ claims: c.claims.filter((_, j) => j !== i) }))} />
            </span>
          </span>
        ))}
        {adding && (
          <span className="caf-claim">
            <span className="caf-axis">주장</span>
            <span className="caf-claim__t">
              <InlineText value="" startEditing placeholder="예) 하나의 플랫폼으로 공간을 묶음 — RQ-01" label="새 주장" onCancel={() => setAdding(false)}
                onCommit={(v) => { setAdding(false); patch({ claims: [...c.claims, { axis: '주장', ...splitClaim(v) }] }); }} />
            </span>
          </span>
        )}
        {!adding && <button type="button" className="caf-more caf-more--corner" onClick={() => setAdding(true)}>+ 주장</button>}
      </div>
    </>
  );
}

// ── 화면 ─────────────────────────────────────────────

export function Editor({ doc, onFinished }: { doc: CFDoc; onFinished: (out: CFStageOut) => void }) {
  const act = useCfActions(doc.id);
  const { confirm, dialog } = useConfirm();
  const [sp, setSp] = useSearchParams();
  const tabQ = sp.get('tab');
  const tab: Tab = tabQ === 'info' || tabQ === 'pc' ? tabQ : 'cmp';
  const setTab = (t: Tab) => {
    const n = new URLSearchParams(sp);
    if (t === 'cmp') n.delete('tab'); else n.set('tab', t);
    setSp(n, { replace: true });
  };
  const [sel, setSel] = useState<string | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [name, setName] = useState('');
  const [adding, setAdding] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const comps = doc.competitors;
  const cur = comps.find((c) => c.id === sel) ?? comps[0] ?? null;
  const cand = cur?.by === 'ai-pending';
  const n = doc.counts.competitors;
  const nPairs = doc.counts.matches;
  const basis = doc.basis;

  const run = async <T,>(fn: () => Promise<T>): Promise<T | null> => {
    try { return await fn(); } catch (e) { toast(errText(e)); return null; }
  };
  const patch = (cid: string) => (b: Parameters<typeof act.patchCompetitor>[1]) => { void run(() => act.patchCompetitor(cid, b)); };

  const runAi = async () => {
    setAiBusy(true);
    const before = new Set(comps.map((c) => c.id));
    const r = await run(() => act.candidates());
    setAiBusy(false);
    if (!r) return;
    const first = (r.flow.competitors ?? []).find((c) => !before.has(c.id));
    if (first) setSel(first.id);
    if (!r.added) toast(r.reason ?? '근거가 확인되는 새 후보가 없어요 · 경쟁사를 직접 추가해 주세요.');
  };
  const addOne = async () => {
    const v = name.replace(/\s+/g, ' ').trim();
    if (!v || adding) return;
    setAdding(v);
    const d = await run(() => act.addCompetitor(v));
    setAdding(null);
    if (!d) return;
    setName('');
    const added = [...d.competitors].reverse().find((c) => c.name.toLowerCase() === v.toLowerCase());
    if (added) setSel(added.id);
  };
  const accept = (cid: string) => { setSel(cid); void run(() => act.patchCompetitor(cid, { accept: true })); };
  const remove = async (c: CFCompetitor) => {
    if (c.by !== 'ai-pending') {
      const ok = await confirm({ title: `${c.name}${josa(c.name, '을', '를')} 목록에서 뺄까요?`, message: '비교 쌍 · 장단점 · 주장도 함께 빠져요.', confirmLabel: '빼기', tone: 'danger' });
      if (!ok) return;
    }
    const d = await run(() => act.deleteCompetitor(c.id));
    if (d && sel === c.id) setSel(null);
  };
  const save = async () => {
    if (saving) return;
    setSaving(true);
    try { onFinished(await act.finish()); } catch (e) { toast(errText(e)); } finally { setSaving(false); }
  };

  const sbIds = doc.sb_id ? [doc.sb_id] : [];
  return (
    <FlowScreen pad="18px 40px" gap={12} className="caf-screen"
      bar={<FlowBar sbIds={sbIds} current="ca" note="Storyboard를 그대로 가져왔어요 · 사전 작업 DSS 확인됨" emptyText="연결된 Storyboard가 없어요" />}>
      <div className="caf-head">
        <div className="caf-head__t">
          <h1 className="wm-flow__h1">경쟁사를 리스트업하고 우리 제안과 비교해요</h1>
          <div className="caf-basis">
            <b>비교 기준 · {basis.from ?? 'DSS'}</b>
            {basis.categories.map((cat) => <span key={cat} className="caf-cat">{cat} {basis.counts?.[cat] ?? ''}</span>)}
          </div>
        </div>
        <AiButton onClick={() => void runAi()} busy={aiBusy}>AI 경쟁사 후보군 웹 탐색</AiButton>
      </div>

      <div className="wm-flow__grid caf-grid">
        {/* 경쟁사 목록(290) */}
        <div className="wm-flow__panel caf-left">
          <div className="caf-lhead"><b>경쟁사 {n}</b><span>점선은 AI 후보</span></div>
          <div className="caf-list" role="list" aria-label="경쟁사">
            {comps.map((c) => {
              const on = cur?.id === c.id;
              const isCand = c.by === 'ai-pending';
              return (
                <div key={c.id} role="listitem" className={cx('caf-row', on && 'caf-row--on', isCand && 'caf-row--cand')} data-cid={c.id}>
                  <button type="button" className="caf-card" aria-pressed={on} onClick={() => setSel(c.id)}>
                    <span className="caf-card__name"><b>{c.name}</b><ByTag by={c.by} /></span>
                    <span className="caf-card__meta">{c.industry} · {c.size}</span>
                    <span className="caf-card__why">{c.why}</span>
                  </button>
                  {isCand && <button type="button" className="caf-addcand" aria-label={`${c.name} 목록에 추가`} onClick={() => accept(c.id)}>추가</button>}
                  <button type="button" className="caf-rowx" aria-label={`${c.name} 빼기`} title={isCand ? 'AI 후보 빼기' : '목록에서 빼기'} onClick={() => void remove(c)}>×</button>
                </div>
              );
            })}
            {!comps.length && (
              <div className="caf-lempty">아직 경쟁사가 없어요. 아래에 회사 이름을 넣으면 위키 정보를 불러오고, 「AI 경쟁사 후보군 웹 탐색」으로 후보를 찾을 수도 있어요.</div>
            )}
          </div>
          <div className="caf-lfoot">
            <label htmlFor="ca-add" className="wm-sr-only">경쟁사 추가</label>
            <input id="ca-add" className="caf-addin" value={adding ?? name} disabled={!!adding}
              placeholder={adding ? '' : '+ 회사 이름 · 위키 정보를 불러와요'}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); void addOne(); } if (e.key === 'Escape') setName(''); }} />
          </div>
        </div>

        {/* 고른 경쟁사(1fr) */}
        <div className={cx('wm-flow__panel', cand && 'wm-flow__panel--dashed', 'caf-detail')} data-cid={cur?.id}>
          {!cur ? (
            <div className="caf-dempty"><b>경쟁사를 고르거나 추가해요</b>
              <span>왼쪽 아래에 회사 이름을 넣거나, 위 「AI 경쟁사 후보군 웹 탐색」으로 DSS 제품과 겹치는 후보를 찾아요.<br />비교 기준은 {basis.from ?? 'DSS'}의 제품 · 공간이에요.</span></div>
          ) : (
            <>
              <div className="caf-dhead">
                <span className="caf-letter" aria-hidden>{cur.id}</span>
                <span className="caf-dtitles">
                  <span className="caf-dname"><b>{cur.name}</b><ByTag by={cur.by} /></span>
                  <span className="caf-oneline">{cur.wiki.industry} · {cur.wiki.mainBusiness} · {cur.wiki.hq}</span>
                </span>
                {cand && <button type="button" className="caf-accept" onClick={() => accept(cur.id)}>목록에 추가</button>}
              </div>
              <div className="caf-tabs" role="tablist" aria-label={`${cur.name} 보기`}>
                {TABS.map(([id, t]) => (
                  <button key={id} type="button" role="tab" id={`caf-tab-${id}`} aria-selected={tab === id} aria-controls="caf-panel" className="caf-tab" onClick={() => setTab(id)}>{t}</button>
                ))}
              </div>
              <div className="caf-body" role="tabpanel" id="caf-panel" aria-labelledby={`caf-tab-${tab}`} key={`${cur.id}-${tab}`}>
                {tab === 'info' && <InfoTab c={cur} patch={patch(cur.id)} />}
                {tab === 'cmp' && <CompareTab c={cur} items={doc.dss_items} act={act} />}
                {tab === 'pc' && <PcTab c={cur} patch={patch(cur.id)} />}
              </div>
            </>
          )}
        </div>
      </div>

      <FlowFooter back={{ to: doc.sb_id ? `/storyboard/flow/${doc.sb_id}` : '/competitor', label: 'Storyboard' }}
        summary={n ? `경쟁사 ${n} · 비교 쌍 ${nPairs}` : '경쟁사를 하나 이상 목록에 넣어 주세요'} summaryTone={n ? undefined : 'warn'}
        primary={{ label: '저장', onClick: () => void save(), busy: saving, disabled: !n }} />
      {dialog}
    </FlowScreen>
  );
}
