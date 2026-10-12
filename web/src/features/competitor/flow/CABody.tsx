/**
 * 경쟁사 분석 본문(보드 webapp1 CABody — 래퍼 CA2 · CA_Draft · CA2_Info · CA2_Pc · CA2_AI · CA2_Edit · CA_View · CA_Table). px 는 보드 인라인 값 그대로(caflow.css · 접두어 caf-).
 *   띠(48): 비교 기준 · DSS-xx + 제품군 칩 · 보기 전환 「경쟁사별 | 비교표」 · AI 경쟁사 후보군 웹 탐색
 *   경쟁사별: 목록 290 | 고른 경쟁사 1fr(머리 · 탭 3 — 개요 · 선별 기준 / 제안 기준 비교 / 장단점 · 주장 포인트). 모든 칸을 그 자리에서 고친다(글은 칸을 떠날 때 저장 · 고르기는 누르는 즉시).
 *   비교표: 판정 합계 · 경쟁사 × 5축 · 우리 주장 포인트 — 행을 누르면 경쟁사별에서 그 경쟁사.
 * 저장된 것을 고치면(서버 changes > 0) 이 화면에서 고친 칸에 파란 테두리(cd-in--chg · 판정은 고리)를 단다 — 저장 · 되돌리기 하면 지운다.
 */
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { InlineInput, AiButton } from '@/shell';
import { ApiError } from '@/api/client';
import { cx, displayUrl, josa, toast, useConfirm } from '@/ui';
import {
  DIMS, VERDICTS, VERDICT_LABEL, useCfActions,
  type CFClaim, type CFCompetitor, type CFCriterion, type CFDoc, type CFDssItem, type CFMatch, type DimKey,
} from './api';
import { NewLine, NewPair, NoteBox, Pick, hasPlaceholder, type V } from './edit';

type Tab = 'info' | 'cmp' | 'pc';
type View = 'list' | 'table';
type Act = ReturnType<typeof useCfActions>;
type CompPatch = Parameters<Act['patchCompetitor']>[1];

const TABS: Array<[Tab, string]> = [['info', '개요 · 선별 기준'], ['cmp', '제안 기준 비교'], ['pc', '장단점 · 주장 포인트']];
const VIEWS: Array<[View, string]> = [['list', '경쟁사별'], ['table', '비교표']];
const AI_DOWN = '지금은 AI를 쓸 수 없어요 · 경쟁사를 직접 추가해 주세요.';
const AXES = ['통합', '사례', '가격', '스펙', 'ESG', '브랜드'];

export function errText(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.code === 'LLM_UNAVAILABLE' || e.code === 'POLICY_CONFIDENTIAL' || e.code === 'LLM_TIMEOUT') return AI_DOWN;
    return e.message || '문제가 생겼어요. 다시 시도해 주세요.';
  }
  return '연결이 끊겼어요. 다시 시도해 주세요.';
}

const NO_DIM = { verdict: 'no-data' as V, note: '자료 없음' };
const dimOf = (m: CFMatch, k: DimKey) => (m.dims?.[k] as { verdict: V; note: string } | undefined) ?? NO_DIM;
const inList = (c: CFCompetitor) => c.by !== 'ai-pending';

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

function tagOf(c: CFCompetitor): [string, string] {
  if (c.by === 'manual') return ['직접', 'caf-tag--manual'];
  return c.by === 'ai-web' ? ['AI 웹 탐색 · 추가', 'caf-tag--ai-web'] : ['AI 후보', 'caf-tag--ai-pending'];
}
function Tag({ c, table }: { c: CFCompetitor; table?: boolean }) {
  const [t, cls] = tagOf(c);
  return <span className={cx('caf-tag', cls)}>{table && c.by === 'ai-web' ? 'AI 웹 탐색' : t}</span>;
}

/** 고친 칸 표시 — 저장된 것을 고치는 중(changes > 0)일 때만 */
type Mark = (key: string) => boolean;

// ── 개요 · 선별 기준 ─────────────────────────────────

