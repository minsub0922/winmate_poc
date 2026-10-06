/** MI3S — 출처 · 근거 패널 `/mi/:id/result?tab=&panel=sources&claim=` (§4.11) — 왼쪽 주장 목록 + 오른쪽 패널 */
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { CloseButton, Modal, Skeleton, cx, toast } from '@/ui';
import { fileUrl, uploadFile } from '@/api/client';
import {
  AREA_TAB, addSource, askQuestion, errText, getSnapshot, listSources, removeCitation, revertFix, startRevision, useClaim, useClaims, useSources,
  type Area, type ClaimItem, type ResultView, type SourceCard,
} from '../api';
import { useJobWatch } from '../hooks';
import { copyText } from '../lib';
import { Agent, BigButton, Dock, ErrorBand, Ic, P, Pill, PromptInput, ResultTabs, SecButton, Spin, UserBubble } from '../parts';

const FILTERS: Array<{ key: string | null; label: string; count: string }> = [
  { key: null, label: '전체', count: 'total' }, { key: 'public', label: '공개 자료', count: 'public' },
  { key: 'kb_case', label: '사내 사례 DB', count: 'kb_case' }, { key: 'needs_check', label: '확인 필요', count: 'needs_check' },
];

export function SourcesView({ aid, r, tab, claimId, version, onTab, onClaim, onClose, title }:
  { aid: string; r: ResultView; tab: Area; claimId: string | null; version?: number | null; onTab: (a: Area) => void; onClaim: (c: string | null) => void;
    onClose: () => void; title?: string }) {
  const nav = useNavigate();
  const qc = useQueryClient();
  const claims = useClaims(aid, { tab, version });
  const [onlyNeeds, setOnlyNeeds] = useState(false);
  const [filter, setFilter] = useState<string | null>(null);
  const [qa, setQa] = useState<Array<{ q: string; a?: string; cites?: number[]; busy?: boolean }>>([]);

  const items = (claims.data?.items ?? []).filter((c) => !onlyNeeds || (c.status !== 'matched' && c.status !== 'confirmed'));
  const tabSrc = (claims.data?.tab_sources ?? {}) as Record<string, number>;
  const needsTotal = claims.data?.needs_check_total ?? r.needs_check_total ?? 0;
  const badges = (claims.data?.badges ?? {}) as Partial<Record<Area, number>>;
  const selected = claimId && !filter ? claimId : null;

  // 처음 열면(주장 없이) 첫 확인 필요 주장, 없으면 첫 주장
  useEffect(() => {
    if (claimId || filter || !claims.data?.items.length) return;
    const first = claims.data.items.find((c) => c.status !== 'matched' && c.status !== 'confirmed') ?? claims.data.items[0];
    onClaim(first.id);
  }, [claims.data, claimId, filter, onClaim]);

  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ['mi', 'claims', aid] });
    void qc.invalidateQueries({ queryKey: ['mi', 'claim', aid] });
    void qc.invalidateQueries({ queryKey: ['mi', 'sources', aid] });
    void qc.invalidateQueries({ queryKey: ['mi', 'result', aid] });
    void qc.invalidateQueries({ queryKey: ['mi', 'fix', aid] });
  };

  async function ask(text: string) {
    const i = qa.length;
    setQa((x) => [...x, { q: text, busy: true }]);
    try {
      const res = await askQuestion(aid, { text, tab, claim_id: selected });
      setQa((x) => x.map((y, j) => (j === i ? { q: text, a: res.answerable ? res.answer_md : '저장된 출처로는 답할 수 없어요', cites: res.citations.map((c) => c.n) } : y)));
    } catch (e) {
      setQa((x) => x.map((y, j) => (j === i ? { q: text, a: errText(e) } : y)));
    }
  }

  async function copyList() {
    try {
      const { items: srcs } = await listSources(aid, { tab, version });
      const lines = srcs.filter((s) => s.n).sort((x, y) => (x.n ?? 0) - (y.n ?? 0)).map((s) => `${s.n}. ${s.card?.footnote ?? s.title}`);
      if (await copyText(lines.join('\n'))) toast(tab === 'competitor' ? '실명이 들어 있어요 · 고객 문서에는 익명 표기로 넣어 주세요' : '출처 목록을 복사했어요');
    } catch (e) { toast(errText(e)); }
  }

  return (
    <div className="mi-split">
      <div className="mi-split__main">
        <div className="mi-scroll">
          <div className="mi-col mi-col--narrow">
            <Agent text="결과의 주장마다 출처를 달았습니다. 번호를 누르면 오른쪽에 원문 구절이 열리고, 근거가 약한 주장은 '확인 필요'로 표시해 두었어요.">
              {claims.isError && <ErrorBand onRetry={() => void claims.refetch()} />}
              <div className="mi-card" data-testid="mi3s-claims">
                <ResultTabs tabs={r.tabs} value={tab} onChange={(a) => { setFilter(null); onTab(a); }} badges={badges} previewMode={r.preview} />
                <div className="mi-claims" role="list" aria-label="주장">
                  {!claims.data && <div className="mi-skel"><Skeleton h={14} /><Skeleton w="80%" h={14} /><Skeleton w="70%" h={14} /></div>}
                  {items.map((c) => <ClaimRow key={c.id} c={c} on={c.id === selected} onClick={() => { setFilter(null); onClaim(c.id); }} />)}
                  {claims.data && !items.length && <div className="mi-note" style={{ padding: 12 }}>{onlyNeeds ? '이 탭에는 확인 필요한 주장이 없어요.' : '이 탭에는 주장이 없어요.'}</div>}
                </div>
                <div className="mi-footer" style={{ padding: '8px 16px 12px', borderTop: '1px solid var(--wm-line-soft)' }}>
                  <span className="mi-ell" data-testid="mi3s-tab-summary">{claims.data?.summary_text}</span>
                  <span className="mi-legend">
                    <span className="mi-brand"><Ic d={P.ok} size={12} w={2.4} />원문 일치</span>
                    <span style={{ color: 'var(--wm-text)' }}><Ic d={P.warn} size={12} w={2.4} />확인 필요</span>
                  </span>
                </div>
              </div>
            </Agent>
            {qa.map((x, i) => (
              <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <UserBubble>{x.q}</UserBubble>
                <Agent>{x.busy ? <span className="mi-row"><Spin size={14} /> 저장된 출처에서 찾는 중</span>
                  : <div className="mi-answer__text">{x.a}{(x.cites ?? []).map((n) => <span key={n} className="mi-cite">{n}</span>)}</div>}</Agent>
              </div>
            ))}
          </div>
        </div>
        <Dock narrow title="근거 확인" meta={`확인 필요 ${needsTotal}건 남음`}
          right={<>
            <Pill pressed={onlyNeeds} onClick={() => setOnlyNeeds((v) => !v)}>확인 필요만 보기</Pill>
            <Pill onClick={() => void copyList()}>출처 목록 복사</Pill>
          </>}
          row={
            <div className="mi-dock__row">
              <PromptInput label="근거 질문" placeholder="근거 묻기 (예: 4번 출처 기준은?)" onSend={ask} />
              <SecButton to={`/mi/${aid}/verify`}>수치 확정하기</SecButton>
              <BigButton onClick={() => nav(`/mi/${aid}/export`)}>제안서 MI 섹션으로</BigButton>
            </div>
          } />
      </div>
      <SourcesPanel aid={aid} tab={tab} claimId={selected} version={version} filter={filter} setFilter={(f) => { setFilter(f); if (f) onClaim(null); }}
        counts={tabSrc} needsTotal={needsTotal} onClose={onClose} onChanged={refresh} title={title} />
    </div>
  );
}

function ClaimRow({ c, on, onClick }: { c: ClaimItem; on: boolean; onClick: () => void }) {
  const ok = c.status === 'matched' || c.status === 'confirmed';
  return (
    <div role="listitem" className={cx('mi-crow', on && 'mi-crow--sel')} onClick={onClick} data-claim={c.id} data-status={c.status}
      tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(); } }}>
      <div className="mi-crow__text">
        {c.text}
        {c.citations.map((x) => <span key={x.source_id} className={cx('mi-cite', on && 'mi-cite--on')}>{x.n}</span>)}
      </div>
      <span className={cx('mi-crow__st', ok && 'mi-crow__st--ok')}><Ic d={ok ? P.ok : P.warn} size={13} w={2.2} />{c.label}</span>
    </div>
  );
}

function SourcesPanel({ aid, tab, claimId, version, filter, setFilter, counts, needsTotal, onClose, onChanged, title }:
  { aid: string; tab: Area; claimId: string | null; version?: number | null; filter: string | null; setFilter: (f: string | null) => void;
    counts: Record<string, number>; needsTotal: number; onClose: () => void; onChanged: () => void; title?: string }) {
  const nav = useNavigate();
  const claim = useClaim(aid, claimId, version);
  const list = useSources(aid, { tab, kind: filter, version }, !!filter || !claimId);
  const [adding, setAdding] = useState<{ url: string } | null>(null);
  const [job, setJob] = useState<string | null>(null);
  const [snap, setSnap] = useState<{ title: string; text: string } | null>(null);

  useJobWatch(job, { onDone: (j) => { setJob(null); onChanged(); if (j.status === 'failed') toast(j.error?.message || '출처를 확인하지 못했어요'); } });

  const det = claim.data;
  const cards: SourceCard[] = filter || !claimId ? (list.data?.items ?? []).map((s) => s.card).filter((c): c is SourceCard => !!c) : det?.cards ?? [];

  async function act(card: SourceCard, label: string) {
    try {
      if (label === '원문 열기' && card.url) { window.open(card.url, '_blank', 'noopener,noreferrer'); return; }
      if (label === '파일 열기' && card.file_id) { window.open(fileUrl(card.file_id), '_blank', 'noopener,noreferrer'); return; }
      if (label === '수집본 보기') { const s = await getSnapshot(aid, card.source_id); setSnap({ title: card.title, text: s.text }); return; }
      if (label === '각주로 복사') {
        if (await copyText(card.footnote)) toast(tab === 'competitor' ? '실명이 들어 있어요 · 고객 문서에는 익명 표기로 넣어 주세요' : '각주를 복사했어요');
        return;
      }
      if (label === 'URL 붙여 확인') { setAdding({ url: '' }); return; }
      if (label === '다른 출처 찾기' && det) {
        const r = await startRevision(aid, { kind: 'claims', ids: [det.claim.id] }, '다른 출처 찾기');
        nav(`/mi/${aid}/revise?rev=${r.revision_id}`);
        return;
      }
      if (label === '값 직접 확정') { nav(`/mi/${aid}/verify${det?.fix_id ? `?fix=${det.fix_id}` : ''}`); return; }
      if (label === '이 출처 빼기' && det) { await removeCitation(aid, det.claim.id, card.source_id); onChanged(); return; }
      if (label === '되돌리기' && det?.fix_id) { await revertFix(aid, det.fix_id); onChanged(); return; }
    } catch (e) { toast(errText(e)); }
  }

  const sub = filter
    ? `${AREA_TAB[tab]} 탭 · ${FILTERS.find((f) => f.key === filter)?.label} ${cards.length}건`
    : `${AREA_TAB[tab]} 탭 · 선택한 주장의 출처 ${det?.counts?.total ?? cards.length}건`;
  return (
    <aside className="mi-panel" role="complementary" aria-label="출처 · 근거" data-testid="mi3s-panel">
      <div className="mi-panel__head">
        <Ic d={P.doc} size={18} w={2} className="mi-brand" />
        <div className="mi-grow" style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <div className="mi-panel__title">{title ?? '출처 · 근거'}</div>
          <div className="mi-panel__sub">{sub}</div>
        </div>
        <CloseButton label="패널 닫기" onClick={onClose} />
      </div>
      <div className="mi-panel__body">
        <div className="mi-kfilters" role="tablist" aria-label="출처 종류">
          {FILTERS.map((f) => (
            <button key={f.label} type="button" role="tab" className="mi-kfilter" aria-selected={filter === f.key && (!!f.key || !claimId)}
              onClick={() => setFilter(f.key)}>{f.label}<b>{counts[f.count] ?? 0}</b></button>
          ))}
        </div>
        {!filter && det && (
          <div className="mi-selclaim" data-testid="mi3s-selected">
            <span>선택한 주장</span>
            <b>{det.claim.text}</b>
            <span>출처 {det.counts.total}건 · 원문 일치 {det.counts.matched} · 확인 필요 {det.counts.needs_check}</span>
          </div>
        )}
        {(claim.isLoading || list.isLoading) && <Skeleton h={120} r={12} />}
        {(claim.isError || list.isError) && <ErrorBand onRetry={() => { void claim.refetch(); void list.refetch(); }} />}
        {cards.map((c) => <Card key={c.source_id} c={c} onAct={act} />)}
        {!filter && det && !cards.length && <div className="mi-note">이 주장에는 출처가 없어요 · 값을 직접 확정하거나 출처를 더해 주세요.</div>}
        {adding ? (
          <AddSourceForm aid={aid} claimId={det?.claim.id ?? null} initialUrl={adding.url} onCancel={() => setAdding(null)}
            onStarted={(jid) => { setAdding(null); setJob(jid); }} />
        ) : (
          <button type="button" className="mi-addsrc" onClick={() => setAdding({ url: '' })} disabled={!!job}>
            {job ? <Spin size={13} /> : <Ic d={P.plus} size={13} w={2.4} />}{job ? '출처를 확인하는 중' : '출처 직접 추가 · URL 또는 사내 문서'}
          </button>
        )}
      </div>
      <div className="mi-panel__foot">
        <div className="mi-grow" style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <div style={{ fontSize: 12.5, fontWeight: 600 }}>확인 필요 {needsTotal}건 <span className="mi-sub">· 전체 탭</span></div>
          <div className="mi-note mi-ell" style={{ fontSize: 11.5 }}>값 입력 · 사내 자료로 확정</div>
        </div>
        <Link to={`/mi/${aid}/verify`} className="mi-btn mi-btn--primary" style={{ height: 38, fontSize: 13, padding: '0 14px', borderRadius: 10 }}>
          한 번에 확정하기<Ic d={P.arrow} size={14} w={2.2} /></Link>
      </div>
      {snap && (
        <Modal open onClose={() => setSnap(null)} title={`수집본 · ${snap.title}`} width={640}>
          <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.65, maxHeight: '60vh', overflowY: 'auto' }}>{snap.text}</div>
        </Modal>
      )}
    </aside>
  );
}