function InfoTab({ c, patch, mk, mark }: { c: CFCompetitor; patch: (b: CompPatch) => void; mk: Mark; mark: (k: string) => void }) {
  const w = c.wiki;
  const meta: Array<[string, string, string, (v: string) => CompPatch]> = [
    ['hq', '본사', w.hq, (v) => ({ wiki: { hq: v } })],
    ['size', '규모', sizeText(w), (v) => ({ wiki: splitSize(v) })],
    ['employees', '임직원', w.employees, (v) => ({ wiki: { employees: v } })],
    ['industry', '업종', w.industry, (v) => ({ wiki: { industry: v } })],
    ['mainBusiness', '주력 사업', w.mainBusiness, (v) => ({ wiki: { mainBusiness: v } })],
    ['b2bOffice', 'B2B 오피스', w.b2bOffice, (v) => ({ wiki: { b2bOffice: v } })],
  ];
  const src = w.source;
  const ev = c.candidateEvidence;
  const [adding, setAdding] = useState(false);
  const setCrit = (i: number, x: Partial<CFCriterion>) => { mark(`cr:${c.id}:${i}`); patch({ criteria: c.criteria.map((y, j) => (j === i ? { ...y, ...x } : y)) }); };
  const delCrit = (i: number) => patch({ criteria: c.criteria.filter((_, j) => j !== i) });
  return (
    <>
      <div className="caf-meta">
        {meta.map(([key, k, v, body]) => (
          <div key={key} className="caf-mcell">
            <span className="caf-mcell__k" aria-hidden>{k}</span>
            <InlineInput className={cx('caf-min', hasPlaceholder(v) && 'caf-min--ph')} value={v} label={`${c.name} ${k}`} maxLength={120}
              changed={mk(`w:${c.id}:${key}`)} onCommit={(x) => { mark(`w:${c.id}:${key}`); patch(body(x)); }} />
          </div>
        ))}
      </div>
      <span className="caf-src">
        기본 정보 · {src.type}{src.type === '직접 입력' ? '' : ' 기준'}{' '}
        {src.url
          ? <a href={src.url} target="_blank" rel="noreferrer" title={src.title ?? src.url}>{displayUrl(src.url)}</a>
          : <InlineInput className="caf-srcin" value="" placeholder="<원문 URL>" label={`${c.name} 기본 정보 원문 URL`} maxLength={300}
              onCommit={(v) => { mark(`w:${c.id}:src`); patch({ wiki: { source_url: v } }); }} />}
        {ev && <span title={ev.quote}> · 후보 근거 · {ev.source}{ev.date ? ` · ${ev.date}` : ''}</span>}
        {' · [위키 값]은 원문에서 채워요'}
      </span>
      <span className="caf-hrow"><b>선별 기준</b><span>왜 이 회사를 경쟁사로 봤는지</span></span>
      {c.criteria.map((x, i) => (
        <div key={`${i}-${x.k}`} className="caf-crit">
          <span className="caf-crit__k">{x.k}</span>
          <InlineInput className="caf-critin" value={x.v} label={`${x.k} 선별 기준`} maxLength={200} changed={mk(`cr:${c.id}:${i}`)}
            onCommit={(v) => (v ? setCrit(i, { v }) : delCrit(i))} />
          {x.status === 'check'
            ? <button type="button" className="caf-tbd" title="눌러서 확인 끝내기" aria-label={`${x.k} 확인 필요 · 눌러서 확인 끝내기`} onClick={() => setCrit(i, { status: 'ok' })}>확인 필요</button>
            : <button type="button" className="caf-tbd caf-tbd--mark" aria-label={`${x.k} 확인 필요로 표시`} onClick={() => setCrit(i, { status: 'check' })}>확인 필요</button>}
        </div>
      ))}
      {adding && (
        <NewPair className="caf-crit" onClose={() => setAdding(false)}
          head={(v, set) => <input className="cd-in caf-critk" aria-label="새 선별 기준 이름" placeholder="기준" value={v} maxLength={20} onChange={(e) => set(e.target.value)} />}
          text={{ placeholder: '예) E 자산운용 거래 이력', label: '새 선별 기준', className: 'caf-critin' }}
          onAdd={(k, v) => { mark(`cr:${c.id}:${c.criteria.length}`); patch({ criteria: [...c.criteria, { k: k || '기준', v, status: 'check' }] }); }} />
      )}
      {!adding && <button type="button" className="cd-link caf-link28" onClick={() => setAdding(true)}>+ 기준 추가</button>}
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
      <label className="cd-sr" htmlFor="caf-ours">우리 제품 · 솔루션(DSS)</label>
      <select id="caf-ours" className="cd-in" value={ours} onChange={(e) => setOurs(e.target.value)}>
        {cats.map((cat) => (
          <optgroup key={cat} label={cat}>
            {items.filter((i) => i.category === cat).map((i) => <option key={i.name} value={i.name}>{i.name}{i.spaces?.length ? ` · ${i.spaces.join(' · ')}` : ''}</option>)}
          </optgroup>
        ))}
      </select>
      <span aria-hidden>↔</span>
      <label className="cd-sr" htmlFor="caf-theirs">경쟁 제품</label>
      <input id="caf-theirs" className="cd-in" value={theirs} placeholder="경쟁 제품 · 예) 55&quot; 보급형 사이니지" maxLength={120} onChange={(e) => setTheirs(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing && ours) onAdd(ours, theirs); if (e.key === 'Escape') onCancel(); }} />
      <button type="button" className="cd-ok cd-ok--28" disabled={!ours || busy} onClick={() => onAdd(ours, theirs)}>추가</button>
      <button type="button" className="cd-link" onClick={onCancel}>취소</button>
    </div>
  );
}

function CompareTab({ c, items, act, mk, mark, run }: { c: CFCompetitor; items: CFDssItem[]; act: Act; mk: Mark; mark: (k: string) => void; run: (fn: () => Promise<unknown>) => Promise<unknown> }) {
  const [adding, setAdding] = useState(false);
  const pick = (m: CFMatch, k: DimKey, x: V) => {
    const cur = dimOf(m, k);
    const body: { verdict: V; note?: string } = { verdict: x };
    if (x !== 'no-data' && cur.note === '자료 없음') body.note = '';          // 판정을 고르면 기본 메모(자료 없음)는 지운다
    if (x === 'no-data' && !cur.note.trim()) body.note = '';                 // 서버가 ‘자료 없음’ 으로 채운다
    mark(`v:${c.id}:${m.id}:${k}`);
    void run(() => act.patchMatch(c.id, m.id, { dims: { [k]: body } }));
  };
  return (
    <>
      <div className="caf-cmp caf-cmphead"><span>우리 제안 ↔ 경쟁 제품</span>{DIMS.map(([, l]) => <span key={l}>{l}</span>)}</div>
      {c.matches.map((m) => (
        <div key={m.id} className={cx('caf-cmp caf-pair', mk(`mr:${c.id}:${m.id}`) && 'cd-chgrow')} data-match={m.id}>
          <span className="caf-pair__l">
            <InlineInput className="caf-bare caf-where" value={m.space} label={`${m.ours} 공간`} maxLength={60} changed={mk(`m:${c.id}:${m.id}:space`)}
              onCommit={(v) => { if (v) { mark(`m:${c.id}:${m.id}:space`); void run(() => act.patchMatch(c.id, m.id, { space: v })); } }} />
            <span className="caf-ours">{m.ours}</span>
            <span className="caf-theirs"><span aria-hidden>↔</span>
              <InlineInput className="caf-bare caf-theirsin" value={m.theirs} label={`${m.ours} 경쟁 제품`} maxLength={120} changed={mk(`m:${c.id}:${m.id}:theirs`)}
                onCommit={(v) => { mark(`m:${c.id}:${m.id}:theirs`); void run(() => act.patchMatch(c.id, m.id, { theirs: v })); }} />
            </span>
            <button type="button" className="caf-x caf-pairx" aria-label={`${m.ours} 비교 쌍 빼기`} title="비교 쌍 빼기" onClick={() => void run(() => act.deleteMatch(c.id, m.id))}>×</button>
          </span>
          {DIMS.map(([k, l]) => {
            const x = dimOf(m, k);
            return (
              <span key={k} className="caf-dim" data-dim={k}>
                <Pick<V> value={x.verdict} options={VERDICTS} labelOf={(v) => VERDICT_LABEL[v]} label={`${m.ours} ${l} 판정`} onPick={(v) => pick(m, k, v)}
                  className={cx('caf-pill', `caf-pill--${x.verdict}`)} optionClass={(v) => cx('caf-pill', `caf-pill--${v}`)} changed={mk(`v:${c.id}:${m.id}:${k}`)} />
                <NoteBox value={x.note} placeholder="한 줄 메모" label={`${m.ours} ${l} 메모`} changed={mk(`n:${c.id}:${m.id}:${k}`)}
                  onCommit={(v) => { mark(`n:${c.id}:${m.id}:${k}`); return run(() => act.patchMatch(c.id, m.id, { dims: { [k]: { note: v } } })); }} />
              </span>
            );
          })}
        </div>
      ))}
      {!c.matches.length && !adding && <div className="caf-cmpempty">비교 쌍이 없어요 · 아래 「+ 비교 쌍 추가」로 DSS 제품과 맞서는 경쟁 제품을 더해요</div>}
      {adding && (
        <AddPair items={items} busy={act.busy} onCancel={() => setAdding(false)}
          onAdd={(ours, theirs) => void run(async () => {
            const before = new Set(c.matches.map((m) => m.id));
            const d = await act.addMatch(c.id, { ours, theirs: theirs.trim() || '[확인 필요]' });
            const nm = d.competitors.find((x) => x.id === c.id)?.matches.find((m) => !before.has(m.id));
            if (nm) mark(`mr:${c.id}:${nm.id}`);
            setAdding(false);
          })} />
      )}
      {!adding && <button type="button" className="cd-link caf-link28" disabled={!items.length} onClick={() => setAdding(true)}>+ 비교 쌍 추가 · DSS 공간 제품 ↔ 경쟁 제품</button>}
      <span className="caf-foot">판정은 우리 제품 기준 · 우위 / 비슷 / 열위 / 자료 없음 · 수치와 견적은 원문 · 사내 자료로 확인</span>
    </>
  );
}