function Card({ c, onAct }: { c: SourceCard; onAct: (c: SourceCard, label: string) => void }) {
  const ok = c.status === 'matched' || c.status === 'confirmed';
  const quote = c.quote_highlight
    ? <>“… {c.quote_before}<mark>{c.quote_highlight}</mark>{c.quote_after} …”</>
    : c.quote ? <>“… {c.quote} …”</> : null;
  return (
    <div className={cx('mi-scard', !ok && 'mi-scard--warn')} data-testid="mi3s-card" data-kind={c.kind} data-status={c.status}>
      <div className="mi-row">
        <span className="mi-scard__n">{c.n || '·'}</span>
        <span className="mi-scard__kind"><Ic d={c.kind.startsWith('kb') ? P.doc : P.globe} size={12} w={2} />{c.kind_label}</span>
        {ok ? <span className="mi-scard__ok"><Ic d={P.ok} size={13} w={2.4} />{c.status_label}</span>
          : <span className="mi-scard__warn"><Ic d={P.warn} size={13} w={2.4} />{c.status_label}</span>}
      </div>
      <div className="mi-scard__title" title={c.title}>{c.title}</div>
      {c.meta && <div className="mi-scard__meta">{c.meta}</div>}
      {quote && <div className={cx('mi-quote', !ok && 'mi-quote--weak', c.quote_style === 'model' && 'mi-quote--model')}>{quote}</div>}
      {c.reason && <div className="mi-reason"><Ic d={P.info} size={14} w={2.2} /><span>{c.reason}</span></div>}
      {c.flag && <div className="mi-flag">{c.flag}</div>}
      {c.actions.length > 0 && (
        <div className="mi-scard__acts">
          {c.actions.map((label) => (
            <button key={label} type="button" className={cx('mi-mini', label === '이 출처 빼기' && 'mi-mini--ghost')} onClick={() => onAct(c, label)}>
              {label === '원문 열기' && <Ic d={P.external} size={12} w={2.2} />}
              {label === '다른 출처 찾기' && <Ic d={P.refresh} size={12} w={2.2} />}
              {label}
            </button>
          ))}
          {c.has_snapshot && !c.actions.includes('수집본 보기') && c.url && <button type="button" className="mi-mini mi-mini--ghost" onClick={() => onAct(c, '수집본 보기')}>수집본 보기</button>}
        </div>
      )}
    </div>
  );
}

/** 출처 직접 추가(제안) — URL 또는 파일(분류 사내 자료 · 고객 자료 · 대외비) */
function AddSourceForm({ aid, claimId, initialUrl, onCancel, onStarted }:
  { aid: string; claimId: string | null; initialUrl: string; onCancel: () => void; onStarted: (jobId: string) => void }) {
  const [url, setUrl] = useState(initialUrl);
  const [cls, setCls] = useState<'internal' | 'customer' | 'confidential'>('internal');
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  async function submit(file?: File) {
    setBusy(true);
    try {
      let body: { url?: string; file_id?: string; classification: 'internal' | 'customer' | 'confidential'; claim_id?: string | null };
      if (file) {
        const up = await uploadFile(file, { confidential: cls !== 'customer', purpose: 'mi.source' });
        body = { file_id: up.id, classification: cls, claim_id: claimId };
      } else {
        const u = url.trim();
        if (!/^https?:\/\//.test(u)) { toast('http(s) 주소를 넣어 주세요'); setBusy(false); return; }
        body = { url: u, classification: 'internal', claim_id: claimId };
      }
      const r = await addSource(aid, body);
      onStarted(r.job_id);
    } catch (e) { toast(errText(e)); } finally { setBusy(false); }
  }
  return (
    <div className="mi-addsrc-form" data-testid="mi3s-addsrc">
      <label className="wm-sr-only" htmlFor="mi-src-url">출처 URL</label>
      <input id="mi-src-url" type="url" placeholder="https://… 원문 주소" value={url} onChange={(e) => setUrl(e.target.value)} />
      <div className="mi-row" style={{ gap: 6, flexWrap: 'wrap' }}>
        <button type="button" className="mi-mini mi-mini--primary" disabled={busy || !url.trim()} onClick={() => void submit()}>{busy ? <Spin size={12} /> : null}URL로 확인</button>
        <span className="mi-note">또는</span>
        <select value={cls} onChange={(e) => setCls(e.target.value as typeof cls)} aria-label="자료 분류" className="mi-select__btn" style={{ height: 28 }}>
          <option value="internal">사내 자료</option><option value="customer">고객 자료</option><option value="confidential">대외비</option>
        </select>
        <button type="button" className="mi-mini" disabled={busy} onClick={() => fileRef.current?.click()}><Ic d={P.upload} size={12} w={2.2} />사내 문서 올리기</button>
        <input ref={fileRef} type="file" hidden accept=".pdf,.pptx,.docx,.xlsx,.txt" onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) void submit(f); }} />
        <span className="mi-grow" />
        <button type="button" className="mi-mini mi-mini--ghost" onClick={onCancel}>취소</button>
      </div>
    </div>
  );
}