// ── 장단점 · 주장 포인트 ─────────────────────────────

function PcBox({ c, kind, items, patch, mk, mark }: { c: CFCompetitor; kind: 'pros' | 'cons'; items: string[]; patch: (b: CompPatch) => void; mk: Mark; mark: (k: string) => void }) {
  const [adding, setAdding] = useState(false);
  const title = kind === 'pros' ? '경쟁사 장점 · 삼성 대비' : '경쟁사 단점 · 삼성 대비';
  const word = kind === 'pros' ? '장점' : '단점';
  const set = (xs: string[]) => patch(kind === 'pros' ? { pros: xs } : { cons: xs });
  return (
    <div className={cx('caf-pcbox', `caf-pcbox--${kind}`)}>
      <span className="caf-pcbox__h">{title}</span>
      {items.map((t, i) => (
        <InlineInput key={`${i}-${t}`} className="caf-pcin" value={t} label={`${c.name} ${word} ${i + 1}`} maxLength={200} changed={mk(`p:${c.id}:${kind}:${i}`)}
          onCommit={(v) => { mark(`p:${c.id}:${kind}:${i}`); set(v ? items.map((y, j) => (j === i ? v : y)) : items.filter((_, j) => j !== i)); }} />
      ))}
      {adding
        ? <NewLine className="caf-pcin" placeholder={`${word} 한 줄`} label={`${c.name} 새 ${word}`} onClose={() => setAdding(false)}
            onAdd={(v) => { mark(`p:${c.id}:${kind}:${items.length}`); set([...items, v]); }} />
        : <button type="button" className="cd-link" onClick={() => setAdding(true)}>+ 추가</button>}
    </div>
  );
}

function AxisPick({ value, label, onPick, changed }: { value: string; label: string; onPick: (v: string) => void; changed?: boolean }) {
  const opts = AXES.includes(value) ? AXES : [value, ...AXES];
  return <Pick<string> value={value} options={opts} labelOf={(v) => v} label={label} onPick={onPick} className="caf-axis" changed={changed} />;
}

function PcTab({ c, patch, mk, mark }: { c: CFCompetitor; patch: (b: CompPatch) => void; mk: Mark; mark: (k: string) => void }) {
  const [adding, setAdding] = useState(false);
  const setClaim = (i: number, x: Partial<CFClaim>, key: string) => { mark(key); patch({ claims: c.claims.map((y, j) => (j === i ? { ...y, ...x } : y)) }); };
  return (
    <>
      <div className="caf-pc">
        <PcBox c={c} kind="pros" items={c.pros} patch={patch} mk={mk} mark={mark} />
        <PcBox c={c} kind="cons" items={c.cons} patch={patch} mk={mk} mark={mark} />
      </div>
      <div className="caf-claims">
        <span className="caf-claims__h">그래서 우리가 주장할 것</span>
        {c.claims.map((x, i) => (
          <span key={`${i}-${x.axis}-${x.text}`} className="caf-claim">
            <AxisPick value={x.axis} label={`주장 ${i + 1} 축`} changed={mk(`ca:${c.id}:${i}`)} onPick={(v) => setClaim(i, { axis: v }, `ca:${c.id}:${i}`)} />
            <InlineInput className="caf-claimin" value={claimText(x)} label={`주장 ${i + 1}`} maxLength={300} changed={mk(`ct:${c.id}:${i}`)}
              onCommit={(v) => (v ? setClaim(i, splitClaim(v), `ct:${c.id}:${i}`) : patch({ claims: c.claims.filter((_, j) => j !== i) }))} />
          </span>
        ))}
        {adding && <NewClaim onClose={() => setAdding(false)} onAdd={(axis, v) => { mark(`ct:${c.id}:${c.claims.length}`); patch({ claims: [...c.claims, { axis, ...splitClaim(v) }] }); }} />}
        {!adding && <button type="button" className="cd-link" onClick={() => setAdding(true)}>+ 주장 추가</button>}
      </div>
    </>
  );
}

function NewClaim({ onAdd, onClose }: { onAdd: (axis: string, text: string) => void; onClose: () => void }) {
  const [axis, setAxis] = useState(AXES[0]);
  return (
    <NewPair className="caf-claim" onClose={onClose} onAdd={(_, t) => onAdd(axis, t)}
      head={() => <AxisPick value={axis} label="새 주장 축" onPick={setAxis} />}
      text={{ placeholder: '예) 하나의 플랫폼으로 공간을 묶음 — RQ-01', label: '새 주장', className: 'caf-claimin' }} />
  );
}

// ── 비교표 ───────────────────────────────────────────

type Agg = V | 'mixed';
const AGG_LABEL: Record<Agg, string> = { ...VERDICT_LABEL, mixed: '엇갈림' };

function aggregate(c: CFCompetitor, k: DimKey): { v: Agg; n: string } {
  const n: Record<V, number> = { 'ours-better': 0, similar: 0, 'ours-worse': 0, 'no-data': 0 };
  for (const m of c.matches) n[dimOf(m, k).verdict]++;
  const tot = c.matches.length;
  const b = n['ours-better'];
  const w = n['ours-worse'];
  const v: Agg = b && w ? (b === w ? 'mixed' : b > w ? 'ours-better' : 'ours-worse') : b ? 'ours-better' : w ? 'ours-worse' : n.similar ? 'similar' : 'no-data';
  return { v, n: v === 'mixed' ? `우위 ${b} · 열위 ${w}` : `${n[v as V]} / ${tot}쌍` };
}

function TableView({ comps, onOpen }: { comps: CFCompetitor[]; onOpen: (id: string) => void }) {
  const tally = useMemo(() => {
    const t: Record<V, number> = { 'ours-better': 0, similar: 0, 'ours-worse': 0, 'no-data': 0 };
    for (const c of comps) for (const m of c.matches) for (const [k] of DIMS) t[dimOf(m, k).verdict]++;
    return t;
  }, [comps]);
  return (
    <div className="caf-table">
      <div className="caf-tally">
        <b>판정 합계</b>
        {VERDICTS.map((v) => <span key={v} className="caf-tally__i"><span className={cx('caf-chip', `caf-chip--${v}`)}>{VERDICT_LABEL[v]}</span>{tally[v]}</span>)}
        <span style={{ flexGrow: 1 }} />
        <span className="caf-tally__note">행을 누르면 경쟁사별에서 바로 고쳐요</span>
      </div>
      <div className="caf-trow caf-thead" aria-hidden>
        <span>경쟁사 · 겹치는 공간</span>{DIMS.map(([, l]) => <span key={l}>{l}</span>)}<span>우리 주장 포인트</span>
      </div>
      <div className="caf-tbody" role="list" aria-label="경쟁사 비교표">
        {comps.map((c) => (
          <button key={c.id} type="button" role="listitem" className="caf-trow caf-tline" data-cid={c.id} onClick={() => onOpen(c.id)} aria-label={`${c.name} 경쟁사별에서 고치기`}>
            <span className="caf-tname">
              <span className="caf-tname__t"><b>{c.name}</b><Tag c={c} table /></span>
              <span className="caf-tname__w">{c.industry} · {c.size} · {c.wiki.hq}</span>
              <span className="caf-tname__s">{c.spaces.length ? `${c.spaces.join(' · ')} 겹침` : '겹치는 공간 [확인 필요]'}</span>
            </span>
            {DIMS.map(([k]) => {
              const a = aggregate(c, k);
              return <span key={k} className="caf-tcell" data-dim={k}><span className={cx('caf-chip', `caf-chip--${a.v}`)}>{AGG_LABEL[a.v]}</span><span className="caf-tcell__n">{a.n}</span></span>;
            })}
            <span className="caf-tclaims">
              {c.claims.slice(0, 2).map((x, i) => <span key={i} className="caf-tclaim"><span className="caf-tclaim__k">{x.axis}</span><span>{claimText(x)}</span></span>)}
            </span>
          </button>
        ))}
        {!comps.length && <div className="caf-tempty">목록에 든 경쟁사가 없어요 · 경쟁사별에서 회사 이름을 넣거나 AI 후보를 추가해요</div>}
      </div>
    </div>
  );
}

// ── 본문 ─────────────────────────────────────────────

export function CABody({ doc, act, saved }: { doc: CFDoc; act: Act; saved: boolean }) {
  const { confirm, dialog } = useConfirm();
  const [view, setView] = useState<View>('list');
  const [tab, setTab] = useState<Tab>('cmp');
  const [sel, setSel] = useState<string | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [name, setName] = useState('');
  const [adding, setAdding] = useState<string | null>(null);
  // 이 화면에서 고친 칸(저장된 것을 고치는 중에만 보인다 · 고친 곳이 0 이 되면 지운다)
  const [marks, setMarks] = useState<Set<string>>(() => new Set());
  const editing = saved && (doc.changes ?? 0) > 0;
  useEffect(() => { if (!editing) setMarks((m) => (m.size ? new Set() : m)); }, [editing]);
  const mark = (k: string) => { if (saved) setMarks((m) => (m.has(k) ? m : new Set(m).add(k))); };
  const mk: Mark = (k) => editing && marks.has(k);

  // 목록 순서 = 목록에 든 것 · 점선 AI 후보(보드 order = inIds + candIds)
  const comps = useMemo(() => [...doc.competitors.filter(inList), ...doc.competitors.filter((c) => !inList(c))], [doc.competitors]);
  const listed = comps.filter(inList);
  const nCand = comps.length - listed.length;
  const cur = comps.find((c) => c.id === sel) ?? comps[0] ?? null;
  const cand = !!cur && !inList(cur);
  const basis = doc.basis;

  const run = async <T,>(fn: () => Promise<T>): Promise<T | null> => {
    try { return await fn(); } catch (e) { toast(errText(e)); return null; }
  };
  const patch = (cid: string) => (b: CompPatch) => { void run(() => act.patchCompetitor(cid, b)); };

  const runAi = async () => {
    setAiBusy(true);
    const before = new Set(doc.competitors.map((c) => c.id));
    const r = await run(() => act.candidates());
    setAiBusy(false);
    if (!r) return;
    const first = (r.flow.competitors ?? []).find((c) => !before.has(c.id));
    if (first) { setSel(first.id); setView('list'); }
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
    if (added) { setSel(added.id); mark(`c:${added.id}`); }
  };
  const accept = (cid: string) => { setSel(cid); mark(`c:${cid}`); void run(() => act.patchCompetitor(cid, { accept: true })); };
  const remove = async (c: CFCompetitor) => {
    if (inList(c)) {
      const ok = await confirm({ title: `${c.name}${josa(c.name, '을', '를')} 목록에서 뺄까요?`, message: '비교 쌍 · 장단점 · 주장도 함께 빠져요.', confirmLabel: '빼기', tone: 'danger' });
      if (!ok) return;
    }
    const d = await run(() => act.deleteCompetitor(c.id));
    if (d && sel === c.id) setSel(null);
  };
  const openFromTable = (id: string) => { setSel(id); setView('list'); };

  let detail: ReactNode;
  if (!cur) {
    detail = (
      <div className="caf-nosel">
        <b>경쟁사를 고르면 여기서 바로 비교해요</b>
        <span>개요 · 선별 기준 → 제안 기준 비교(스펙 · 가격 · 유관 사례 · ESG · 브랜드 평판) → 장단점 · 주장 포인트</span>
      </div>
    );
  } else {
    detail = (
      <div className={cx('caf-detail', cand && 'caf-detail--cand')} data-cid={cur.id}>
        <div className="caf-dhead">
          <span className="caf-letter" aria-hidden>{cur.id}</span>
          <span className="caf-dtitles">
            <span className="caf-dname"><b>{cur.name}</b><Tag c={cur} /></span>
            <span className="caf-oneline">{cur.wiki.industry} · {cur.wiki.mainBusiness} · {cur.wiki.hq}</span>
          </span>
          {cand
            ? <button type="button" className="caf-accept" onClick={() => accept(cur.id)}>목록에 추가</button>
            : <button type="button" className="caf-out" onClick={() => void remove(cur)}>목록에서 빼기</button>}
        </div>
        <div className="caf-tabs" role="tablist" aria-label={`${cur.name} 보기`}>
          {TABS.map(([id, t]) => (
            <button key={id} type="button" role="tab" id={`caf-tab-${id}`} aria-selected={tab === id} aria-controls="caf-panel" className="caf-tab" onClick={() => setTab(id)}>{t}</button>
          ))}
        </div>
        <div className="caf-dbody" role="tabpanel" id="caf-panel" aria-labelledby={`caf-tab-${tab}`} key={`${cur.id}-${tab}`}>
          {tab === 'info' && <InfoTab c={cur} patch={patch(cur.id)} mk={mk} mark={mark} />}
          {tab === 'cmp' && <CompareTab c={cur} items={doc.dss_items} act={act} mk={mk} mark={mark} run={run} />}
          {tab === 'pc' && <PcTab c={cur} patch={patch(cur.id)} mk={mk} mark={mark} />}
        </div>
      </div>
    );
  }

  return (
    <div className="caf-body">
      <div className="cd-strip caf-strip">
        <span className="caf-strip__b">비교 기준 · {basis.from ?? 'DSS'}</span>
        {basis.categories.map((cat) => <span key={cat} className="caf-cat">{cat} {basis.counts?.[cat] ?? ''}</span>)}
        <span style={{ flexGrow: 1 }} />
        <div className="caf-seg" role="tablist" aria-label="보기">
          {VIEWS.map(([id, t]) => <button key={id} type="button" role="tab" aria-selected={view === id} className="caf-segbtn" onClick={() => setView(id)}>{t}</button>)}
        </div>
        <AiButton size={36} onClick={() => void runAi()} busy={aiBusy}>AI 경쟁사 후보군 웹 탐색</AiButton>
      </div>

      {view === 'list' ? (
        <div className="caf-grid">
          <div className="caf-left">
            <div className="caf-lhead"><b>경쟁사 {listed.length}</b><span>{nCand ? '점선은 AI 후보 · 추가해야 들어가요' : `비교 쌍 ${doc.counts.matches}`}</span></div>
            <div className="caf-list" role="list" aria-label="경쟁사">
              {!comps.length && (
                <div className="caf-lempty"><b>아직 경쟁사가 없어요</b><span>아래에 회사 이름을 넣거나 위의 AI 경쟁사 후보군 웹 탐색을 눌러요</span></div>
              )}
              {comps.map((c) => {
                const on = cur?.id === c.id;
                const isCand = !inList(c);
                return (
                  <div key={c.id} role="listitem" className={cx('caf-row', on && 'caf-row--on', isCand && 'caf-row--cand', mk(`c:${c.id}`) && 'caf-row--chg')} data-cid={c.id}>
                    <button type="button" className="caf-card" aria-pressed={on} onClick={() => setSel(c.id)}>
                      <span className="caf-card__name"><b>{c.name}</b><Tag c={c} /></span>
                      <span className="caf-card__meta">{c.industry} · {c.size}</span>
                      <span className="caf-card__why">{c.why}</span>
                    </button>
                    {isCand && <>
                      <button type="button" className="caf-addcand" aria-label={`${c.name} 목록에 추가`} onClick={() => accept(c.id)}>추가</button>
                      <button type="button" className="caf-x caf-rowx" aria-label={`${c.name} 후보 빼기`} title="AI 후보 빼기" onClick={() => void remove(c)}>×</button>
                    </>}
                  </div>
                );
              })}
            </div>
            <div className="caf-lfoot">
              <label htmlFor="ca-add" className="cd-sr">경쟁사 추가</label>
              <input id="ca-add" className="caf-addin" value={adding ?? name} disabled={!!adding} maxLength={80}
                placeholder="+ 회사 이름 · 위키 정보를 불러와요"
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); void addOne(); } if (e.key === 'Escape') setName(''); }} />
            </div>
          </div>
          {detail}
        </div>
      ) : (
        <TableView comps={listed} onOpen={openFromTable} />
      )}
      {dialog}
    </div>
  );
}
